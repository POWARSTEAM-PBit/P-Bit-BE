from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid

from db.init_engine import get_db
from db import db_models
from utils import api_resp, error_resp
from middleware import get_current_user

router = APIRouter(prefix="/class")

# Pydantic models for request/response
class ClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)

class ClassJoin(BaseModel):
    passphrase: str = Field(..., min_length=1, max_length=12)

class ClassResponse(BaseModel):
    id: str
    name: str
    subject: str
    description: Optional[str]
    passphrase: str
    owner_id: str
    owner_name: str
    member_count: int
    created_at: str

# Create a new class
@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate, 
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only teachers can create classes", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Generate unique passphrase
    passphrase = db_models.generate_passphrase()
    
    # Create new class
    new_class = db_models.Class(
        id=str(uuid.uuid4()),
        name=payload.name,
        subject=payload.subject,
        description=payload.description,
        passphrase=passphrase,
        owner_id=current_user.user_id,
    )
    
    try:
        db.add(new_class)
        db.commit()
        db.refresh(new_class)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Class created successfully", 
                data={
                    "id": new_class.id,
                    "name": new_class.name,
                    "subject": new_class.subject,
                    "description": new_class.description,
                    "passphrase": new_class.passphrase,
                    "owner_id": new_class.owner_id,
                    "created_at": new_class.created_at.isoformat() if new_class.created_at else None
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to create class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Join a class using passphrase
@router.post("/join", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class(
    payload: ClassJoin,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find class by passphrase
    class_obj = db.query(db_models.Class).filter(
        db_models.Class.passphrase == payload.passphrase
    ).first()
    
    if not class_obj:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Invalid passphrase", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if user is already a member
    existing_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_obj.id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first()
    
    if existing_member:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="You are already a member of this class", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Create new membership
    new_member = db_models.ClassMember(
        id=str(uuid.uuid4()),
        class_id=class_obj.id,
        user_id=current_user.user_id,
    )
    
    try:
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message=f"Successfully joined {class_obj.name}", 
                data={
                    "class_id": class_obj.id,
                    "class_name": class_obj.name,
                    "subject": class_obj.subject,
                    "joined_at": new_member.joined_at.isoformat() if new_member.joined_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to join class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get classes owned by current user (teacher)
@router.get("/owned", tags=["class"], status_code=status.HTTP_200_OK)
async def get_owned_classes(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only teachers can own classes", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get owned classes with member count
    owned_classes = db.query(db_models.Class).filter(
        db_models.Class.owner_id == current_user.user_id
    ).all()
    
    classes_data = []
    for class_obj in owned_classes:
        member_count = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == class_obj.id
        ).count()
        
        classes_data.append({
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": class_obj.subject,
            "description": class_obj.description,
            "passphrase": class_obj.passphrase,
            "owner_id": class_obj.owner_id,
            "owner_name": f"{current_user.first_name} {current_user.last_name}",
            "member_count": member_count,
            "created_at": class_obj.created_at.isoformat() if class_obj.created_at else None
        })
    
    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Owned classes retrieved successfully", 
            data=classes_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get classes where current user is a member
@router.get("/enrolled", tags=["class"], status_code=status.HTTP_200_OK)
async def get_enrolled_classes(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get classes where user is a member
    enrolled_classes = db.query(db_models.Class).join(
        db_models.ClassMember
    ).filter(
        db_models.ClassMember.user_id == current_user.user_id
    ).all()
    
    classes_data = []
    for class_obj in enrolled_classes:
        # Get owner name
        owner = db.query(db_models.User).filter(
            db_models.User.user_id == class_obj.owner_id
        ).first()
        
        # Get member count
        member_count = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == class_obj.id
        ).count()
        
        # Get join date for current user
        membership = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == class_obj.id,
            db_models.ClassMember.user_id == current_user.user_id
        ).first()
        
        classes_data.append({
            "id": class_obj.id,
            "name": class_obj.name,
            "subject": class_obj.subject,
            "description": class_obj.description,
            "owner_id": class_obj.owner_id,
            "owner_name": f"{owner.first_name} {owner.last_name}" if owner else "Unknown",
            "member_count": member_count,
            "joined_at": membership.joined_at.isoformat() if membership and membership.joined_at else None,
            "created_at": class_obj.created_at.isoformat() if class_obj.created_at else None
        })
    
    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Enrolled classes retrieved successfully", 
            data=classes_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Delete a class (only by owner)
@router.delete("/{class_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the class
    class_obj = db.query(db_models.Class).filter(
        db_models.Class.id == class_id
    ).first()
    
    if not class_obj:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if user is the owner
    if class_obj.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only the class owner can delete the class", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    try:
        # Delete the class (cascade will handle members)
        db.delete(class_obj)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Class deleted successfully", 
                data=None
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to delete class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Leave a class (remove membership)
@router.delete("/{class_id}/leave", tags=["class"], status_code=status.HTTP_200_OK)
async def leave_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the membership
    membership = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first()
    
    if not membership:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="You are not a member of this class", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if user is trying to leave their own class
    class_obj = db.query(db_models.Class).filter(
        db_models.Class.id == class_id
    ).first()
    
    if class_obj and class_obj.owner_id == current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class owners cannot leave their own class. Delete the class instead.", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        db.delete(membership)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Successfully left the class", 
                data=None
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to leave class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
