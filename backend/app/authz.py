from fastapi import HTTPException, status
from bson import ObjectId

from app.models.user import UserInDB


def require_valid_object_id(value: str, name: str = "id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} not found")
    return ObjectId(value)


def user_can_access_patient(current_user: UserInDB, patient_id: str) -> bool:
    if current_user.role == "admin":
        return True
    if current_user.id == patient_id:
        return True
    return patient_id in current_user.assigned_patients


def ensure_patient_access(current_user: UserInDB, patient_id: str) -> None:
    if not user_can_access_patient(current_user, patient_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")


async def ensure_patient_exists(patient_id: str, db) -> None:
    object_id = require_valid_object_id(patient_id, "User")
    exists = await db["users"].find_one({"_id": object_id, "role": "patient"}, {"_id": 1})
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")


async def ensure_device_access(current_user: UserInDB, device_id: str, db) -> dict:
    device = await db["devices"].find_one({"device_id": device_id})
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    owner_id = device.get("user_id")
    if owner_id and not user_can_access_patient(current_user, owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    if not owner_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return device
