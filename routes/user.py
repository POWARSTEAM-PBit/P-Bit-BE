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
from utils import api_resp, error_resp
from utils import LOGIN_SUCCESS_RESPONSE, INVALID_EMAIL_RESPONSE, UNAUTHORIZED_RESPONSES, USER_NOT_FOUND_RESPONSE

router: APIRouter = APIRouter(prefix="/user")
db_models.Base.metadata.create_all(bind=engine)

class user_type(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"

class user_login(BaseModel):
    user_id: str  # either email or username
    password: str
    user_type: user_type

router = APIRouter()

@router.post(
    "/login", 
    tags=["user"], 
    status_code=status.HTTP_200_OK,
    responses={
        200: LOGIN_SUCCESS_RESPONSE,
        400: INVALID_EMAIL_RESPONSE,
        401: UNAUTHORIZED_RESPONSES,
        404: USER_NOT_FOUND_RESPONSE
    }
)
async def login(user: user_login, request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    user_model_id_map = {
        user_type.TEACHER: (db_models.teacher, db_models.teacher.email),
        user_type.STUDENT: (db_models.student, db_models.student.user_name),
    }

    model_info = user_model_id_map.get(user.user_type)

    if not model_info:
        content = api_resp(success=False, message="Invalid user type", error=error_resp(code=status.HTTP_401_UNAUTHORIZED)).dict()
        return JSONResponse(content=content, status_code=status.HTTP_401_UNAUTHORIZED)

    model_class, identifier_field = model_info

    if user.user_type == user_type.TEACHER:
        try:
            valid = validate_email(user.user_id)
            user.user_id = valid.email
        except EmailNotValidError as e:
            content = api_resp(success=False, message=f"Invalid email address: {str(e)}", error=error_resp(code=status.HTTP_400_BAD_REQUEST)).dict()
            return JSONResponse(content=content, status_code=status.HTTP_400_BAD_REQUEST)

    db_user = db.query(model_class).filter(identifier_field == user.user_id).first()

    if not db_user:
        content = api_resp(success=False, message="User does not exist", error=error_resp(code=status.HTTP_404_NOT_FOUND)).dict()
        return JSONResponse(content=content, status_code=status.HTTP_404_NOT_FOUND)

    if not verify_password(user.password, db_user.password):
        content = api_resp(success=False, message="Password is incorrect", error=error_resp(code=status.HTTP_401_UNAUTHORIZED)).dict()
        return JSONResponse(content=content, status_code=status.HTTP_401_UNAUTHORIZED)
    
    content = api_resp(success=True, message="Login successful", data={"api_key": str(uuid.uuid4())}).dict()
    return JSONResponse(content=content, status_code=status.HTTP_200_OK)




def hash_password(plain_password: str): # Function to hash the password
    salt: bytes = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str): # Function to verify the password
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))