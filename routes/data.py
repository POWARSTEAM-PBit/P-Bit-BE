from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
from datetime import datetime, timedelta

from db.init_engine import get_db
from db import db_models
from utils import (
    api_resp, error_resp, 
    validate_mac_address, validate_time_range
)
from middleware import get_current_user

router = APIRouter(prefix="/device")

# Pydantic models for request/response
class DeviceDataUpload(BaseModel):
    temperature: Optional[float] = Field(None, ge=-50, le=100)
    moisture: Optional[float] = Field(None, ge=0, le=100)
    light: Optional[float] = Field(None, ge=0, le=10000)
    sound: Optional[float] = Field(None, ge=0, le=200)
    battery_level: Optional[int] = Field(None, ge=0, le=100)

# Get device data
@router.get("/{device_id}/data", tags=["data"], status_code=status.HTTP_200_OK)
async def get_device_data(
    device_id: str,
    time_range: str = Query(default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate time range
    is_valid_range, range_error = validate_time_range(time_range)
    if not is_valid_range:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=range_error,
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
    
    # Calculate time range
    now = datetime.utcnow()
    if time_range == "1h":
        start_time = now - timedelta(hours=1)
    elif time_range == "6h":
        start_time = now - timedelta(hours=6)
    elif time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    elif time_range == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)  # Default to 24h
    
    # Get sensor data within time range
    sensor_data = db.query(db_models.DeviceData).filter(
        db_models.DeviceData.device_id == device_id,
        db_models.DeviceData.timestamp >= start_time
    ).order_by(db_models.DeviceData.timestamp.desc()).all()
    
    # Format sensor data
    sensor_data_list = []
    for data in sensor_data:
        sensor_data_list.append({
            "timestamp": data.timestamp.isoformat() if data.timestamp else None,
            "temperature": float(data.temperature) if data.temperature is not None else None,
            "moisture": float(data.moisture) if data.moisture is not None else None,
            "light": float(data.light) if data.light is not None else None,
            "sound": float(data.sound) if data.sound is not None else None
        })
    
    # Get current readings (most recent data)
    current_readings = None
    if sensor_data:
        latest_data = sensor_data[0]  # Most recent due to desc order
        current_readings = {
            "temperature": float(latest_data.temperature) if latest_data.temperature is not None else None,
            "moisture": float(latest_data.moisture) if latest_data.moisture is not None else None,
            "light": float(latest_data.light) if latest_data.light is not None else None,
            "sound": float(latest_data.sound) if latest_data.sound is not None else None,
            "timestamp": latest_data.timestamp.isoformat() if latest_data.timestamp else None
        }
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Device data retrieved successfully",
            data={
                "device_id": device_id,
                "time_range": time_range,
                "sensor_data": sensor_data_list,
                "current_readings": current_readings
            }
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Get device data by MAC address (direct access)
@router.get("/mac/{mac_address}/data", tags=["data"], status_code=status.HTTP_200_OK)
async def get_device_data_by_mac(
    mac_address: str,
    time_range: str = Query(default="24h", description="Time range: 1h, 6h, 24h, 7d, 30d"),
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
    
    # Validate time range
    is_valid_range, range_error = validate_time_range(time_range)
    if not is_valid_range:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=range_error,
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
    
    # Calculate time range
    now = datetime.utcnow()
    if time_range == "1h":
        start_time = now - timedelta(hours=1)
    elif time_range == "6h":
        start_time = now - timedelta(hours=6)
    elif time_range == "24h":
        start_time = now - timedelta(hours=24)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    elif time_range == "30d":
        start_time = now - timedelta(days=30)
    else:
        start_time = now - timedelta(hours=24)  # Default to 24h
    
    # Get sensor data within time range
    sensor_data = db.query(db_models.DeviceData).filter(
        db_models.DeviceData.device_id == device.id,
        db_models.DeviceData.timestamp >= start_time
    ).order_by(db_models.DeviceData.timestamp.desc()).all()
    
    # Format sensor data
    sensor_data_list = []
    for data in sensor_data:
        sensor_data_list.append({
            "timestamp": data.timestamp.isoformat() if data.timestamp else None,
            "temperature": float(data.temperature) if data.temperature is not None else None,
            "moisture": float(data.moisture) if data.moisture is not None else None,
            "light": float(data.light) if data.light is not None else None,
            "sound": float(data.sound) if data.sound is not None else None
        })
    
    # Get current readings (most recent data)
    current_readings = None
    if sensor_data:
        latest_data = sensor_data[0]  # Most recent due to desc order
        current_readings = {
            "temperature": float(latest_data.temperature) if latest_data.temperature is not None else None,
            "moisture": float(latest_data.moisture) if latest_data.moisture is not None else None,
            "light": float(latest_data.light) if latest_data.light is not None else None,
            "sound": float(latest_data.sound) if latest_data.sound is not None else None,
            "timestamp": latest_data.timestamp.isoformat() if latest_data.timestamp else None
        }
    
    return JSONResponse(
        content=api_resp(
            success=True,
            message="Device data retrieved successfully",
            data={
                "device_id": device.id,
                "time_range": time_range,
                "sensor_data": sensor_data_list,
                "current_readings": current_readings
            }
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

# Upload device data (for P-Bit devices)
@router.post("/mac/{mac_address}/upload", tags=["data"], status_code=status.HTTP_200_OK)
async def upload_device_data(
    mac_address: str,
    payload: DeviceDataUpload,
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
    
    # Create new data entry
    new_data = db_models.DeviceData(
        id=str(uuid.uuid4()),
        device_id=device.id,
        timestamp=datetime.utcnow(),
        temperature=payload.temperature,
        moisture=payload.moisture,
        light=payload.light,
        sound=payload.sound
    )
    
    try:
        db.add(new_data)
        
        # Update device status
        device.is_active = True
        device.last_seen = datetime.utcnow()
        if payload.battery_level is not None:
            device.battery_level = payload.battery_level
        
        db.commit()
        db.refresh(new_data)
        
        return JSONResponse(
            content=api_resp(
                success=True,
                message="Data uploaded successfully",
                data={
                    "device_id": device.id,
                    "timestamp": new_data.timestamp.isoformat() if new_data.timestamp else None,
                    "temperature": float(new_data.temperature) if new_data.temperature is not None else None,
                    "moisture": float(new_data.moisture) if new_data.moisture is not None else None,
                    "light": float(new_data.light) if new_data.light is not None else None,
                    "sound": float(new_data.sound) if new_data.sound is not None else None
                }
            ).dict(),
            status_code=status.HTTP_200_OK,
        )
    except Exception:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Failed to upload data",
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
