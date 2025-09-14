from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from db.init_engine import get_db
from db import db_models
from utils import api_resp, error_resp

class AddDeviceManf(BaseModel):
    mac_addr: str = Field(min_length=6, max_length=6)  # For example, MAC address of exact 17 chars

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