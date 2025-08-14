from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.init_engine import get_db, engine
from db import db_models
from pydantic import BaseModel
from pydantic import Field
from typing import Optional
from enum import Enum
from email_validator import validate_email, EmailNotValidError
import uuid
import bcrypt


router: APIRouter = APIRouter(prefix="/user")
db_models.Base.metadata.create_all(bind=engine)

class user_type(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"

class user_login(BaseModel):
    user_id: str  # either email or username
    password: str
    user_type: user_type

class user_register(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    user_id: str
    user_type: user_type # identify the user

user_model_map = {
        user_type.TEACHER: (db_models.teacher, db_models.teacher.email),
        user_type.STUDENT: (db_models.student, db_models.student.user_name),
    }

def hash_password(plain_password: str): # Function to hash the password
    salt: bytes = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str): # Function to verify the password
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


@router.post("/register", tags=["user"], status_code=status.HTTP_201_CREATED)
async def register(payload: user_register, db:Session = Depends(get_db)):
    
    model_info = user_model_map.get(payload.user_type)

    if not model_info:
        return JSONResponse(content={'msg': "Invalid user type"}, status_code=status. HTTP_422_UNPROCESSABLE_ENTITY)
    
    model_class, identifier_field = model_info

    existing_user = db.query(model_class).filter(identifier_field == payload.user_id).first()
    
    if existing_user:
        return JSONResponse(content={'msg': f"User already exists"}, status_code=status.HTTP_409_CONFLICT)

    if payload.user_type == user_type.TEACHER:
        if not payload.user_id:
            return JSONResponse(content={'msg': "Email is required for teacher registration"}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
        try:
            valid = validate_email(payload.user_id.strip())
            identifier = valid.email.lower()
        except EmailNotValidError as e:
            return JSONResponse(content={'msg': f"Invalid email address: {str(e)}"}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

        new_user = model_class(
            email=identifier,
            first_name=payload.first_name,
            last_name=payload.last_name,
            password=hash_password(payload.password)
        )

    elif payload.user_type == user_type.STUDENT:
        if not payload.user_id:
            return JSONResponse(content={'msg': "Username is required for student registration"}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
            
        identifier = payload.user_id.strip()
        new_user = model_class(
            user_name=identifier,
            first_name=payload.first_name,
            last_name=payload.last_name,
            password=hash_password(payload.password)
        )
    else:
        return JSONResponse(content={'msg': "Unsupported user type"}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        return JSONResponse(content={'msg': f"Failed to register {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return {'msg': "User registered successfully","user_type": payload.user_type.value, "id":identifier}


@router.post("/login", tags=["user"], status_code=status.HTTP_200_OK)
async def login(user: user_login, request: Request, db: Session = Depends(get_db)):

    model_info = user_model_map.get(user.user_type)

    if not model_info:
        return JSONResponse(content={'msg': "Invalid user type"}, status_code=status.HTTP_401_UNAUTHORIZED)

    model_class, identifier_field = model_info

    if user.user_type == user_type.TEACHER:
        try:
            valid = validate_email(user.user_id)
            user.user_id = valid.email
        except EmailNotValidError as e:
            return JSONResponse(content={'msg': f"Invalid email address: {str(e)}"}, status_code=status.HTTP_400_BAD_REQUEST)

    db_user = db.query(model_class).filter(identifier_field == user.user_id).first()

    if not db_user or not verify_password(user.password, db_user.password):
        return JSONResponse(content={'msg': "User does not exist"}, status_code=status.HTTP_401_UNAUTHORIZED)
    
    api_key = str(uuid.uuid4())

    return {"message": api_key}
