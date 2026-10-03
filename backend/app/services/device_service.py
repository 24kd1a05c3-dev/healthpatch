from app.models.device import DeviceCreate, DeviceResponse
from datetime import datetime, timezone
import pymongo

async def register_device(device_data: DeviceCreate, db) -> DeviceResponse:
    doc = device_data.model_dump()
    doc["status"] = "OFFLINE"
    doc["model_name"] = "HealthPatch"
    await db["devices"].insert_one(doc)
    return DeviceResponse(**doc)

async def pair_device(device_id: str, user_id: str, db) -> DeviceResponse | None:
    doc = await db["devices"].find_one_and_update(
        {"device_id": device_id, "$or": [{"user_id": {"$exists": False}}, {"user_id": None}, {"user_id": user_id}]},
        {"$set": {"user_id": user_id}},
        return_document=pymongo.ReturnDocument.AFTER,
    )
    if doc:
        return DeviceResponse(**doc)
    return None

async def get_devices(user_id: str, db) -> list[DeviceResponse]:
    cursor = db["devices"].find({"user_id": user_id}).limit(100)
    docs = await cursor.to_list(length=100)
    return [DeviceResponse(**d) for d in docs]

async def get_device(device_id: str, db) -> DeviceResponse | None:
    doc = await db["devices"].find_one({"device_id": device_id})
    if doc:
        return DeviceResponse(**doc)
    return None

async def update_device_status(device_id: str, status: str, battery: float, signal_quality: float, db):
    await db["devices"].update_one(
        {"device_id": device_id},
        {"$set": {
            "status": status,
            "battery": battery,
            "signal_quality": signal_quality,
            "last_seen": datetime.now(timezone.utc)
        }}
    )
