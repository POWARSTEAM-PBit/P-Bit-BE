from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from email_validator import validate_email, EmailNotValidError
from db.init_engine import get_db, engine
from db import db_models
from utils import api_resp, error_resp

db_models.Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/class")

@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED, responses={})
async def register(payload: str, db: Session = Depends(get_db)):
    print("HELLO")