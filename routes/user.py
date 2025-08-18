from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from email_validator import validate_email, EmailNotValidError
import uuid
import bcrypt

from db.init_engine import get_db, engine
from db import db_models
from utils import api_resp, error_resp
from utils import REGISTER_SUCCESS_RESPONSE, INVALID_EMAIL_REGISTER_RESPONSE, INVALID_USER_TYPE_REGISTER_RESPONSE, VALIDATION_ERROR_REGISTER_RESPONSES, INTERNAL_SERVER_ERROR_REGISTER_RESPONSE
from utils import LOGIN_SUCCESS_RESPONSE, INVALID_EMAIL_RESPONSE, UNAUTHORIZED_RESPONSES, USER_NOT_FOUND_RESPONSE

db_models.Base.metadata.create_all(bind=engine)

class user_register(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)
    user_id: str
    user_type: db_models.UserType

class user_login(BaseModel):
    user_id: str
    password: str
    user_type: db_models.UserType

router = APIRouter(prefix="/user")

def hash_password(plain_password: str):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

@router.post("/register", tags=["user"], status_code=status.HTTP_201_CREATED, responses={
    201: REGISTER_SUCCESS_RESPONSE,
    400: INVALID_EMAIL_REGISTER_RESPONSE,
    401: INVALID_USER_TYPE_REGISTER_RESPONSE,
    422: VALIDATION_ERROR_REGISTER_RESPONSES,
    500: INTERNAL_SERVER_ERROR_REGISTER_RESPONSE,
})
async def register(payload: user_register, db: Session = Depends(get_db)):
    existing_user = db.query(db_models.User).filter(db_models.User.user_id == payload.user_id).first()
    if existing_user:
        return JSONResponse(
            content=api_resp(success=False, message="User already exists", error=error_resp(code=status.HTTP_422_UNPROCESSABLE_ENTITY)).dict(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if payload.user_type == db_models.UserType.TEACHER:
        try:
            validated = validate_email(payload.user_id)
            user_id = validated.email.lower()
        except EmailNotValidError as e:
            return JSONResponse(
                content=api_resp(False, f"Invalid email: {str(e)}", error=error_resp(status.HTTP_400_BAD_REQUEST)).dict(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    else:
        user_id = payload.user_id.strip()

    new_user = db_models.User(
        user_id=user_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        password=hash_password(payload.password),
        user_type=payload.user_type,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(False, "Failed to register", error=error_resp(status.HTTP_500_INTERNAL_SERVER_ERROR)).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return JSONResponse(
        content=api_resp(success=True, message="Register successful", data=None).dict(),
        status_code=status.HTTP_201_CREATED,
    )

@router.post("/login", tags=["user"], status_code=status.HTTP_200_OK, responses={
    200: LOGIN_SUCCESS_RESPONSE,
    400: INVALID_EMAIL_RESPONSE,
    401: UNAUTHORIZED_RESPONSES,
    404: USER_NOT_FOUND_RESPONSE,
})
async def login(user: user_login, request: Request, db: Session = Depends(get_db)):
    user_id = user.user_id

    if user.user_type == db_models.UserType.TEACHER:
        try:
            validated = validate_email(user.user_id)
            user_id = validated.email.lower()
        except EmailNotValidError as e:
            return JSONResponse(
                content=api_resp(False, f"Invalid email: {str(e)}", error=error_resp(status.HTTP_400_BAD_REQUEST)).dict(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    db_user = db.query(db_models.User).filter(
        db_models.User.user_id == user_id,
        db_models.User.user_type == user.user_type
    ).first()

    if not db_user:
        return JSONResponse(
            content=api_resp(success=False, message="User does not exist", error=error_resp(code=status.HTTP_404_NOT_FOUND)).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    if not verify_password(user.password, db_user.password):
        return JSONResponse(
            content=api_resp(success=False, message="Incorrect password", error=error_resp(status.HTTP_401_UNAUTHORIZED)).dict(),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return JSONResponse(
        content=api_resp(success=True, message="Login successful", data={"api_key": str(uuid.uuid4())}).dict(),
        status_code=status.HTTP_200_OK,
    )
