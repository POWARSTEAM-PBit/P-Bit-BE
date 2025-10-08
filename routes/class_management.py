from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional
import uuid

from db.init_engine import get_db
from db import db_models
from utils import api_resp, error_resp, validate_pin_code, validate_first_name, validate_passphrase
from middleware import get_current_user

router = APIRouter(prefix="/class")

# ---------- Pydantic models ----------
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

class FindAnonymousUser(BaseModel):
    passphrase: str = Field(..., min_length=1, max_length=12)
    first_name: str = Field(..., min_length=1, max_length=50)
    pin_code: str = Field(..., min_length=4, max_length=4)

class UpdateStudentPin(BaseModel):
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

class ClassRename(BaseModel):
    # New class name
    name: str = Field(..., min_length=1, max_length=100)

# Create a new class

# ---------- Create class (teacher only) ----------
@router.post("/create", tags=["class"], status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate, 
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    """
    Create a class for the current teacher.
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
    except Exception:
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

# ---------- Join class (logged-in user) ----------
@router.post("/join", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class(
    payload: ClassJoin,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find class by passphrase
    """
    Add the current user (student/teacher) into a class by passphrase.
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
    
    # Prevent duplicate membership (also enforced by DB unique constraint)
    exists = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_obj.id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first()
    
    if exists:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="You are already a member of this class", 
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
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
    except Exception:
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

# ---------- Join class anonymously (temp student) ----------
@router.post("/join-anonymous", tags=["class"], status_code=status.HTTP_200_OK)
async def join_class_anonymous(
    payload: ClassJoinAnonymous,
    db: Session = Depends(get_db)
):
    # Validate input
    is_valid_passphrase, passphrase_error = validate_passphrase(payload.passphrase)
    if not is_valid_passphrase:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=passphrase_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_name, name_error = validate_first_name(payload.first_name)
    if not is_valid_name:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=name_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_pin, pin_error = validate_pin_code(payload.pin_code)
    if not is_valid_pin:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=pin_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
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
    
    # Check if a student with the same name already exists in the classroom
    existing_anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == class_obj.id,
        db_models.AnonymousStudent.first_name == payload.first_name.strip()
    ).first()
    
    if existing_anonymous_student:
    tmp_student_id = generate_tmp_user(payload.first_name)

    # If user exists, validate PIN and flags; otherwise create a temp one
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
            last_name="",   # empty last name for anonymous student
            password="",    # no password for anonymous student
            user_type=db_models.UserType.STUDENT,
            pin_code=payload.pin_code,
            pin_reset_required=False,
        )
        
        try:
            db.add(temp_user)
            db.commit()
            db.refresh(temp_user)
            user_id = temp_user.user_id
        except Exception:
            db.rollback()
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="Failed to create temporary user", 
                    error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                ).dict(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    # Prevent duplicate membership
    exists = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_obj.id,
        db_models.ClassMember.user_id == user_id
    ).first()
    
    if exists:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="A student with this name already exists in this classroom. Please choose a different name or contact your teacher.",
                error_type="duplicate_name"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    # Generate unique student ID
    import time
    student_id = f"anon_{payload.first_name.lower().replace(' ', '_')}_{int(time.time())}"
    
    # Create new anonymous student
    new_anonymous_student = db_models.AnonymousStudent(
        student_id=student_id,
    new_member = db_models.ClassMember(
        id=str(uuid.uuid4()),
        class_id=class_obj.id,
        first_name=payload.first_name.strip(),
        pin_code=payload.pin_code,
    )
    
    try:
        db.add(new_anonymous_student)
        db.commit()
        db.refresh(new_anonymous_student)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message=f"Successfully joined {class_obj.name}", 
                data={
                    "class_id": class_obj.id,
                    "class_name": class_obj.name,
                    "subject": class_obj.subject,
                    "student_id": new_anonymous_student.student_id,
                    "first_name": new_anonymous_student.first_name,
                    "joined_at": new_anonymous_student.joined_at.isoformat() if new_anonymous_student.joined_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        # Check if it's an integrity error (duplicate name constraint violation)
        if "unique_name_per_classroom" in str(e) or "Duplicate entry" in str(e):
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="A student with this name already exists in this classroom. Please choose a different name or contact your teacher.",
                    error_type="duplicate_name"
                ).dict(),
                status_code=status.HTTP_409_CONFLICT,
            )
        else:
            return JSONResponse(
                content=api_resp(
                    success=False, 
                    message="Failed to join class", 
                    error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                ).dict(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

# Find existing anonymous user
@router.post("/find-anonymous-user", tags=["class"], status_code=status.HTTP_200_OK)
async def find_anonymous_user(
    payload: FindAnonymousUser,
    db: Session = Depends(get_db)
):
    # Validate input
    is_valid_passphrase, passphrase_error = validate_passphrase(payload.passphrase)
    if not is_valid_passphrase:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=passphrase_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_name, name_error = validate_first_name(payload.first_name)
    if not is_valid_name:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=name_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_pin, pin_error = validate_pin_code(payload.pin_code)
    if not is_valid_pin:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=pin_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
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
    
    # First check if user exists with exact name and PIN match
    anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == class_obj.id,
        db_models.AnonymousStudent.first_name == payload.first_name.strip(),
        db_models.AnonymousStudent.pin_code == payload.pin_code
    ).first()
    
    if anonymous_student:
        # User found with correct name and PIN - update last_active and return success
        try:
            anonymous_student.last_active = func.now()
            db.commit()
            db.refresh(anonymous_student)
        except Exception:
            # Log error but don't fail the request
            pass
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="User found",
                data={
                    "student_id": anonymous_student.student_id,
                    "class_id": anonymous_student.class_id,
                    "class_name": class_obj.name,
                    "subject": class_obj.subject,
                    "first_name": anonymous_student.first_name,
                    "pin_code": anonymous_student.pin_code,
                    "joined_at": anonymous_student.joined_at.isoformat() if anonymous_student.joined_at else None,
                    "last_active": anonymous_student.last_active.isoformat() if anonymous_student.last_active else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    
    # Check if name exists with different PIN
    name_exists = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == class_obj.id,
        db_models.AnonymousStudent.first_name == payload.first_name.strip()
    ).first()
    
    if name_exists:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="A student with this name already exists in this classroom",
                error_type="name_exists"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    
    # No user found with this name and PIN combination
    return JSONResponse(
        content=api_resp(
            success=False,
            message="No user found with this name and PIN combination",
            error_type="not_found"
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get anonymous students for classroom (teachers only)
@router.get("/{classroom_id}/anonymous-students", tags=["class"], status_code=status.HTTP_200_OK)
async def get_anonymous_students(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Teachers only",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the class and verify ownership
    class_obj = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
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
                message="Unauthorized - Only class owner can view anonymous students",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all anonymous students for this class
    anonymous_students = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == classroom_id
    ).order_by(db_models.AnonymousStudent.joined_at.desc()).all()
    
    students_data = []
    for student in anonymous_students:
        students_data.append({
            "student_id": student.student_id,
            "first_name": student.first_name,
            "pin_code": student.pin_code,
            "joined_at": student.joined_at.isoformat() if student.joined_at else None,
            "last_active": student.last_active.isoformat() if student.last_active else None
        })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Anonymous students retrieved successfully" if students_data else "No anonymous students found",
            data=students_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Update student PIN (teachers only)
@router.put("/{classroom_id}/anonymous-student/{student_id}/pin", tags=["class"], status_code=status.HTTP_200_OK)
async def update_student_pin(
    classroom_id: str,
    student_id: str,
    payload: UpdateStudentPin,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    if current_user.user_type != db_models.UserType.TEACHER:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Teachers only",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Validate PIN code
    is_valid_pin, pin_error = validate_pin_code(payload.pin_code)
    if not is_valid_pin:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=pin_error,
                error=error_resp(code=status.HTTP_400_BAD_REQUEST)
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Find the class and verify ownership
    class_obj = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
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
                message="Unauthorized - Only class owner can update student PINs",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the anonymous student
    anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.student_id == student_id,
        db_models.AnonymousStudent.class_id == classroom_id
    ).first()
    
    if not anonymous_student:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Student not found",
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        # Update the PIN
        anonymous_student.pin_code = payload.pin_code
        db.commit()
        db.refresh(anonymous_student)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="PIN updated successfully",
                data={
                    "student_id": anonymous_student.student_id,
                    "new_pin_code": anonymous_student.pin_code
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to update PIN",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------- Set PIN for anonymous student (placeholder) ----------
@router.post("/set-pin", tags=["class"], status_code=status.HTTP_200_OK)
async def set_pin_code(
    _payload: SetPinCode,
    _db: Session = Depends(get_db)
):
    # In a real flow, you need a way to identify the student (token/session).
    return JSONResponse(
        content=api_resp(
            success=False, 
            message="Student identification required for PIN setting", 
            error=error_resp(code=status.HTTP_400_BAD_REQUEST)
        ).dict(),
        status_code=status.HTTP_400_NOTHING_TO_DO_HERE if hasattr(status, "HTTP_400_NOTHING_TO_DO_HERE") else status.HTTP_400_BAD_REQUEST,
    )


# ---------- Get class members (owner or an enrolled member) ----------
@router.get("/{class_id}/members", tags=["class"], status_code=status.HTTP_200_OK)
async def get_class_members(
    class_id: str,
    # Use regex validation for query params (FastAPI style)
    sort_by: str = Query(default="joined_at", regex="^(joined_at|first_name|user_id)$"),
    order: str   = Query(default="asc",       regex="^(asc|desc)$"),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1) find class
    class_obj = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not class_obj:
    """
    Return all members in a class.
    - Only class owner or enrolled members can view.
    - Support sorting by joined_at / first_name / user_id and asc/desc.
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

    # 2) permission: owner OR enrolled member
    is_owner = (class_obj.owner_id == current_user.user_id)
    is_member = (
        db.query(db_models.ClassMember)
          .filter(
              db_models.ClassMember.class_id == class_id,
              db_models.ClassMember.user_id == current_user.user_id,
          )
          .first()
        is not None
    )
    if not (is_owner or is_member):
    
    is_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == current_user.user_id,
    ).first()

    if (not is_member) and (current_user.user_id != existing_class.owner_id):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Not authorized to view class members",
                error=error_resp(code=status.HTTP_403_FORBIDDEN),
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # 3) build query (join to avoid N+1)
    # Join to avoid N+1: fetch users + joined_at in one query
    q = (
        db.query(
            db_models.User.user_id,
            db_models.User.first_name,
            db_models.User.last_name,
            db_models.ClassMember.joined_at,
        )
        .join(db_models.ClassMember, db_models.ClassMember.user_id == db_models.User.user_id)
        .filter(db_models.ClassMember.class_id == class_id)
    )

    # 4) sorting
    if sort_by == "first_name":
        sort_col = db_models.User.first_name
    elif sort_by == "user_id":
        sort_col = db_models.User.user_id
    else:
        sort_col = db_models.ClassMember.joined_at

    q = q.order_by(sort_col.desc() if order.lower() == "desc" else sort_col.asc())

    # 5) execute & serialize (only required fields for classmates view)
    sort_col = {
        "first_name": db_models.User.first_name,
        "user_id": db_models.User.user_id,
        "joined_at": db_models.ClassMember.joined_at,
    }[sort_by]

    q = q.order_by(sort_col.desc() if order.lower() == "desc" else sort_col.asc())

    rows = q.all()
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

# >>> added: rename endpoint

# ---------- Rename class (owner only) ----------
@router.patch("/{class_id}/rename", tags=["class"], status_code=status.HTTP_200_OK)
async def rename_class(
    class_id: str,
    payload: ClassRename,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # find class
    class_obj = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not class_obj:
    """
    Rename an existing class (owner only). Idempotent if same name.
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

    # only owner (teacher) can rename
    if current_user.user_type != db_models.UserType.TEACHER or class_obj.owner_id != current_user.user_id:
    
    if existing_class.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Only the class owner can rename this class",
                error=error_resp(code=status.HTTP_403_FORBIDDEN),
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # normalize name
    
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
    if class_obj.name == new_name:
    class_data = {
        "id": existing_class.id,
        "name": existing_class.name,
        "subject": existing_class.subject,
        "description": existing_class.description,
        "passphrase": existing_class.passphrase,
        "owner_id": existing_class.owner_id,
        "created_at": existing_class.created_at.isoformat() if existing_class.created_at else None,
    }

    # If unchanged, return success (idempotent)
    if existing_class.name == new_name:
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Class name is unchanged",
                data={
                    "id": class_obj.id,
                    "name": class_obj.name,
                    "subject": class_obj.subject,
                    "description": class_obj.description,
                    "passphrase": class_obj.passphrase,
                    "owner_id": class_obj.owner_id,
                    "created_at": class_obj.created_at.isoformat() if class_obj.created_at else None,
                },
            ).dict(),
            status_code=status.HTTP_200_OK,
        )

    
    try:
        # update name
        class_obj.name = new_name
        db.add(class_obj)
        db.commit()
        db.refresh(class_obj)

        class_data["name"] = new_name

        return JSONResponse(
            content=api_resp(
                success=True,
                message="Class renamed successfully",
                data={
                    "id": class_obj.id,
                    "name": class_obj.name,
                    "subject": class_obj.subject,
                    "description": class_obj.description,
                    "passphrase": class_obj.passphrase,
                    "owner_id": class_obj.owner_id,
                    "created_at": class_obj.created_at.isoformat() if class_obj.created_at else None,
                },
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
# <<< added


# ---------- Reset student PIN (owner only) ----------
@router.post("/{class_id}/reset-student-pin/{student_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def reset_student_pin(
    class_id: str,
    student_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Owner can mark a student's PIN to be reset (and clear current PIN).
    """
    class_obj = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not class_obj:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if class_obj.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only the class owner can reset student PINs", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
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
        student.pin_reset_required = True
        student.pin_code = None  # clear old PIN
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
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to reset student PIN", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ---------- Remove student from class (owner only) ----------
@router.delete("/{class_id}/remove-student/{student_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def remove_student_from_class(
    class_id: str,
    student_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Owner removes a student from the class.
    """
    class_obj = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not class_obj:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Class not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if class_obj.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Only the class owner can remove students", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
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
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to remove student", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Remove anonymous student from class (teacher only)
@router.delete("/{class_id}/remove-anonymous-student/{student_id}", tags=["class"], status_code=status.HTTP_200_OK)
async def remove_anonymous_student_from_class(
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
    
    # Find the anonymous student
    anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.student_id == student_id,
        db_models.AnonymousStudent.class_id == class_id
    ).first()
    
    if not anonymous_student:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Anonymous student not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        # Remove any group memberships first
        group_memberships = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.student_id == student_id,
            db_models.GroupMembership.student_type == "anonymous"
        ).all()
        
        for membership in group_memberships:
            db.delete(membership)
        
        # Remove the anonymous student
        db.delete(anonymous_student)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Anonymous student removed from class successfully", 
                data={
                    "student_id": anonymous_student.student_id,
                    "first_name": anonymous_student.first_name,
                    "class_id": class_id
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to remove anonymous student from class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get classes owned by current user (teacher)

# ---------- Get classes owned by current user (teacher) ----------
@router.get("/owned", tags=["class"], status_code=status.HTTP_200_OK)
async def get_owned_classes(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher
    """
    Fetch all classes owned by the current teacher.
    - Uses a single GROUP BY to compute member_count (no N+1).
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

    # Aggregate: count members per class in one query
    owned = (
        db.query(
            db_models.Class.id,
            db_models.Class.name,
            db_models.Class.subject,
            db_models.Class.description,
            db_models.Class.passphrase,
            db_models.Class.owner_id,
            db_models.Class.created_at,
            func.count(db_models.ClassMember.id).label("member_count"),
        )
        .outerjoin(db_models.ClassMember, db_models.Class.id == db_models.ClassMember.class_id)
        .filter(db_models.Class.owner_id == current_user.user_id)
        .group_by(db_models.Class.id)
        .all()
    )

    data = [
        {
            "id": c.id,
            "name": c.name,
            "subject": c.subject,
            "description": c.description,
            "passphrase": c.passphrase,
            "owner_id": c.owner_id,
            "owner_name": f"{current_user.first_name} {current_user.last_name}",
            "member_count": int(c.member_count or 0),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in owned
    ]

    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Owned classes retrieved successfully", 
            data=data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get classes where current user is a member

# ---------- Get classes where current user is enrolled (student) ----------
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
    
    """
    Fetch all classes where the current user is a member.
    - One pass: join owner to build owner_name; group to count members (no N+1).
    """
    # Aliases to join ClassMember twice (one for "my membership", one for counting)
    MyMembership = aliased(db_models.ClassMember)
    AnyMembership = aliased(db_models.ClassMember)

    q = (
        db.query(
            db_models.Class.id,
            db_models.Class.name,
            db_models.Class.subject,
            db_models.Class.description,
            db_models.Class.owner_id,
            db_models.Class.created_at,
            db_models.User.first_name.label("owner_first"),
            db_models.User.last_name.label("owner_last"),
            func.count(AnyMembership.id).label("member_count"),
            MyMembership.joined_at.label("joined_at"),
        )
        # Classes where I am a member
        .join(MyMembership, MyMembership.class_id == db_models.Class.id)
        .filter(MyMembership.user_id == current_user.user_id)
        # Join to owner to get owner name
        .join(db_models.User, db_models.User.user_id == db_models.Class.owner_id)
        # Outer join to count everyone in the class
        .outerjoin(AnyMembership, AnyMembership.class_id == db_models.Class.id)
        .group_by(
            db_models.Class.id,
            db_models.User.first_name,
            db_models.User.last_name,
            MyMembership.joined_at,
        )
    )

    rows = q.all()
    data = [
        {
            "id": r.id,
            "name": r.name,
            "subject": r.subject,
            "description": r.description,
            "owner_id": r.owner_id,
            "owner_name": f"{r.owner_first} {r.owner_last}" if r.owner_first else "Unknown",
            "member_count": int(r.member_count or 0),
            "joined_at": r.joined_at.isoformat() if r.joined_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Enrolled classes retrieved successfully", 
            data=classes_data
            data=data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Delete a class (only by owner)

# ---------- Delete class (owner only) ----------
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
    """
    Delete a class (owner only).
    """
    cls = db.query(db_models.Class).filter(db_models.Class.id == class_id).first()
    if not cls:
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
    if cls.owner_id != current_user.user_id:
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
        db.delete(cls)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Class deleted successfully", 
                data=None
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
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

# ---------- Leave class (non-owner) ----------
@router.delete("/{class_id}/leave", tags=["class"], status_code=status.HTTP_200_OK)
async def leave_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Find the membership
    """
    Allow a member to leave the class.
    - Owner cannot leave their own class (must delete).
    """
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
    if membership.class_obj.owner_id == current_user.user_id:
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
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to leave class", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get student-specific data (groups and devices) for a classroom
@router.get("/{class_id}/student-data", tags=["class"], status_code=status.HTTP_200_OK)
async def get_student_data(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is enrolled in the class
    class_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == class_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first()
    
    if not class_member:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="You are not enrolled in this class", 
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    try:
        # Get groups the student belongs to
        student_groups = db.query(db_models.Group).join(
            db_models.GroupMembership,
            db_models.Group.id == db_models.GroupMembership.group_id
        ).filter(
            db_models.Group.classroom_id == class_id,
            db_models.GroupMembership.student_id == current_user.user_id,
            db_models.GroupMembership.student_type == "registered"
        ).all()
        
        groups_data = []
        for group in student_groups:
            # Get devices assigned to this group
            group_devices = db.query(db_models.Device).join(
                db_models.DeviceAssignment,
                db_models.Device.id == db_models.DeviceAssignment.device_id
            ).filter(
                db_models.DeviceAssignment.classroom_id == class_id,
                db_models.DeviceAssignment.assignment_type == "group",
                db_models.DeviceAssignment.assignment_id == group.id
            ).all()
            
            group_devices_data = []
            for device in group_devices:
                group_devices_data.append({
                    "id": device.id,
                    "nickname": device.nickname,
                    "mac_address": device.mac_address,
                    "battery_level": device.battery_level,
                    "is_active": device.is_active,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None
                })
            
                groups_data.append({
                    "id": group.id,
                    "name": group.name,
                    "icon": group.icon,
                    "devices": group_devices_data
                })
            
            # Get devices assigned directly to the student
        student_devices = db.query(db_models.Device).join(
            db_models.DeviceAssignment,
            db_models.Device.id == db_models.DeviceAssignment.device_id
        ).filter(
            db_models.DeviceAssignment.classroom_id == class_id,
            db_models.DeviceAssignment.assignment_type == "student",
            db_models.DeviceAssignment.assignment_id == current_user.user_id
        ).all()
        
        student_devices_data = []
        for device in student_devices:
            student_devices_data.append({
                "id": device.id,
                "nickname": device.nickname,
                "mac_address": device.mac_address,
                "battery_level": device.battery_level,
                "is_active": device.is_active,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            })
        
        # Get public devices (unassigned devices)
        public_devices = db.query(db_models.Device).join(
            db_models.DeviceAssignment,
            db_models.Device.id == db_models.DeviceAssignment.device_id
        ).filter(
            db_models.DeviceAssignment.classroom_id == class_id,
            db_models.DeviceAssignment.assignment_type == "unassigned"
        ).all()
        
        public_devices_data = []
        for device in public_devices:
            public_devices_data.append({
                "id": device.id,
                "nickname": device.nickname,
                "mac_address": device.mac_address,
                "battery_level": device.battery_level,
                "is_active": device.is_active,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            })
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Student data retrieved successfully", 
                data={
                    "groups": groups_data,
                    "assigned_devices": student_devices_data,
                    "public_devices": public_devices_data
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to retrieve student data", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get student-specific data for anonymous students
@router.get("/{class_id}/anonymous-student-data", tags=["class"], status_code=status.HTTP_200_OK)
async def get_anonymous_student_data(
    class_id: str,
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    db: Session = Depends(get_db)
):
    # Find the anonymous student
    anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == class_id,
        db_models.AnonymousStudent.first_name == first_name,
        db_models.AnonymousStudent.pin_code == pin_code
    ).first()
    
    if not anonymous_student:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Anonymous student not found", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        # Get groups the anonymous student belongs to
        student_groups = db.query(db_models.Group).join(
            db_models.GroupMembership,
            db_models.Group.id == db_models.GroupMembership.group_id
        ).filter(
            db_models.Group.classroom_id == class_id,
            db_models.GroupMembership.student_id == anonymous_student.student_id,
            db_models.GroupMembership.student_type == "anonymous"
        ).all()
        
        groups_data = []
        for group in student_groups:
            # Get devices assigned to this group
            group_devices = db.query(db_models.Device).join(
                db_models.DeviceAssignment,
                db_models.Device.id == db_models.DeviceAssignment.device_id
            ).filter(
                db_models.DeviceAssignment.classroom_id == class_id,
                db_models.DeviceAssignment.assignment_type == "group",
                db_models.DeviceAssignment.assignment_id == group.id
            ).all()
            
            group_devices_data = []
            for device in group_devices:
                group_devices_data.append({
                    "id": device.id,
                    "nickname": device.nickname,
                    "mac_address": device.mac_address,
                    "battery_level": device.battery_level,
                    "is_active": device.is_active,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None
                })
            
            groups_data.append({
                "id": group.id,
                "name": group.name,
                "icon": group.icon,
                "devices": group_devices_data
            })
        
        # Get devices assigned directly to the anonymous student
        student_devices = db.query(db_models.Device).join(
            db_models.DeviceAssignment,
            db_models.Device.id == db_models.DeviceAssignment.device_id
        ).filter(
            db_models.DeviceAssignment.classroom_id == class_id,
            db_models.DeviceAssignment.assignment_type == "student",
            db_models.DeviceAssignment.assignment_id == anonymous_student.student_id
        ).all()
        
        student_devices_data = []
        for device in student_devices:
            student_devices_data.append({
                "id": device.id,
                "nickname": device.nickname,
                "mac_address": device.mac_address,
                "battery_level": device.battery_level,
                "is_active": device.is_active,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            })
        
        # Get public devices (unassigned devices)
        public_devices = db.query(db_models.Device).join(
            db_models.DeviceAssignment,
            db_models.Device.id == db_models.DeviceAssignment.device_id
        ).filter(
            db_models.DeviceAssignment.classroom_id == class_id,
            db_models.DeviceAssignment.assignment_type == "unassigned"
        ).all()
        
        public_devices_data = []
        for device in public_devices:
            public_devices_data.append({
                "id": device.id,
                "nickname": device.nickname,
                "mac_address": device.mac_address,
                "battery_level": device.battery_level,
                "is_active": device.is_active,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            })
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Anonymous student data retrieved successfully", 
                data={
                    "groups": groups_data,
                    "assigned_devices": student_devices_data,
                    "public_devices": public_devices_data
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message="Failed to retrieve anonymous student data", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# ---------- Helpers ----------
def generate_passphrase(length=8):
    """Generate an easy-to-type unique passphrase (A–Z + digits, no O/0/1/I/L)."""
    alphabet = string.ascii_uppercase + string.digits
    for ch in ("0", "O", "1", "I", "L"):
        alphabet = alphabet.replace(ch, "")
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(length))
        if len(set(code)) > 1:  # not all same char
            return code

def generate_pin_code():
    """Generate a 4-digit PIN code."""
    return "".join(secrets.choice(string.digits) for _ in range(4))

def generate_tmp_user(first_name: str):
    """Create a temp user_id like student_{name}_{timestamp}."""
    return f"student_{first_name.lower()}_{int(time.time())}"
