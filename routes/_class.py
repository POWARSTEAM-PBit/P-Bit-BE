from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.init_engine import get_db, engine
from db import db_models
from utils import api_resp, error_resp
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from middleware import get_current_user

db_models.Base.metadata.create_all(bind=engine)

class create_class_input(BaseModel):
    class_name: str
    class_description: str
    tag: List[str]

router = APIRouter(prefix="/class")

def create_tags(tag_list: List[str], class_id: int, db: Session) -> Tuple[bool, Optional[str]]:
    """ The following function takes a list of tags and adds them to the Tag table"""
    for tag_name in tag_list:
        new_tag = db_models.Tag(tag_name=tag_name, class_id=class_id)
        try:
            db.add(new_tag)
            db.commit()
            db.refresh(new_tag)
        except Exception as e:
            db.rollback()
            return False, f"Failed to add tag '{tag_name}'"
    return True, None


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
        db.refresh(new_class)  # Get the generated class_id

        tag_success, tag_error_msg = create_tags(payload.tag, new_class.class_id, db)
        if not tag_success:
            return JSONResponse(
                content=api_resp(success=False, message=tag_error_msg, error=error_resp(code=status.HTTP_422_UNPROCESSABLE_ENTITY)).dict(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return JSONResponse(
            content=api_resp(success=True, message="Successfully created class and tags", data=None).dict(),
            status_code=status.HTTP_201_CREATED,
        )

    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(False, "Failed to create class", error=error_resp(status.HTTP_500_INTERNAL_SERVER_ERROR)).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )