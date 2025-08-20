from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.init_engine import get_db, engine
from db import db_models
from utils import api_resp, error_resp
from typing import List
from middleware import get_current_user

db_models.Base.metadata.create_all(bind=engine)

class create_class_input(BaseModel):
    class_name: str
    class_description: str
    tag: List[str]

router = APIRouter(prefix="/class")

@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED, responses={})
async def create_class(payload: create_class_input, current_user: db_models.User = Depends(get_current_user), db: Session = Depends(get_db)):


    existing_class = db.query(db_models.Class).filter(
        db_models.Class.class_name == payload.class_name,
        db_models.Class.class_owner == current_user.user_id
    ).first()

    if existing_class:
        return JSONResponse(
            content=api_resp(success=False, message="Class already exists", error=error_resp(code=status.HTTP_422_UNPROCESSABLE_ENTITY)).dict(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    
    new_class = db_models.Class(
        class_name=payload.class_name,
        class_owner=current_user.user_id,
        class_description=payload.class_description,
    )

    try:
        db.add(new_class)
        db.commit()
        db.refresh(new_class)

        return JSONResponse(
            content=api_resp(success=True, message="Successfuly created class", data=None).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(False, "Failed to create class", error=error_resp(status.HTTP_500_INTERNAL_SERVER_ERROR)).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )