from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime, timedelta

from db.init_engine import get_db
from db import db_models
from utils import (
    api_resp, error_resp, 
    validate_mac_address, validate_nickname, validate_assignment_type
)
from middleware import get_current_user
from sqlalchemy import func
from typing import Optional
from db.init_engine import get_db
from db import db_models as m

router = APIRouter(prefix="/device", tags=["device"])


# ------------------------------
# Helpers
# ------------------------------
def api_resp(success: bool, message: str, data=None):
    """Uniform API envelope."""
    return {"success": success, "message": message, "data": data}


# Pydantic models for request/response
class DeviceRegister(BaseModel):
    mac_address: str = Field(..., min_length=17, max_length=17)
    nickname: str = Field(..., min_length=2, max_length=20)

class DeviceAssign(BaseModel):
    classroom_id: str = Field(..., min_length=1)
    assignment_type: str = Field(..., min_length=1)
    assignment_id: Optional[str] = Field(None)

class DeviceDataInput(BaseModel):
    device_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    light: Optional[float] = Field(None, ge=0, le=100000)
    sound: Optional[float] = Field(None, ge=0, le=200)

class DeviceDataResponse(BaseModel):
    id: str
    device_id: str
    timestamp: datetime
    temperature: Optional[float]
    humidity: Optional[float]
    light: Optional[float]
    sound: Optional[float]
    created_at: datetime


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
    classroom_id: str,
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
        db_models.DeviceAssignment.classroom_id == classroom_id
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

# Update device assignment
@router.put("/{device_id}/assignment", tags=["device"], status_code=status.HTTP_200_OK)
async def update_device_assignment(
    device_id: str,
    classroom_id: str,
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
                message="Unauthorized - Only classroom owner can update device assignments",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Find the existing assignment
    assignment = db.query(db_models.DeviceAssignment).filter(
        db_models.DeviceAssignment.device_id == device_id,
        db_models.DeviceAssignment.classroom_id == classroom_id
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
        # Update the assignment
        assignment.assignment_type = payload.assignment_type
        assignment.assignment_id = payload.assignment_id
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device assignment updated successfully",
                data={
                    "device_id": device_id,
                    "classroom_id": classroom_id,
                    "assignment_type": payload.assignment_type,
                    "assignment_id": payload.assignment_id
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to update device assignment",
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

# Get device by ID for anonymous students
@router.get("/{device_id}/anonymous", tags=["device"], status_code=status.HTTP_200_OK)
async def get_device_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    db: Session = Depends(get_db)
):
    """
    Get device details by device ID for anonymous students.
    """
    try:
        # Verify anonymous student exists and has access to the classroom
        anonymous_student = db.query(db_models.AnonymousStudent).filter(
            db_models.AnonymousStudent.class_id == class_id,
            db_models.AnonymousStudent.first_name == first_name,
            db_models.AnonymousStudent.pin_code == pin_code
        ).first()
        
        if not anonymous_student:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Invalid student credentials",
                    error=error_resp(code=status.HTTP_401_UNAUTHORIZED)
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Find the device
        device = db.query(db_models.Device).filter(
            db_models.Device.id == device_id
        ).first()
        
        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found",
                    error=error_resp(code=status.HTTP_404_NOT_FOUND)
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if device is assigned to the classroom the anonymous student is in
        device_assignment = db.query(db_models.DeviceAssignment).filter(
            db_models.DeviceAssignment.device_id == device_id,
            db_models.DeviceAssignment.classroom_id == class_id
        ).first()
        
        if not device_assignment:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not assigned to this classroom",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device retrieved successfully",
                data={
                    "id": device.id,
                    "mac_address": device.mac_address,
                    "nickname": device.nickname,
                    "is_active": device.is_active,
                    "battery_level": device.battery_level,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "created_at": device.created_at.isoformat(),
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device by ID
@router.get("/{device_id}", tags=["device"], status_code=status.HTTP_200_OK)
async def get_device(
    device_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get device details by device ID.
    """
    try:
        # Find the device
        device = db.query(db_models.Device).filter(
            db_models.Device.id == device_id
        ).first()
        
        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found",
                    error=error_resp(code=status.HTTP_404_NOT_FOUND)
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if user has access to this device
        # User can access if they own the device or if it's assigned to a classroom they're in
        has_access = False
        
        if device.user_id == current_user.user_id:
            has_access = True
        else:
            # Check if device is assigned to a classroom the user is in
            classroom_access = db.query(db_models.DeviceAssignment).join(
                db_models.ClassMember,
                db_models.DeviceAssignment.classroom_id == db_models.ClassMember.class_id
            ).filter(
                db_models.DeviceAssignment.device_id == device_id,
                db_models.ClassMember.user_id == current_user.user_id
            ).first()
            
            if classroom_access:
                has_access = True
        
        if not has_access:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied to device",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device retrieved successfully",
                data={
                    "id": device.id,
                    "mac_address": device.mac_address,
                    "nickname": device.nickname,
                    "is_active": device.is_active,
                    "battery_level": device.battery_level,
                    "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    "created_at": device.created_at.isoformat(),
                    "updated_at": device.updated_at.isoformat() if device.updated_at else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device",
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

# Device Data Endpoints

@router.post("/data", tags=["device"], status_code=status.HTTP_201_CREATED)
async def add_device_data(
    payload: DeviceDataInput,
    db: Session = Depends(get_db)
):
    """
    Add new sensor data for a device.
    This endpoint is designed to be called by external devices.
    """
    try:
        # Verify device exists
        device = db.query(db_models.Device).filter(
            db_models.Device.id == payload.device_id
        ).first()
        
        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found",
                    error=error_resp(code=status.HTTP_404_NOT_FOUND)
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Create new device data record
        device_data = db_models.DeviceData(
            id=str(uuid.uuid4()),
            device_id=payload.device_id,
            timestamp=payload.timestamp,
            temperature=payload.temperature,
            humidity=payload.humidity,
            light=payload.light,
            sound=payload.sound
        )
        
        db.add(device_data)
        
        # Update device last_seen and battery if provided
        device.last_seen = payload.timestamp
        
        db.commit()
        db.refresh(device_data)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device data added successfully",
                data={
                    "id": device_data.id,
                    "device_id": device_data.device_id,
                    "timestamp": device_data.timestamp.isoformat(),
                    "temperature": float(device_data.temperature) if device_data.temperature else None,
                    "humidity": float(device_data.humidity) if device_data.humidity else None,
                    "light": float(device_data.light) if device_data.light else None,
                    "sound": float(device_data.sound) if device_data.sound else None
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
        
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to add device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@router.get("/{device_id}/data", tags=["device"], status_code=status.HTTP_200_OK)
async def get_device_data(
    device_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get device sensor data with optional time filtering.
    """
    try:
        # Verify device exists and user has access
        device = db.query(db_models.Device).filter(
            db_models.Device.id == device_id
        ).first()
        
        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found",
                    error=error_resp(code=status.HTTP_404_NOT_FOUND)
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if user has access to this device
        # User can access if they own the device or if it's assigned to a classroom they're in
        has_access = False
        
        if device.user_id == current_user.user_id:
            has_access = True
        else:
            # Check if device is assigned to a classroom the user is in
            classroom_access = db.query(db_models.DeviceAssignment).join(
                db_models.ClassMember,
                db_models.DeviceAssignment.classroom_id == db_models.ClassMember.class_id
            ).filter(
                db_models.DeviceAssignment.device_id == device_id,
                db_models.ClassMember.user_id == current_user.user_id
            ).first()
            
            if classroom_access:
                has_access = True
        
        if not has_access:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied to device data",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Build query
        query = db.query(db_models.DeviceData).filter(
            db_models.DeviceData.device_id == device_id
        )
        
        if start_time:
            query = query.filter(db_models.DeviceData.timestamp >= start_time)
        
        if end_time:
            query = query.filter(db_models.DeviceData.timestamp <= end_time)
        
        # Get data ordered by timestamp (newest first)
        data_records = query.order_by(desc(db_models.DeviceData.timestamp)).limit(limit).all()
        
        # Format response data
        data_list = []
        for record in data_records:
            data_list.append({
                "id": record.id,
                "device_id": record.device_id,
                "timestamp": record.timestamp.isoformat(),
                "temperature": float(record.temperature) if record.temperature else None,
                "humidity": float(record.humidity) if record.humidity else None,
                "light": float(record.light) if record.light else None,
                "sound": float(record.sound) if record.sound else None,
                "created_at": record.created_at.isoformat()
            })
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device data retrieved successfully",
                data={
                    "device_id": device_id,
                    "total_records": len(data_list),
                    "data": data_list
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get latest device data for anonymous students
@router.get("/{device_id}/data/latest/anonymous", tags=["device"], status_code=status.HTTP_200_OK)
async def get_latest_device_data_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    db: Session = Depends(get_db)
):
    """
    Get latest device data for anonymous students.
    """
    try:
        # Verify anonymous student exists and has access to the classroom
        anonymous_student = db.query(db_models.AnonymousStudent).filter(
            db_models.AnonymousStudent.class_id == class_id,
            db_models.AnonymousStudent.first_name == first_name,
            db_models.AnonymousStudent.pin_code == pin_code
        ).first()
        
        if not anonymous_student:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Invalid student credentials",
                    error=error_resp(code=status.HTTP_401_UNAUTHORIZED)
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Check if device is assigned to the classroom
        device_assignment = db.query(db_models.DeviceAssignment).filter(
            db_models.DeviceAssignment.device_id == device_id,
            db_models.DeviceAssignment.classroom_id == class_id
        ).first()
        
        if not device_assignment:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not assigned to this classroom",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Get latest device data
        latest_data = db.query(db_models.DeviceData).filter(
            db_models.DeviceData.device_id == device_id
        ).order_by(db_models.DeviceData.timestamp.desc()).first()
        
        if not latest_data:
            return JSONResponse(
                content=api_resp(
                    success=True,
                    message="No data available for this device",
                    data={"data": None}
                ).dict(),
                status_code=status.HTTP_200_OK,
            )
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Latest device data retrieved successfully",
                data={
                    "data": {
                        "id": latest_data.id,
                        "device_id": latest_data.device_id,
                        "timestamp": latest_data.timestamp.isoformat(),
                        "temperature": float(latest_data.temperature) if latest_data.temperature else None,
                        "humidity": float(latest_data.humidity) if latest_data.humidity else None,
                        "light": float(latest_data.light) if latest_data.light else None,
                        "sound": float(latest_data.sound) if latest_data.sound else None,
                        "created_at": latest_data.created_at.isoformat()
                    }
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device data with time filtering for anonymous students
@router.get("/{device_id}/data/anonymous", tags=["device"], status_code=status.HTTP_200_OK)
async def get_device_data_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="End time (ISO format)"),
    limit: Optional[int] = Query(100, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get device data with time filtering for anonymous students.
    """
    try:
        # Verify anonymous student exists and has access to the classroom
        anonymous_student = db.query(db_models.AnonymousStudent).filter(
            db_models.AnonymousStudent.class_id == class_id,
            db_models.AnonymousStudent.first_name == first_name,
            db_models.AnonymousStudent.pin_code == pin_code
        ).first()
        
        if not anonymous_student:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Invalid student credentials",
                    error=error_resp(code=status.HTTP_401_UNAUTHORIZED)
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Check if device is assigned to the classroom
        device_assignment = db.query(db_models.DeviceAssignment).filter(
            db_models.DeviceAssignment.device_id == device_id,
            db_models.DeviceAssignment.classroom_id == class_id
        ).first()
        
        if not device_assignment:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not assigned to this classroom",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Build query for device data
        query = db.query(db_models.DeviceData).filter(
            db_models.DeviceData.device_id == device_id
        )
        
        # Apply time filters if provided
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                query = query.filter(db_models.DeviceData.timestamp >= start_dt)
            except ValueError:
                return JSONResponse(
                    content=api_resp(
                        success=False,
                        message="Invalid start_time format. Use ISO format.",
                        error=error_resp(code=status.HTTP_400_BAD_REQUEST)
                    ).dict(),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                query = query.filter(db_models.DeviceData.timestamp <= end_dt)
            except ValueError:
                return JSONResponse(
                    content=api_resp(
                        success=False,
                        message="Invalid end_time format. Use ISO format.",
                        error=error_resp(code=status.HTTP_400_BAD_REQUEST)
                    ).dict(),
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
        
        # Order by timestamp and apply limit
        query = query.order_by(db_models.DeviceData.timestamp.desc()).limit(limit)
        
        # Execute query
        device_data = query.all()
        
        # Transform data
        data_list = []
        for data in device_data:
            data_list.append({
                "id": data.id,
                "device_id": data.device_id,
                "timestamp": data.timestamp.isoformat(),
                "temperature": float(data.temperature) if data.temperature else None,
                "humidity": float(data.humidity) if data.humidity else None,
                "light": float(data.light) if data.light else None,
                "sound": float(data.sound) if data.sound else None,
                "created_at": data.created_at.isoformat()
            })
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device data retrieved successfully",
                data={
                    "data": data_list,
                    "count": len(data_list)
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@router.get("/{device_id}/data/latest", tags=["device"], status_code=status.HTTP_200_OK)
async def get_latest_device_data(
    device_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the most recent sensor data for a device.
    """
    try:
        # Verify device exists and user has access (same logic as above)
        device = db.query(db_models.Device).filter(
            db_models.Device.id == device_id
        ).first()
        
        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found",
                    error=error_resp(code=status.HTTP_404_NOT_FOUND)
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check access (simplified for brevity - same logic as above)
        has_access = device.user_id == current_user.user_id
        if not has_access:
            # Check classroom access
            classroom_access = db.query(db_models.DeviceAssignment).join(
                db_models.ClassMember,
                db_models.DeviceAssignment.classroom_id == db_models.ClassMember.class_id
            ).filter(
                db_models.DeviceAssignment.device_id == device_id,
                db_models.ClassMember.user_id == current_user.user_id
            ).first()
            has_access = classroom_access is not None
        
        if not has_access:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied to device data",
                    error=error_resp(code=status.HTTP_403_FORBIDDEN)
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Get latest data record
        latest_data = db.query(db_models.DeviceData).filter(
            db_models.DeviceData.device_id == device_id
        ).order_by(desc(db_models.DeviceData.timestamp)).first()
        
        if not latest_data:
            return JSONResponse(
                content=api_resp(
                    success=True,
                    message="No data available for this device",
                    data={
                        "device_id": device_id,
                        "data": None
                    }
                ).dict(),
                status_code=status.HTTP_200_OK,
            )
        
        # Format response
        data_response = {
            "id": latest_data.id,
            "device_id": latest_data.device_id,
            "timestamp": latest_data.timestamp.isoformat(),
            "temperature": float(latest_data.temperature) if latest_data.temperature else None,
            "humidity": float(latest_data.humidity) if latest_data.humidity else None,
            "light": float(latest_data.light) if latest_data.light else None,
            "sound": float(latest_data.sound) if latest_data.sound else None,
            "created_at": latest_data.created_at.isoformat()
        }
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Latest device data retrieved successfully",
                data={
                    "device_id": device_id,
                    "data": data_response
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve latest device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
def normalize_mac(raw: str) -> Optional[str]:
    """
    Normalize MAC address to a 12-char uppercase string without separators.
    Accepts forms like: 'a1:b2:c3:d4:e5:f6', 'A1-B2-C3-D4-E5-F6', 'a1b2c3d4e5f6'.
    Returns None if invalid.
    """
    if not raw:
        return None
    s = raw.replace(":", "").replace("-", "").strip().upper()
    if len(s) != 12 or not s.isalnum():
        return None
    return s


# ------------------------------
# Endpoints
# ------------------------------
@router.get("/data", status_code=status.HTTP_200_OK)
def get_device_data(
    mac: str = Query(..., description="Device MAC (any format, e.g. A1:B2:C3:D4:E5:F6)"),
    limit: int = Query(500, ge=1, le=5000, description="Max number of points"),
    type: Optional[str] = Query(None, description="Optional sensor type filter, e.g. temp"),
    order: str = Query("asc", pattern="^(asc|desc)$", description="Sort by timestamp"),
    db: Session = Depends(get_db),
):
    """
    Return time-series data points for a device.
    - Normalizes the MAC
    - Optional filter by 'type'
    - Sort by timestamp ASC/DESC
    """
    mac_norm = normalize_mac(mac)
    if mac_norm is None:
        return JSONResponse(
            api_resp(False, "Invalid MAC address format", data=[]),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # (Optional) ensure device exists; if not, return empty data
    exists = db.query(m.Device).filter(m.Device.mac_addr == mac_norm).first()
    if not exists:
        return JSONResponse(api_resp(True, "Device not found", data=[]))

    q = (
        db.query(m.Data.timestamp, m.Data.type, m.Data.value)
        .filter(m.Data.mac_addr == mac_norm)
    )
    if type:
        q = q.filter(m.Data.type == type)

    q = q.order_by(m.Data.timestamp.desc() if order == "desc" else m.Data.timestamp.asc())
    rows = q.limit(limit).all()

    series = [
        {
            "ts": r.timestamp.isoformat() if r.timestamp else None,
            "type": r.type,
            "value": float(r.value) if r.value is not None else None,
        }
        for r in rows
    ]

    return JSONResponse(api_resp(True, "ok", series))


@router.get("/metrics", status_code=status.HTTP_200_OK)
def get_metrics(db: Session = Depends(get_db)):
    """
    Aggregate metrics per (device, type):
    - count, min, max, avg, latest {value, ts}
    """
    # base stats per (mac, type)
    stats = (
        db.query(
            m.Data.mac_addr,
            m.Data.type,
            func.count().label("count"),
            func.min(m.Data.value).label("min"),
            func.max(m.Data.value).label("max"),
            func.avg(m.Data.value).label("avg"),
        )
        .group_by(m.Data.mac_addr, m.Data.type)
        .all()
    )

    # latest value per (mac, type)
    latest_sub = (
        db.query(
            m.Data.mac_addr,
            m.Data.type,
            func.max(m.Data.timestamp).label("max_ts"),
        )
        .group_by(m.Data.mac_addr, m.Data.type)
        .subquery()
    )

    latest_rows = (
        db.query(m.Data.mac_addr, m.Data.type, m.Data.value, m.Data.timestamp)
        .join(
            latest_sub,
            (m.Data.mac_addr == latest_sub.c.mac_addr)
            & (m.Data.type == latest_sub.c.type)
            & (m.Data.timestamp == latest_sub.c.max_ts),
        )
        .all()
    )

    latest_map = {
        (r.mac_addr, r.type): {
            "value": float(r.value) if r.value is not None else None,
            "ts": r.timestamp.isoformat() if r.timestamp else None,
        }
        for r in latest_rows
    }

    out = []
    for r in stats:
        key = (r.mac_addr, r.type)
        out.append(
            {
                "mac": r.mac_addr,
                "type": r.type,
                "count": int(r.count) if r.count is not None else 0,
                "min": float(r.min) if r.min is not None else None,
                "max": float(r.max) if r.max is not None else None,
                "avg": float(r.avg) if r.avg is not None else None,
                "latest": latest_map.get(key),
            }
        )

    return JSONResponse(api_resp(True, "ok", out))
