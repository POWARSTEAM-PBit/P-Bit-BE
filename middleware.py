from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session


from db.init_engine import get_db
from db import db_models

SECRET_KEY = "gyukgyukt78i*Y&*GHFDE"  # Replace with a strong secret key in env variables!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/user/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from jose import JWTError, ExpiredSignatureError

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> db_models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print("No username in token payload")
            raise credentials_exception
    except ExpiredSignatureError:
        print("Token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print(f"JWT decode error: {e}")
        raise credentials_exception

    print(f"Token valid for user: {username}")

    db_user = db.query(db_models.User).filter(db_models.User.user_id == username).first()
    if db_user is None:
        print("User not found in DB")
        raise credentials_exception
    
    return db_user

