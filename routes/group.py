from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import random

from db.init_engine import get_db
from db import db_models
from utils import (
    api_resp, error_resp, 
    validate_group_name, validate_group_icon
)
from middleware import get_current_user

router = APIRouter(prefix="/classroom")

# Pydantic models for request/response
class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    icon: str = Field(..., min_length=1, max_length=10)

class GroupUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class StudentAddToGroup(BaseModel):
    student_id: str = Field(..., min_length=1)

# Create group
@router.post("/{classroom_id}/groups", tags=["group"], status_code=status.HTTP_201_CREATED)
async def create_group(
    classroom_id: str,
    payload: GroupCreate,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate input
    is_valid_name, name_error = validate_group_name(payload.name)
    if not is_valid_name:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=name_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_icon, icon_error = validate_group_icon(payload.icon)
    if not is_valid_icon:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=icon_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can create groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Create new group
    new_group = db_models.Group(
        id=str(uuid.uuid4()),
        classroom_id=classroom_id,
        name=payload.name,
        icon=payload.icon
    )
    
    try:
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Group created successfully",
                data={
                    "id": new_group.id,
                    "classroom_id": new_group.classroom_id,
                    "name": new_group.name,
                    "icon": new_group.icon,
                    "created_at": new_group.created_at.isoformat() if new_group.created_at else None
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to create group",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get classroom groups
@router.get("/{classroom_id}/groups", tags=["group"], status_code=status.HTTP_200_OK)
async def get_classroom_groups(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user has access
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if user is owner or member
    is_owner = classroom.owner_id == current_user.user_id
    is_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first() is not None
    
    if not (is_owner or is_member):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Access denied",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all groups for this classroom
    groups = db.query(db_models.Group).filter(
        db_models.Group.classroom_id == classroom_id
    ).all()
    
    groups_data = []
    for group in groups:
        # Count students in this group
        student_count = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.group_id == group.id
        ).count()
        
        groups_data.append({
            "id": group.id,
            "classroom_id": group.classroom_id,
            "name": group.name,
            "icon": group.icon,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "student_count": student_count
        })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Classroom groups retrieved successfully",
            data=groups_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get classroom students
@router.get("/{classroom_id}/students", tags=["group"], status_code=status.HTTP_200_OK)
async def get_classroom_students(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user has access
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if user is owner or member
    is_owner = classroom.owner_id == current_user.user_id
    is_member = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first() is not None
    
    if not (is_owner or is_member):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Access denied",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all students (both registered and anonymous) in this classroom
    students_data = []
    
    # Get registered students
    registered_students = db.query(db_models.User, db_models.ClassMember).join(
        db_models.ClassMember, db_models.ClassMember.user_id == db_models.User.user_id
    ).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.User.user_type == db_models.UserType.STUDENT
    ).all()
    
    for user, membership in registered_students:
        # Get group assignment
        group_membership = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.student_id == user.user_id,
            db_models.GroupMembership.student_type == "registered"
        ).first()
        
        group_info = None
        if group_membership:
            group = db.query(db_models.Group).filter(
                db_models.Group.id == group_membership.group_id
            ).first()
            if group:
                group_info = {
                    "group_id": group.id,
                    "group_name": group.name
                }
        
        students_data.append({
            "id": user.user_id,
            "first_name": user.first_name,
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.user_id if "@" in user.user_id else None,
            "group_id": group_info["group_id"] if group_info else None,
            "group_name": group_info["group_name"] if group_info else None,
            "joined_at": membership.joined_at.isoformat() if membership.joined_at else None,
            "student_type": "registered"
        })
    
    # Get anonymous students
    anonymous_students = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == classroom_id
    ).all()
    
    for student in anonymous_students:
        # Get group assignment
        group_membership = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.student_id == student.student_id,
            db_models.GroupMembership.student_type == "anonymous"
        ).first()
        
        group_info = None
        if group_membership:
            group = db.query(db_models.Group).filter(
                db_models.Group.id == group_membership.group_id
            ).first()
            if group:
                group_info = {
                    "group_id": group.id,
                    "group_name": group.name
                }
        
        students_data.append({
            "id": student.student_id,
            "first_name": student.first_name,
            "name": student.first_name,
            "email": None,
            "group_id": group_info["group_id"] if group_info else None,
            "group_name": group_info["group_name"] if group_info else None,
            "joined_at": student.joined_at.isoformat() if student.joined_at else None,
            "student_type": "anonymous"
        })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Classroom students retrieved successfully",
            data=students_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Add student to group
@router.post("/{classroom_id}/groups/{group_id}/students", tags=["group"], status_code=status.HTTP_200_OK)
async def add_student_to_group(
    classroom_id: str,
    group_id: str,
    payload: StudentAddToGroup,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can manage groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Check if group exists and belongs to this classroom
    group = db.query(db_models.Group).filter(
        db_models.Group.id == group_id,
        db_models.Group.classroom_id == classroom_id
    ).first()
    
    if not group:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Group not found",
                error_type="group_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if student exists in this classroom
    student_exists = False
    student_type = None
    
    # Check if it's a registered student
    registered_student = db.query(db_models.User).join(
        db_models.ClassMember, db_models.ClassMember.user_id == db_models.User.user_id
    ).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.User.user_id == payload.student_id,
        db_models.User.user_type == db_models.UserType.STUDENT
    ).first()
    
    if registered_student:
        student_exists = True
        student_type = "registered"
    else:
        # Check if it's an anonymous student
        anonymous_student = db.query(db_models.AnonymousStudent).filter(
            db_models.AnonymousStudent.student_id == payload.student_id,
            db_models.AnonymousStudent.class_id == classroom_id
        ).first()
        
        if anonymous_student:
            student_exists = True
            student_type = "anonymous"
    
    if not student_exists:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Student not found in this classroom",
                error_type="student_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if student is already in a group
    existing_membership = db.query(db_models.GroupMembership).filter(
        db_models.GroupMembership.student_id == payload.student_id,
        db_models.GroupMembership.student_type == student_type
    ).first()
    
    if existing_membership:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Student is already assigned to a group",
                error_type="student_already_in_group"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    # Create new membership
    new_membership = db_models.GroupMembership(
        id=str(uuid.uuid4()),
        group_id=group_id,
        student_id=payload.student_id,
        student_type=student_type
    )
    
    try:
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Student added to group successfully",
                data={
                    "student_id": new_membership.student_id,
                    "group_id": new_membership.group_id,
                    "assigned_at": new_membership.assigned_at.isoformat() if new_membership.assigned_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to add student to group",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Remove student from group
@router.delete("/{classroom_id}/groups/{group_id}/students/{student_id}", tags=["group"], status_code=status.HTTP_200_OK)
async def remove_student_from_group(
    classroom_id: str,
    group_id: str,
    student_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can manage groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the membership
    membership = db.query(db_models.GroupMembership).filter(
        db_models.GroupMembership.group_id == group_id,
        db_models.GroupMembership.student_id == student_id
    ).first()
    
    if not membership:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Student is not in this group",
                error_type="membership_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        db.delete(membership)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Student removed from group"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to remove student from group",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Randomly distribute students
@router.post("/{classroom_id}/groups/random-distribute", tags=["group"], status_code=status.HTTP_200_OK)
async def randomly_distribute_students(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can manage groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all groups in this classroom
    groups = db.query(db_models.Group).filter(
        db_models.Group.classroom_id == classroom_id
    ).all()
    
    if not groups:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="No groups found in this classroom",
                error_type="no_groups_found"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Get all students (both registered and anonymous) not already in groups
    unassigned_students = []
    
    # Get unassigned registered students
    registered_students = db.query(db_models.User).join(
        db_models.ClassMember, db_models.ClassMember.user_id == db_models.User.user_id
    ).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.User.user_type == db_models.UserType.STUDENT
    ).all()
    
    for student in registered_students:
        existing_membership = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.student_id == student.user_id,
            db_models.GroupMembership.student_type == "registered"
        ).first()
        
        if not existing_membership:
            unassigned_students.append({
                "student_id": student.user_id,
                "student_type": "registered"
            })
    
    # Get unassigned anonymous students
    anonymous_students = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == classroom_id
    ).all()
    
    for student in anonymous_students:
        existing_membership = db.query(db_models.GroupMembership).filter(
            db_models.GroupMembership.student_id == student.student_id,
            db_models.GroupMembership.student_type == "anonymous"
        ).first()
        
        if not existing_membership:
            unassigned_students.append({
                "student_id": student.student_id,
                "student_type": "anonymous"
            })
    
    if not unassigned_students:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="No unassigned students found",
                error_type="no_unassigned_students"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Randomly distribute students
    random.shuffle(unassigned_students)
    distributed_count = 0
    
    try:
        for i, student in enumerate(unassigned_students):
            group = groups[i % len(groups)]  # Round-robin distribution
            
            new_membership = db_models.GroupMembership(
                id=str(uuid.uuid4()),
                group_id=group.id,
                student_id=student["student_id"],
                student_type=student["student_type"]
            )
            
            db.add(new_membership)
            distributed_count += 1
        
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Students distributed successfully",
                data={
                    "distributed_count": distributed_count,
                    "groups_used": len(groups)
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to distribute students",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Update group name
@router.put("/{classroom_id}/groups/{group_id}", tags=["group"], status_code=status.HTTP_200_OK)
async def update_group_name(
    classroom_id: str,
    group_id: str,
    payload: GroupUpdate,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate input
    is_valid_name, name_error = validate_group_name(payload.name)
    if not is_valid_name:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=name_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can manage groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Check if group exists and belongs to this classroom
    group = db.query(db_models.Group).filter(
        db_models.Group.id == group_id,
        db_models.Group.classroom_id == classroom_id
    ).first()
    
    if not group:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Group not found",
                error_type="group_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        group.name = payload.name
        db.commit()
        db.refresh(group)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Group name updated successfully",
                data={
                    "id": group.id,
                    "name": group.name,
                    "icon": group.icon,
                    "updated_at": group.updated_at.isoformat() if group.updated_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to update group name",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Delete group
@router.delete("/{classroom_id}/groups/{group_id}", tags=["group"], status_code=status.HTTP_200_OK)
async def delete_group(
    classroom_id: str,
    group_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == classroom_id
    ).first()
    
    if not classroom:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Classroom not found",
                error_type="classroom_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    if classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom owner can manage groups",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Check if group exists and belongs to this classroom
    group = db.query(db_models.Group).filter(
        db_models.Group.id == group_id,
        db_models.Group.classroom_id == classroom_id
    ).first()
    
    if not group:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Group not found",
                error_type="group_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        # Delete the group (cascade will handle memberships)
        db.delete(group)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Group deleted successfully"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to delete group",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
