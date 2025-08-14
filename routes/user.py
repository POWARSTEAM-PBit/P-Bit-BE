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
import re


USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")

router: APIRouter = APIRouter(prefix="/user")
db_models.Base.metadata.create_all(bind=engine)

class user_type(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"





class user_register(BaseModel):
    user_type: user_type # identify the user
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    #teacher 
    email: Optional[str] = None
    #student specific fields
    user_name: Optional[str] = Field(None, min_length=3, max_length=32)
    

@router.post("/register", tags=["user"], status_code=status.HTTP_201_CREATED)
async def register(payload: user_register, db:Session = Depends(get_db)):
    
    
    if payload.user_type == user_type.TEACHER:
        if not payload.email:
            return JSONResponse(
                content={'msg': "Email is required for teacher registration"}, status_code=status.HTTP_400_BAD_REQUEST)
        try:
            valid = validate_email(payload.email.strip())
            identifier = valid.email.lower()
        except EmailNotValidError as e:
            return JSONResponse(content={'msg': f"Invalid email address: {str(e)}"}, status_code=status.HTTP_400_BAD_REQUEST)

        model = db_models.teacher
        unique_col = db_models.teacher.email
        new_row = model(
            email=identifier,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            password=hash_password(payload.password)
        )   

    elif payload.user_type == user_type.STUDENT:
        if not payload.user_name:
            return JSONResponse({'msg': "Username is required for student registration"}, status_code=status.HTTP_400_BAD_REQUEST)
        uname = payload.user_name.strip()
        if not USERNAME_RE.fullmatch(uname):
            return JSONResponse({'msg': "Invalid username"}, status_code=status.HTTP_400_BAD_REQUEST)
        
        identifier = uname
        model = db_models.student
        unique_col = db_models.student.user_name
        new_row = model(
            user_name=identifier,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            password=hash_password(payload.password)
        )
    else:
        return JSONResponse(content={'msg': "Invalid user type"}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    
    if db.query(model).filter(unique_col == identifier).first():
        return JSONResponse(content={'msg': "User already exists"}, status_code=status.HTTP_409_CONFLICT)
    
    try:
        db.add(new_row)
        db.commit()
        db.refresh(new_row)
    except Exception as e:
        db.rollback()
        return JSONResponse(content={'msg': f"Failed to register {str(e)}"}, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return {'msg': "User registered successfully","user_type": payload.user_type.value, "id":identifier}












class user_login(BaseModel):
    user_id: str  # either email or username
    password: str
    user_type: user_type


@router.post("/login", tags=["user"], status_code=status.HTTP_200_OK)
async def login(user: user_login, request: Request, db: Session = Depends(get_db)):

    user_model_map = {
        user_type.TEACHER: (db_models.teacher, db_models.teacher.email),
        user_type.STUDENT: (db_models.student, db_models.student.user_name),
    }

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

def hash_password(plain_password: str): # Function to hash the password
    salt: bytes = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str): # Function to verify the password
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))