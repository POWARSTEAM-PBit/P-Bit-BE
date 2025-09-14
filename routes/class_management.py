from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import secrets
import string
import time
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

# >>> added: rename model
class ClassRename(BaseModel):
    # new class name
    name: str = Field(..., min_length=1, max_length=100)
# <<< added


@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate, 
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    The following function creates a class for a given teacher
    """
    
    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only teachers can create classes", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    unique_passphrase = generate_passphrase()

    new_class = db_models.Class(
        id=str(uuid.uuid4()),
        name=payload.name,
        subject=payload.subject,
        description=payload.description,
        passphrase=unique_passphrase,
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

@router.post("/join", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class(
    payload: ClassJoin,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    The following function assigns a teacher/student (logged in users) into the 
    class.
    """
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

@router.post("/join-anonymous", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class_anonymous(
    payload: ClassJoinAnonymous,
    db: Session = Depends(get_db)
):
    """
    The following function allows non-logged in users to join a class
    """
    
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
    
    tmp_student_id = generate_tmp_user(payload.first_name)
    
    # Check if this student ID already exists
    existing_user = db.query(db_models.User).filter(
        db_models.User.user_id == tmp_student_id
    ).first()
    
    if existing_user:
        user_id = existing_user.user_id
        
        if existing_user.pin_reset_required:
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="PIN reset required. Please set a new PIN code.", 
                    error=error_resp(code=status.HTTP_400_BAD_REQUEST)
                ).dict(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
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
        temp_user = db_models.User(
            user_id=tmp_student_id,
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
    existing_member_class = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_obj.id,
        db_models.ClassMember.user_id == user_id
    ).first()
    
    if existing_member_class:
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

    
# Get class members (owner or enrolled member)
@router.get("/{class_id}/members", tags=["class"], status_code=status.HTTP_200_OK)
async def get_class_members(
    class_id: str,
    sort_by: str = Query(default="joined_at", pattern="^(joined_at|first_name|user_id)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The following function retrieves all the class members of a class, if the class
    does not exist. Then an exception is raised
    """
    
    existing_class = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not existing_class:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Class not found",
                error=error_resp(code=status.HTTP_404_NOT_FOUND),
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    is_member = db.query(db_models.ClassMember).filter(
              db_models.ClassMember.class_id == class_id,
              db_models.ClassMember.user_id == current_user.user_id,
          ).first()

    if (not is_member) and (current_user.user_id != existing_class.owner_id):
        return JSONResponse(
                content=api_resp(
                success=False,
                message="Not authorised to view students from this class",
                error=error_resp(code=status.HTTP_403_FORBIDDEN),
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    

    # join to avoid N+1
    class_members = (
        db.query(db_models.User.user_id, db_models.User.first_name,
            db_models.User.last_name,
            db_models.ClassMember.joined_at,
        )
        .join(db_models.ClassMember, db_models.ClassMember.user_id == db_models.User.user_id)
        .filter(db_models.ClassMember.class_id == class_id)
    )

    if sort_by == "first_name":
        sort_col = db_models.User.first_name
    elif sort_by == "user_id":
        sort_col = db_models.User.user_id
    else:
        sort_col = db_models.ClassMember.joined_at

    class_members = class_members.order_by(sort_col.desc() if order.lower() == "desc" else sort_col.asc())

    # 5) execute & serialize (only required fields for classmates view)
    rows = class_members.all()
    members_data = [
        {
            "user_id": r.user_id,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "joined_at": r.joined_at.isoformat() if r.joined_at else None,
        }
        for r in rows
    ]

    return JSONResponse(
        content=api_resp(
            success=True,
            message="Class members retrieved successfully",
            data=members_data,
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

@router.patch("/{class_id}/rename", tags=["class"], status_code=status.HTTP_200_OK)
async def rename_class(
    class_id: str,
    payload: ClassRename,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    The following function renames an existing class
    """
    
    existing_class = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not existing_class:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Class not found",
                error=error_resp(code=status.HTTP_404_NOT_FOUND),
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if (existing_class.owner_id != current_user.user_id):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Only the class owner can rename this class",
                error=error_resp(code=status.HTTP_403_FORBIDDEN),
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    class_data = {
        "id": existing_class.id,
        "name": existing_class.name,
        "subject": existing_class.subject,
        "description": existing_class.description,
        "passphrase": existing_class.passphrase,
        "owner_id": existing_class.owner_id,
        "created_at": existing_class.created_at.isoformat() if existing_class.created_at else None,
    }

    
    new_name = payload.name.strip()
    if not new_name:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Name cannot be empty",
                error=error_resp(code=status.HTTP_400_BAD_REQUEST),
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # if unchanged, still return success (idempotent)
    if existing_class.name == new_name:
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Class name is unchanged",
                data=class_data,
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    
    class_data["name"] = new_name

    try:
        existing_class.name = new_name
        db.add(existing_class)
        db.commit()
        db.refresh(existing_class)

        return JSONResponse(
            content=api_resp(
                success=True,
                message="Class renamed successfully",
                data=class_data,
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to rename class",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR),
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    """
    The following function get's all classes owned by a teacher
    """

    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Only teachers can own classes", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    
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

@router.get("/enrolled", tags=["class"], status_code=status.HTTP_200_OK)
async def get_enrolled_classes(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    The following function retrieves all of the classes that the 
    student is apart of. 
    """

    student_enrolled_classes = db.query(db_models.Class).join(db_models.ClassMember).filter(
        db_models.ClassMember.user_id == current_user.user_id
    ).all()
    
    student_classes = []
    for _class in student_enrolled_classes:
        # Get owner name
        owner = db.query(db_models.User).filter(
            db_models.User.user_id == _class.owner_id
        ).first()
        
        # Get member count
        member_count = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == _class.id
        ).count()
        
        # Get join date for current user
        membership = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == _class.id,
            db_models.ClassMember.user_id == current_user.user_id
        ).first()
        
        student_classes.append({
            "id": _class.id,
            "name": _class.name,
            "subject": _class.subject,
            "description": _class.description,
            "owner_id": _class.owner_id,
            "owner_name": f"{owner.first_name} {owner.last_name}" if owner else "Unknown",
            "member_count": member_count,
            "joined_at": membership.joined_at.isoformat() if membership and membership.joined_at else None,
            "created_at": _class.created_at.isoformat() if _class.created_at else None
        })
    
    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Enrolled classes retrieved successfully", 
            data=student_classes
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

@router.delete("/{class_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def delete_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    The following function delete's a valid class
    """
    
    does_class_exist = db.query(db_models.Class).filter(
        db_models.Class.id == class_id
    ).first()
    
    if not does_class_exist:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if does_class_exist.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only the class owner can delete the class", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    try:
        db.delete(does_class_exist)
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

@router.delete("/{class_id}/leave", tags=["class"], status_code=status.HTTP_200_OK)
async def leave_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    The following function allows students to leave the registered class, class-owners (teachers) cannot leave there
    own class. 
    """
    
    is_user_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first()
    
    if not is_user_member:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="You are not a member of this class", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if is_user_member.class_obj.owner_id == current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class owners cannot leave their own class. Delete the class instead.", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        db.delete(is_user_member)
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
def generate_passphrase(length=8):
    """Generate an easy-to-type unique passphrase"""
    # Use only letters and numbers, avoiding confusing characters
    alphabet = string.ascii_uppercase + string.digits
    # Remove confusing characters: 0, O, 1, I, L
    alphabet = alphabet.replace('0', '').replace('O', '').replace('1', '').replace('I', '').replace('L', '')

    while True:
        passphrase = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure it's not all the same character
        if len(set(passphrase)) > 1:
            return passphrase

def generate_pin_code():
    """Generate a 4-digit PIN code"""
    return ''.join(secrets.choice(string.digits) for _ in range(4))

def generate_tmp_user(first_name: str):
    return f"student_{first_name.lower()}_{int(time.time())}"