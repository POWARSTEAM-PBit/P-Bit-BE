from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from email_validator import validate_email, EmailNotValidError
from db.init_engine import get_db, engine
from db import db_models
from utils import api_resp, error_resp
from typing import List

db_models.Base.metadata.create_all(bind=engine)

class create_class_input(BaseModel):
    class_name: str
    class_description: str
    tag: List[str]

router = APIRouter(prefix="/class")

@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED, responses={})
async def create_class(payload: create_class_input, db: Session = Depends(get_db)):
    ## check that user_id exists in user table

    ## Check that the valid user has already created a class with the same name if so
    ##then dont allow

    