from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from db.init_engine import get_db
from db import db_models
from utils import api_resp, error_resp
from typing import Literal
from datetime import datetime, timezone

ALLOWED_TYPES = ['ph', 'moisture']
ValidTypes = Literal[*ALLOWED_TYPES]

class AddDeviceManf(BaseModel):
    mac_addr: str = Field(min_length=6, max_length=6)  # For example, MAC address of exact 17 chars

class AddDeviceData(BaseModel):
    mac_addr: str = Field(min_length=6, max_length=6)  # For example, MAC address of exact 17 chars
    type: ValidTypes = Field(...)
    value: float = Field(...)

router = APIRouter(prefix="/device")

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

@router.post("/add/env", tags=["device"], status_code=status.HTTP_201_CREATED)
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