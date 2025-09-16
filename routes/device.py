from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timedelta

from db.init_engine import get_db
from db import db_models
from utils import (
    api_resp, error_resp, 
    validate_mac_address, validate_nickname, validate_assignment_type
)
from middleware import get_current_user

router = APIRouter(prefix="/device")

# Pydantic models for request/response
class DeviceRegister(BaseModel):
    mac_address: str = Field(..., min_length=17, max_length=17)
    nickname: str = Field(..., min_length=2, max_length=20)

class DeviceAssign(BaseModel):
    classroom_id: str = Field(..., min_length=1)
    assignment_type: str = Field(..., min_length=1)
    assignment_id: Optional[str] = Field(None)

class DeviceUnassign(BaseModel):
    classroom_id: str = Field(..., min_length=1)

# Register new device
@router.post("/register", tags=["device"], status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegister,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate input
    is_valid_mac, mac_error = validate_mac_address(payload.mac_address)
    if not is_valid_mac:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=mac_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    is_valid_nickname, nickname_error = validate_nickname(payload.nickname)
    if not is_valid_nickname:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=nickname_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if MAC address already exists
    existing_device = db.query(db_models.Device).filter(
        db_models.Device.mac_address == payload.mac_address
    ).first()
    
    if existing_device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device with this MAC address already exists",
                error_type="duplicate_mac"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    # Check if nickname already exists for this user
    existing_nickname = db.query(db_models.Device).filter(
        db_models.Device.user_id == current_user.user_id,
        db_models.Device.nickname == payload.nickname
    ).first()
    
    if existing_nickname:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Nickname already exists for this user",
                error_type="duplicate_nickname"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    # Create new device
    new_device = db_models.Device(
        id=str(uuid.uuid4()),
        mac_address=payload.mac_address,
        nickname=payload.nickname,
        user_id=current_user.user_id,
        is_active=False,
        battery_level=0,
        last_seen=None
    )
    
    try:
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device registered successfully",
                data={
                    "id": new_device.id,
                    "mac_address": new_device.mac_address,
                    "nickname": new_device.nickname,
                    "user_id": new_device.user_id,
                    "is_active": new_device.is_active,
                    "battery_level": new_device.battery_level,
                    "last_seen": new_device.last_seen.isoformat() if new_device.last_seen else None,
                    "created_at": new_device.created_at.isoformat() if new_device.created_at else None
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to register device",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get user's devices
@router.get("/user-devices", tags=["device"], status_code=status.HTTP_200_OK)
async def get_user_devices(
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get all devices for the current user
    devices = db.query(db_models.Device).filter(
        db_models.Device.user_id == current_user.user_id
    ).all()
    
    devices_data = []
    for device in devices:
        # Get classroom assignments for this device
        assignments = db.query(db_models.DeviceAssignment).filter(
            db_models.DeviceAssignment.device_id == device.id
        ).all()
        
        classrooms = []
        for assignment in assignments:
            classroom = db.query(db_models.Class).filter(
                db_models.Class.id == assignment.classroom_id
            ).first()
            
            if classroom:
                classrooms.append({
                    "classroom_id": assignment.classroom_id,
                    "classroom_name": classroom.name,
                    "assignment_type": assignment.assignment_type,
                    "assignment_id": assignment.assignment_id
                })
        
        devices_data.append({
            "id": device.id,
            "mac_address": device.mac_address,
            "nickname": device.nickname,
            "is_active": device.is_active,
            "battery_level": device.battery_level,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "created_at": device.created_at.isoformat() if device.created_at else None,
            "classrooms": classrooms
        })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="User devices retrieved successfully",
            data=devices_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get classroom devices
@router.get("/classroom/{classroom_id}/devices", tags=["device"], status_code=status.HTTP_200_OK)
async def get_classroom_devices(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user is a teacher and owns the classroom
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
                message="Unauthorized - Only classroom owner can view devices",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all device assignments for this classroom
    assignments = db.query(db_models.DeviceAssignment).filter(
        db_models.DeviceAssignment.classroom_id == classroom_id
    ).all()
    
    assignments_data = []
    for assignment in assignments:
        device = db.query(db_models.Device).filter(
            db_models.Device.id == assignment.device_id
        ).first()
        
        if device:
            assignments_data.append({
                "id": assignment.id,
                "device_id": assignment.device_id,
                "classroom_id": assignment.classroom_id,
                "assignment_type": assignment.assignment_type,
                "assignment_id": assignment.assignment_id,
                "device": {
                    "id": device.id,
                    "mac_address": device.mac_address,
                    "nickname": device.nickname,
                    "is_active": device.is_active,
                    "battery_level": device.battery_level,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None
                }
            })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Classroom devices retrieved successfully",
            data=assignments_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Assign device to classroom
@router.post("/{device_id}/assign", tags=["device"], status_code=status.HTTP_200_OK)
async def assign_device(
    device_id: str,
    payload: DeviceAssign,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate assignment type
    is_valid_type, type_error = validate_assignment_type(payload.assignment_type)
    if not is_valid_type:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=type_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if device exists and belongs to user
    device = db.query(db_models.Device).filter(
        db_models.Device.id == device_id,
        db_models.Device.user_id == current_user.user_id
    ).first()
    
    if not device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device not found",
                error_type="device_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if classroom exists and user owns it
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == payload.classroom_id
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
                message="Unauthorized - Only classroom owner can assign devices",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Check if device is already assigned to this classroom
    existing_assignment = db.query(db_models.DeviceAssignment).filter(
        db_models.DeviceAssignment.device_id == device_id,
        db_models.DeviceAssignment.classroom_id == payload.classroom_id
    ).first()
    
    if existing_assignment:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device is already assigned to this classroom",
                error_type="duplicate_assignment"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    # Create new assignment
    new_assignment = db_models.DeviceAssignment(
        id=str(uuid.uuid4()),
        device_id=device_id,
        classroom_id=payload.classroom_id,
        assignment_type=payload.assignment_type,
        assignment_id=payload.assignment_id
    )
    
    try:
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device assigned successfully",
                data={
                    "id": new_assignment.id,
                    "device_id": new_assignment.device_id,
                    "classroom_id": new_assignment.classroom_id,
                    "assignment_type": new_assignment.assignment_type,
                    "assignment_id": new_assignment.assignment_id,
                    "created_at": new_assignment.created_at.isoformat() if new_assignment.created_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to assign device",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Unassign device from classroom
@router.delete("/{device_id}/unassign", tags=["device"], status_code=status.HTTP_200_OK)
async def unassign_device(
    device_id: str,
    payload: DeviceUnassign,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if device exists and belongs to user
    device = db.query(db_models.Device).filter(
        db_models.Device.id == device_id,
        db_models.Device.user_id == current_user.user_id
    ).first()
    
    if not device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device not found",
                error_type="device_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Find the assignment
    assignment = db.query(db_models.DeviceAssignment).filter(
        db_models.DeviceAssignment.device_id == device_id,
        db_models.DeviceAssignment.classroom_id == payload.classroom_id
    ).first()
    
    if not assignment:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device is not assigned to this classroom",
                error_type="assignment_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    try:
        db.delete(assignment)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device unassigned successfully"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to unassign device",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Delete device
@router.delete("/{device_id}", tags=["device"], status_code=status.HTTP_200_OK)
async def delete_device(
    device_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if device exists and belongs to user
    device = db.query(db_models.Device).filter(
        db_models.Device.id == device_id,
        db_models.Device.user_id == current_user.user_id
    ).first()
    
    if not device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device not found",
                error_type="device_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    # Check if device has any assignments
    assignments = db.query(db_models.DeviceAssignment).filter(
        db_models.DeviceAssignment.device_id == device_id
    ).all()
    
    if assignments:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Cannot delete device with active classroom assignments. Please unassign from all classrooms first.",
                error_type="device_has_assignments"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    try:
        db.delete(device)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device deleted successfully"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to delete device",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device by MAC address
@router.get("/mac/{mac_address}", tags=["device"], status_code=status.HTTP_200_OK)
async def get_device_by_mac(
    mac_address: str,
    db: Session = Depends(get_db)
):
    # Validate MAC address format
    is_valid_mac, mac_error = validate_mac_address(mac_address)
    if not is_valid_mac:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=mac_error,
                error_type="validation_error"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Find device by MAC address
    device = db.query(db_models.Device).filter(
        db_models.Device.mac_address == mac_address
    ).first()
    
    if not device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device not found",
                error_type="device_not_found"
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Device found",
            data={
                "id": device.id,
                "mac_address": device.mac_address,
                "nickname": device.nickname,
                "is_active": device.is_active,
                "battery_level": device.battery_level,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None
            }
        ).dict(),
        status_code=status.HTTP_200_OK,
    )
