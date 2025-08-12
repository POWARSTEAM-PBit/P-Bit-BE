from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from db.init_engine import get_db, engine
from db import db_models
from pydantic import BaseModel
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