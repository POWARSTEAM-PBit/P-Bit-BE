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

class ClassJoinAnonymous(BaseModel):
    passphrase: str = Field(..., min_length=1, max_length=12)
    first_name: str = Field(..., min_length=1, max_length=50)
    pin_code: str = Field(..., min_length=4, max_length=4)

class SetPinCode(BaseModel):
    pin_code: str = Field(..., min_length=4, max_length=4)

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

class StudentInfo(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    user_type: str
    joined_at: str
    pin_code: Optional[str]
    pin_reset_required: bool

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

# Join a class (for logged-in users)
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

# Join a class anonymously (no login required)
@router.post("/join-anonymous", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class_anonymous(
    payload: ClassJoinAnonymous,
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
    
    # Create a temporary student user
    import time
    student_id = f"student_{payload.first_name.lower()}_{int(time.time())}"
    
    # Check if this student ID already exists
    existing_user = db.query(db_models.User).filter(
        db_models.User.user_id == student_id
    ).first()
    
    if existing_user:
        user_id = existing_user.user_id
        # Check if PIN reset is required
        if existing_user.pin_reset_required:
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="PIN reset required. Please set a new PIN code.", 
                    error=error_resp(code=status.HTTP_400_BAD_REQUEST)
                ).dict(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        # Verify PIN code for existing user
        if existing_user.pin_code != payload.pin_code:
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="Invalid PIN code", 
                    error=error_resp(code=status.HTTP_401_UNAUTHORIZED)
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
    else:
        # Create a new temporary student user with PIN
        temp_user = db_models.User(
            user_id=student_id,
            first_name=payload.first_name,
            last_name="",  # Empty for anonymous students
            password="",   # No password for anonymous students
            user_type=db_models.UserType.STUDENT,
            pin_code=payload.pin_code,
            pin_reset_required=False,
        )
        
        try:
            db.add(temp_user)
            db.commit()
            db.refresh(temp_user)
            user_id = temp_user.user_id
        except Exception as e:
            db.rollback()
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="Failed to create temporary user", 
                    error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                ).dict(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    # Check if user is already a member of this class
    existing_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_obj.id,
        db_models.ClassMember.user_id == user_id
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
        user_id=user_id,
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
                    "student_id": user_id,
                    "first_name": payload.first_name,
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

# Set PIN code for anonymous student (when reset is required)
@router.post("/set-pin", tags=["class"], status_code=status.HTTP_200_OK)
async def set_pin_code(
    payload: SetPinCode,
    db: Session = Depends(get_db)
):
    # Find user by student ID (this would typically come from the request)
    # For now, we'll need to identify the student somehow
    # This endpoint would need to be called with student identification
    
    # This is a placeholder - in practice, you'd need to identify which student
    # is setting their PIN (perhaps through a temporary token or session)
    
    return JSONResponse(
        content=api_resp(
            success=False, 
            message="Student identification required for PIN setting", 
            error=error_resp(code=status.HTTP_400_BAD_REQUEST)
        ).dict(),
        status_code=status.HTTP_400_BAD_REQUEST,
    )

# Get class members (teacher only)
@router.get("/{class_id}/members", tags=["class"], status_code=status.HTTP_200_OK)
async def get_class_members(
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
                message="Only the class owner can view members", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all members with their details
    members = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id
    ).all()
    
    members_data = []
    for member in members:
        user = db.query(db_models.User).filter(
            db_models.User.user_id == member.user_id
        ).first()
        
        if user:
            members_data.append({
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user.user_type.value,
                "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                "pin_code": user.pin_code if user.user_type == db_models.UserType.STUDENT else None,
                "pin_reset_required": user.pin_reset_required if user.user_type == db_models.UserType.STUDENT else False
            })
    
    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Class members retrieved successfully", 
            data=members_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Reset student PIN code (teacher only)
@router.post("/{class_id}/reset-student-pin/{student_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def reset_student_pin(
    class_id: str,
    student_id: str,
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
                message="Only the class owner can reset student PINs", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the student
    student = db.query(db_models.User).filter(
        db_models.User.user_id == student_id,
        db_models.User.user_type == db_models.UserType.STUDENT
    ).first()
    
    if not student:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Student not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if student is a member of this class
    membership = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == student_id
    ).first()
    
    if not membership:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Student is not a member of this class", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Set PIN reset flag
        student.pin_reset_required = True
        student.pin_code = None  # Clear the old PIN
        db.commit()
        db.refresh(student)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Student PIN reset successfully", 
                data={
                    "student_id": student.user_id,
                    "first_name": student.first_name,
                    "pin_reset_required": True
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to reset student PIN", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Remove student from class (teacher only)
@router.delete("/{class_id}/remove-student/{student_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def remove_student_from_class(
    class_id: str,
    student_id: str,
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
                message="Only the class owner can remove students", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the student
    student = db.query(db_models.User).filter(
        db_models.User.user_id == student_id,
        db_models.User.user_type == db_models.UserType.STUDENT
    ).first()
    
    if not student:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Student not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Find the membership
    membership = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == student_id
    ).first()
    
    if not membership:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Student is not a member of this class", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        # Remove the membership
        db.delete(membership)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Student removed from class successfully", 
                data={
                    "student_id": student.user_id,
                    "first_name": student.first_name,
                    "class_id": class_id
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to remove student from class", 
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
