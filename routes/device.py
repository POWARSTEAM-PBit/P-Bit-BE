from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from db.init_engine import get_db
from db import db_models
from utils import api_resp, error_resp
from typing import Literal
from datetime import datetime, timezone
from middleware import get_current_user

ALLOWED_TYPES = ['ph', 'moisture']
ValidTypes = Literal[*ALLOWED_TYPES]

class AddDeviceManf(BaseModel):
    mac_addr: str = Field(min_length=12, max_length=12)  # For example, MAC address of exact 17 chars

class AddDeviceData(BaseModel):
    mac_addr: str = Field(min_length=12, max_length=12)  # For example, MAC address of exact 17 chars
    type: ValidTypes = Field(...)
    value: float = Field(...)

class AddDeviceUser(BaseModel):
    mac_addr: str = Field(min_length=12, max_length=12)  # For example, MAC address of exact 17 chars
    device_name: str
    class_id: str
class GetDevicesClass(BaseModel):
    class_id: str

router = APIRouter(prefix="/device")


@router.get("/get/{class_id}", tags=["device"], status_code=status.HTTP_200_OK)
async def get_all_devices_class(
    class_id: str,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db) 
):
    """
    The following endpoint get's all devices belonging to the class.
    """

    print("Class ID:", class_id, type(class_id))


    does_class_exist = db.query(db_models.Class).filter_by(
        id=class_id
    ).first()

    if not does_class_exist:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Class not found.",
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    is_member = db.query(db_models.ClassMember).filter_by(
        class_id=class_id,
        user_id=current_user.user_id
    ).first()

    is_owner = does_class_exist.owner_id == current_user.user_id

    if not (is_member or is_owner):
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"You are not authorized to view the following classes devices: {does_class_exist.id}.",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    class_devices = db.query(db_models.ClassDevice).filter_by(
        class_id=class_id
    ).all()

    

    devices = []
    for device in class_devices:
        devices.append({
            "mac_addr": device.mac_addr,
            "device_name": device.device_name
        })

    if len(devices) == 0:
        print("empty")
    
    return JSONResponse(
        content=api_resp(
            success=True, 
            message="Owned classes retrieved successfully", 
            data=devices
        ).dict(),
        status_code=status.HTTP_200_OK,
    )

@router.post("/add/class", tags=["device"], status_code=status.HTTP_201_CREATED)
async def link_device_to_user(
    payload: AddDeviceUser,
    current_user: db_models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Links an existing device to a class if the current user is a member or owner of that class.
    """

    device = db.query(db_models.Device).filter(
        db_models.Device.mac_addr == payload.mac_addr
    ).first()

    if not device:
        return JSONResponse(
            content=api_resp(
                success=False,
                message=f"Device with MAC {payload.mac_addr} does not exist.",
                error=error_resp(code=status.HTTP_404_NOT_FOUND),
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    class_obj = db.query(db_models.Class).filter_by(
        id=payload.class_id
    ).first()

    if not class_obj:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Class not found.",
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    is_member = db.query(db_models.ClassMember).filter_by(
        class_id=payload.class_id,
        user_id=current_user.user_id
    ).first()

    is_owner = class_obj.owner_id == current_user.user_id

    if not (is_member or is_owner):
        return JSONResponse(
            content=api_resp(
                success=False,
                message="You are not authorized to add a device to this class.",
                error=error_resp(code=status.HTTP_403_FORBIDDEN)
            ).dict(),
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    existing_link = db.query(db_models.ClassDevice).filter_by(
        mac_addr=payload.mac_addr,
        class_id=payload.class_id
    ).first()

    if existing_link:
        return JSONResponse(
            content=api_resp(
                success=False,
                message="Device is already linked to this class.",
                error=error_resp(code=status.HTTP_409_CONFLICT)
            ).dict(),
            status_code=status.HTTP_409_CONFLICT
        )
    
    new_class_device = db_models.ClassDevice(
        mac_addr=payload.mac_addr,
        class_id=payload.class_id,
        device_name=payload.device_name
    )

    try:
        db.add(new_class_device)
        db.commit()

        return JSONResponse(
            content=api_resp(
                success=True,
                message=f"Device {payload.mac_addr} successfully linked to class {payload.class_id}"
            ).dict(),
            status_code=status.HTTP_201_CREATED
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message=f"Failed to create device {e}", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@router.post("/add/manf", tags=["device"], status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: AddDeviceManf,
    db: Session = Depends(get_db)
):
    """
    The following function creates a device. Note: This endpoint does not 
    need a API key attached to the API header.
    """

    new_device = db_models.Device(
        mac_addr=payload.mac_addr
    )
    
    try:
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Device created successfully", 
                data={
                    "mac_addr": new_device.mac_addr
                }
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message=f"Failed to create device {e}", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

@router.post("/publish/env", tags=["device"], status_code=status.HTTP_201_CREATED)
async def publish_data(
    payload: AddDeviceData,
    db: Session = Depends(get_db)
):
    """
    The following function creates a device. Note: This endpoint does not 
    need a API key attached to the API header.
    """

    does_device_exist = db.query(db_models.Device).filter(
        db_models.Device.mac_addr == payload.mac_addr
    ).first()

    if not does_device_exist:
        return JSONResponse(
            content=api_resp(
                success=False, 
                message=f"The following device does not exist {payload.mac_addr}", 
                error=error_resp(code=status.HTTP_404_NOT_FOUND)
            ).dict(),
            status_code=status.HTTP_404_NOT_FOUND,
        )
    
    data_timestamp = datetime.now(timezone.utc)

    new_data_entry = db_models.Data(
        mac_addr=payload.mac_addr,
        timestamp=data_timestamp,
        type=payload.type,
        value=payload.value
    )
        
    try:
        db.add(new_data_entry)
        db.commit()
        db.refresh(new_data_entry)
        
        return JSONResponse(
            content=api_resp(
                success=True, 
                message="Data was successfully published", 
            ).dict(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content=api_resp(
                success=False, 
                message=f"Failed to publish data {e}", 
                error=error_resp(code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            ).dict(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )