from fastapi import APIRouter, Depends, HTTPException
from app.models.device import DeviceCreate, DeviceResponse
from app.services.device_service import register_device, get_devices, get_device, pair_device
from app.models.user import UserInDB
from app.security import get_current_user, require_role
from app.database import get_collection
from app.authz import ensure_device_access

router = APIRouter(prefix="/devices", tags=["devices"])

@router.post("/", response_model=DeviceResponse)
async def create_device(
    device_data: DeviceCreate,
    current_user: UserInDB = Depends(require_role("admin")),
    db=Depends(lambda: get_collection("devices").database),
):
    existing = await get_device(device_data.device_id, db)
    if existing:
        raise HTTPException(status_code=409, detail="Device already exists")
    return await register_device(device_data, db)

@router.get("/", response_model=list[DeviceResponse])
async def list_devices(current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("devices").database)):
    return await get_devices(current_user.id, db)

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device_info(
    device_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(lambda: get_collection("devices").database),
):
    await ensure_device_access(current_user, device_id, db)
    dev = await get_device(device_id, db)
    return dev

@router.post("/{device_id}/pair", response_model=DeviceResponse)
async def pair(device_id: str, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("devices").database)):
    dev = await pair_device(device_id, current_user.id, db)
    if not dev:
        existing = await get_device(device_id, db)
        if existing:
            raise HTTPException(status_code=409, detail="Device is already paired")
        raise HTTPException(status_code=404, detail="Device not found")
    return dev
