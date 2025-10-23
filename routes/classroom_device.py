from fastapi import APIRouter, Depends, status, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime

from db.init_engine import get_db
from db import db_models
from utils import (
    api_resp, error_resp, 
    validate_assignment_type
)
from middleware import get_current_user

router = APIRouter(prefix="/classroom-device")

# Pydantic models for request/response
class ClassroomDeviceAdd(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100)
    assignment_type: str = Field(..., min_length=1)
    assignment_id: Optional[str] = Field(None)

class ClassroomDeviceUpdate(BaseModel):
    assignment_type: str = Field(..., min_length=1)
    assignment_id: Optional[str] = Field(None)

class BLEDataReading(BaseModel):
    timestamp: datetime
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    thermometer: Optional[float] = Field(None, ge=-50, le=100)
    humidity: Optional[float] = Field(None, ge=0, le=100)
    moisture: Optional[float] = Field(None, ge=0, le=100)
    light: Optional[float] = Field(None, ge=0, le=100000)
    sound: Optional[float] = Field(None, ge=0, le=200)
    battery_level: Optional[float] = Field(None, ge=0, le=100)

class BLEBatchRecord(BaseModel):
    readings: List[BLEDataReading] = Field(..., min_items=1, max_items=100)

# Get classroom devices
@router.get("/classroom/{classroom_id}/devices", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_classroom_devices(
    classroom_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all devices for a classroom"""
    # Check if user has access to the classroom
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
    
    # Check if user is teacher (owner) or student member
    is_teacher = classroom.owner_id == current_user.user_id
    is_student = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first() is not None
    
    if not (is_teacher or is_student):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Access denied to classroom",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Get all devices for this classroom
    devices = db.query(db_models.ClassroomDevice).filter(
        db_models.ClassroomDevice.classroom_id == classroom_id
    ).all()
    
    devices_data = []
    for device in devices:
        # Get assignment info
        assignment = db.query(db_models.ClassroomDeviceAssignment).filter(
            db_models.ClassroomDeviceAssignment.device_id == device.id
        ).first()
        
        # Get added by info
        added_by_name = "Unknown"
        if device.added_by_type == "teacher" and device.added_by_user:
            added_by_name = f"{device.added_by_user.first_name} {device.added_by_user.last_name}"
        elif device.added_by_type == "student" and device.added_by_student_id:
            # Get student info
            student = db.query(db_models.AnonymousStudent).filter(
                db_models.AnonymousStudent.student_id == device.added_by_student_id
            ).first()
            if student:
                added_by_name = f"Student {student.first_name}"
        
        devices_data.append({
            "id": device.id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "is_active": device.is_active,
            "battery_level": device.battery_level,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "added_by": {
                "type": device.added_by_type,
                "name": added_by_name
            },
            "assignment": {
                "type": assignment.assignment_type if assignment else "public",
                "id": assignment.assignment_id if assignment else None
            },
            "created_at": device.created_at.isoformat()
        })
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Classroom devices retrieved successfully",
            data=devices_data
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Add device to classroom
@router.post("/classroom/{classroom_id}/add", tags=["classroom-device"], status_code=status.HTTP_201_CREATED)
async def add_device_to_classroom(
    classroom_id: str,
    payload: ClassroomDeviceAdd,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a BLE device to a classroom"""
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
    
    # Check if classroom exists
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
    
    # Check if user has access to classroom
    is_teacher = classroom.owner_id == current_user.user_id
    is_student = db.query(db_models.ClassMember).filter(
        db_models.ClassMember.class_id == classroom_id,
        db_models.ClassMember.user_id == current_user.user_id
    ).first() is not None
    
    if not (is_teacher or is_student):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Access denied to classroom",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    # Check if device with this name already exists in classroom
    existing_device = db.query(db_models.ClassroomDevice).filter(
        db_models.ClassroomDevice.classroom_id == classroom_id,
        db_models.ClassroomDevice.device_name == payload.device_name
    ).first()
    
    if existing_device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Device '{payload.device_name}' is already connected to this classroom. Please talk to your teacher or choose a different device.",
                error_type="device_already_exists"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    try:
        # Create new classroom device
        new_device = db_models.ClassroomDevice(
            id=str(uuid.uuid4()),
            classroom_id=classroom_id,
            device_name=payload.device_name,
            device_type="ble",
            is_active=True,
            battery_level=0,
            last_seen=datetime.utcnow(),
            added_by_user_id=current_user.user_id if is_teacher else None,
            added_by_student_id=None,  # Will be set for anonymous students
            added_by_type="teacher" if is_teacher else "student"
        )
        db.add(new_device)
        db.flush()  # Get the ID
        
        # Create assignment
        new_assignment = db_models.ClassroomDeviceAssignment(
            id=str(uuid.uuid4()),
            device_id=new_device.id,
            assignment_type=payload.assignment_type,
            assignment_id=payload.assignment_id
        )
        db.add(new_assignment)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device added to classroom successfully",
                data={
                    "device_id": new_device.id,
                    "device_name": new_device.device_name,
                    "assignment_type": payload.assignment_type,
                    "assignment_id": payload.assignment_id
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        print(f"Error adding device to classroom: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Failed to add device: {str(e)}",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Add device to classroom (anonymous student)
@router.post("/classroom/{classroom_id}/add-anonymous", tags=["classroom-device"], status_code=status.HTTP_201_CREATED)
async def add_device_to_classroom_anonymous(
    classroom_id: str,
    payload: ClassroomDeviceAdd,
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    db: Session = Depends(get_db)
):
    """Add a BLE device to classroom by anonymous student"""
    # Verify anonymous student
    anonymous_student = db.query(db_models.AnonymousStudent).filter(
        db_models.AnonymousStudent.class_id == classroom_id,
        db_models.AnonymousStudent.first_name == first_name,
        db_models.AnonymousStudent.pin_code == pin_code
    ).first()
    
    if not anonymous_student:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Invalid student credentials",
                error_type="authentication_error"
            ).dict(),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    
    # Anonymous students can only add public devices
    if payload.assignment_type != "public":
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Anonymous students can only add public devices",
                error_type="invalid_assignment_type"
            ).dict(),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    # Check if device already exists
    existing_device = db.query(db_models.ClassroomDevice).filter(
        db_models.ClassroomDevice.classroom_id == classroom_id,
        db_models.ClassroomDevice.device_name == payload.device_name
    ).first()
    
    if existing_device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Device '{payload.device_name}' is already connected to this classroom. Please talk to your teacher or choose a different device.",
                error_type="device_already_exists"
            ).dict(),
            status_code=status.HTTP_409_CONFLICT,
        )
    
    try:
        # Create new classroom device
        new_device = db_models.ClassroomDevice(
            id=str(uuid.uuid4()),
            classroom_id=classroom_id,
            device_name=payload.device_name,
            device_type="ble",
            is_active=True,
            battery_level=0,
            last_seen=datetime.utcnow(),
            added_by_user_id=None,
            added_by_student_id=anonymous_student.student_id,
            added_by_type="anonymous"
        )
        db.add(new_device)
        db.flush()
        
        # Create public assignment
        new_assignment = db_models.ClassroomDeviceAssignment(
            id=str(uuid.uuid4()),
            device_id=new_device.id,
            assignment_type="public",
            assignment_id=None
        )
        db.add(new_assignment)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device added to classroom successfully",
                data={
                    "device_id": new_device.id,
                    "device_name": new_device.device_name,
                    "assignment_type": "public"
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        print(f"Error adding device to classroom: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Failed to add device: {str(e)}",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Update device assignment (teacher only)
@router.put("/{device_id}/assignment", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def update_device_assignment(
    device_id: str,
    payload: ClassroomDeviceUpdate,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update device assignment (teacher only)"""
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
    
    # Get device
    device = db.query(db_models.ClassroomDevice).filter(
        db_models.ClassroomDevice.id == device_id
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
    
    # Check if user is teacher of this classroom
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == device.classroom_id
    ).first()
    
    if not classroom or classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom teacher can update device assignments",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    try:
        # Update or create assignment
        assignment = db.query(db_models.ClassroomDeviceAssignment).filter(
            db_models.ClassroomDeviceAssignment.device_id == device_id
        ).first()
        
        if assignment:
            assignment.assignment_type = payload.assignment_type
            assignment.assignment_id = payload.assignment_id
            assignment.updated_at = datetime.utcnow()
        else:
            new_assignment = db_models.ClassroomDeviceAssignment(
                id=str(uuid.uuid4()),
                device_id=device_id,
                assignment_type=payload.assignment_type,
                assignment_id=payload.assignment_id
            )
            db.add(new_assignment)
        
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device assignment updated successfully",
                data={
                    "device_id": device_id,
                    "assignment_type": payload.assignment_type,
                    "assignment_id": payload.assignment_id
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        print(f"Error updating device assignment: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Failed to update device assignment: {str(e)}",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Remove device from classroom (teacher only)
@router.delete("/{device_id}", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def remove_device_from_classroom(
    device_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove device from classroom (teacher only)"""
    # Get device
    device = db.query(db_models.ClassroomDevice).filter(
        db_models.ClassroomDevice.id == device_id
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
    
    # Check if user is teacher of this classroom
    classroom = db.query(db_models.Class).filter(
        db_models.Class.id == device.classroom_id
    ).first()
    
    if not classroom or classroom.owner_id != current_user.user_id:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Unauthorized - Only classroom teacher can remove devices",
                error_type="unauthorized"
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN,
        )
    
    try:
        # Delete device (cascade will handle assignments and data)
        db.delete(device)
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device removed from classroom successfully"
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        db.rollback()
        print(f"Error removing device: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Failed to remove device: {str(e)}",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Record BLE batch data
@router.post("/record-ble-batch", tags=["classroom-device"], status_code=status.HTTP_201_CREATED)
async def record_ble_batch(
    request: Request,
    payload: BLEBatchRecord,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record BLE batch data for a classroom device"""
    try:
        # Get the device name from headers
        device_name = request.headers.get('X-Device-Name', 'P-BIT')
        classroom_id = request.headers.get('X-Classroom-ID')
        
        if not classroom_id:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Classroom ID required",
                    error_type="missing_classroom_id"
                ).dict(),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        
        # Validate classroom access for the current user
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

        # Check if user has access to this classroom
        has_access = False

        # Check if user is the classroom owner
        if classroom.owner_id == current_user.user_id:
            has_access = True

        # Check if user is a member of the classroom
        elif current_user.user_type == db_models.UserType.STUDENT:
            membership = db.query(db_models.ClassMember).filter(
                db_models.ClassMember.class_id == classroom_id,
                db_models.ClassMember.user_id == current_user.user_id
            ).first()
            if membership:
                has_access = True

        # Check if user is anonymous and has valid PIN for this classroom
        elif current_user.user_type == db_models.UserType.ANONYMOUS:
            # Anonymous users should have a valid PIN for this classroom
            if hasattr(current_user, 'pin_code') and current_user.pin_code:
                # This is a simplified check - in production you'd want more sophisticated validation
                has_access = True

        if not has_access:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied to classroom",
                    error_type="access_denied"
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Find the classroom device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.classroom_id == classroom_id,
            db_models.ClassroomDevice.device_name == device_name
        ).first()

        if not device:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Classroom device not found",
                    error_type="device_not_found"
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Record each reading
        recorded_count = 0
        for reading in payload.readings:
            try:
                new_data = db_models.ClassroomDeviceData(
                    id=str(uuid.uuid4()),
                    device_id=device.id,
                    timestamp=reading.timestamp,
                    temperature=reading.temperature,
                    thermometer=reading.thermometer,
                    humidity=reading.humidity,
                    moisture=reading.moisture,
                    light=reading.light,
                    sound=reading.sound,
                    battery_level=reading.battery_level
                )
                db.add(new_data)
                recorded_count += 1
            except Exception as e:
                print(f"Error recording individual reading: {e}")
                continue
        
        # Update device status
        if payload.readings and payload.readings[-1].battery_level is not None:
            device.battery_level = payload.readings[-1].battery_level
            device.last_seen = datetime.utcnow()
            device.is_active = True
        
        db.commit()
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message=f"Successfully recorded {recorded_count} BLE readings",
                data={
                    "recorded_count": recorded_count,
                    "total_readings": len(payload.readings),
                    "device_id": device.id
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        print(f"BLE batch recording error: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Failed to record BLE batch: {str(e)}",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device data
@router.get("/{device_id}/data", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_device_data(
    device_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get device sensor data with optional time filtering"""
    try:
        # Get device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.id == device_id
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
        
        # Check if user has access to this device
        classroom = db.query(db_models.Class).filter(
            db_models.Class.id == device.classroom_id
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
        
        # Check access permissions
        is_teacher = classroom.owner_id == current_user.user_id
        is_student = db.query(db_models.ClassMember).filter(
            db_models.ClassMember.class_id == device.classroom_id,
            db_models.ClassMember.user_id == current_user.user_id
        ).first() is not None
        
        if not (is_teacher or is_student):
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied to device data",
                    error_type="unauthorized"
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Build query
        query = db.query(db_models.ClassroomDeviceData).filter(
            db_models.ClassroomDeviceData.device_id == device_id
        )
        
        if start_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp >= start_time)
        
        if end_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp <= end_time)
        
        # Get data ordered by timestamp (newest first)
        data_records = query.order_by(desc(db_models.ClassroomDeviceData.timestamp)).limit(limit).all()
        
        # Format response data
        data_list = []
        for record in data_records:
            data_list.append({
                "id": record.id,
                "device_id": record.device_id,
                "timestamp": record.timestamp.isoformat(),
                "temperature": float(record.temperature) if record.temperature else None,
                "thermometer": float(record.thermometer) if record.thermometer else None,
                "humidity": float(record.humidity) if record.humidity else None,
                "moisture": float(record.moisture) if record.moisture else None,
                "light": float(record.light) if record.light else None,
                "sound": float(record.sound) if record.sound else None,
                "battery_level": record.battery_level,
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
        
    except Exception as e:
        print(f"Error retrieving device data: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get latest device data
@router.get("/{device_id}/data/latest", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_latest_device_data(
    device_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the most recent sensor data for a device"""
    try:
        # Get device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.id == device_id
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
        
        # Get latest data record
        latest_data = db.query(db_models.ClassroomDeviceData).filter(
            db_models.ClassroomDeviceData.device_id == device_id
        ).order_by(desc(db_models.ClassroomDeviceData.timestamp)).first()
        
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
            "thermometer": float(latest_data.thermometer) if latest_data.thermometer else None,
            "humidity": float(latest_data.humidity) if latest_data.humidity else None,
            "moisture": float(latest_data.moisture) if latest_data.moisture else None,
            "light": float(latest_data.light) if latest_data.light else None,
            "sound": float(latest_data.sound) if latest_data.sound else None,
            "battery_level": latest_data.battery_level,
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
        
    except Exception as e:
        print(f"Error retrieving latest device data: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve latest device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device information for anonymous students
@router.get("/{device_id}/anonymous", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_device_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    db: Session = Depends(get_db)
):
    """Get device information for anonymous students"""
    try:
        # Verify anonymous student
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
                    error_type="authentication_error"
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Get device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.id == device_id
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
        
        # Check if device is in the same classroom
        if device.classroom_id != class_id:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found in this classroom",
                    error_type="device_not_found"
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if device is public (anonymous students can only see public devices)
        assignment = db.query(db_models.ClassroomDeviceAssignment).filter(
            db_models.ClassroomDeviceAssignment.device_id == device_id
        ).first()
        
        if not assignment or assignment.assignment_type != "public":
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied - Device is not public",
                    error_type="access_denied"
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Format response
        device_data = {
            "id": device.id,
            "device_name": device.device_name,
            "device_type": device.device_type,
            "is_active": device.is_active,
            "battery_level": device.battery_level,
            "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            "assignment": {
                "type": assignment.assignment_type if assignment else "public",
                "id": assignment.assignment_id if assignment else None
            },
            "created_at": device.created_at.isoformat()
        }
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Device information retrieved successfully",
                data=device_data
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
        
    except Exception as e:
        print(f"Error retrieving device information for anonymous student: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device information",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get device data for anonymous students
@router.get("/{device_id}/data/anonymous", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_device_data_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get device sensor data for anonymous students"""
    try:
        # Verify anonymous student
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
                    error_type="authentication_error"
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Get device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.id == device_id
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
        
        # Check if device is in the same classroom
        if device.classroom_id != class_id:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found in this classroom",
                    error_type="device_not_found"
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if device is public (anonymous students can only see public devices)
        assignment = db.query(db_models.ClassroomDeviceAssignment).filter(
            db_models.ClassroomDeviceAssignment.device_id == device_id
        ).first()
        
        if not assignment or assignment.assignment_type != "public":
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied - Device is not public",
                    error_type="access_denied"
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Build query
        query = db.query(db_models.ClassroomDeviceData).filter(
            db_models.ClassroomDeviceData.device_id == device_id
        )
        
        if start_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp >= start_time)
        
        if end_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp <= end_time)
        
        # Get data ordered by timestamp (newest first)
        data_records = query.order_by(desc(db_models.ClassroomDeviceData.timestamp)).limit(limit).all()
        
        # Format response data
        data_list = []
        for record in data_records:
            data_list.append({
                "id": record.id,
                "device_id": record.device_id,
                "timestamp": record.timestamp.isoformat(),
                "temperature": float(record.temperature) if record.temperature else None,
                "thermometer": float(record.thermometer) if record.thermometer else None,
                "humidity": float(record.humidity) if record.humidity else None,
                "moisture": float(record.moisture) if record.moisture else None,
                "light": float(record.light) if record.light else None,
                "sound": float(record.sound) if record.sound else None,
                "battery_level": record.battery_level,
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
        
    except Exception as e:
        print(f"Error retrieving device data for anonymous student: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Get latest device data for anonymous students
@router.get("/{device_id}/data/latest/anonymous", tags=["classroom-device"], status_code=status.HTTP_200_OK)
async def get_latest_device_data_anonymous(
    device_id: str,
    class_id: str = Query(..., description="Classroom ID"),
    first_name: str = Query(..., description="Student first name"),
    pin_code: str = Query(..., description="Student PIN code"),
    start_time: Optional[datetime] = Query(None, description="Start time for data range"),
    end_time: Optional[datetime] = Query(None, description="End time for data range"),
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get the most recent sensor data for a device (anonymous students)"""
    try:
        # Verify anonymous student
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
                    error_type="authentication_error"
                ).dict(),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        
        # Get device
        device = db.query(db_models.ClassroomDevice).filter(
            db_models.ClassroomDevice.id == device_id
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
        
        # Check if device is in the same classroom
        if device.classroom_id != class_id:
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Device not found in this classroom",
                    error_type="device_not_found"
                ).dict(),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        
        # Check if device is public (anonymous students can only see public devices)
        assignment = db.query(db_models.ClassroomDeviceAssignment).filter(
            db_models.ClassroomDeviceAssignment.device_id == device_id
        ).first()
        
        if not assignment or assignment.assignment_type != "public":
            return JSONResponse(
                content=api_resp(
                    success=False,
                    message="Access denied - Device is not public",
                    error_type="access_denied"
                ).dict(),
                status_code=status.HTTP_403_FORBIDDEN,
            )
        
        # Build query for latest data
        query = db.query(db_models.ClassroomDeviceData).filter(
            db_models.ClassroomDeviceData.device_id == device_id
        )
        
        if start_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp >= start_time)
        
        if end_time:
            query = query.filter(db_models.ClassroomDeviceData.timestamp <= end_time)
        
        # Get latest data record
        latest_data = query.order_by(desc(db_models.ClassroomDeviceData.timestamp)).first()
        
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
            "thermometer": float(latest_data.thermometer) if latest_data.thermometer else None,
            "humidity": float(latest_data.humidity) if latest_data.humidity else None,
            "moisture": float(latest_data.moisture) if latest_data.moisture else None,
            "light": float(latest_data.light) if latest_data.light else None,
            "sound": float(latest_data.sound) if latest_data.sound else None,
            "battery_level": latest_data.battery_level,
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
        
    except Exception as e:
        print(f"Error retrieving latest device data for anonymous student: {str(e)}")
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to retrieve latest device data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
