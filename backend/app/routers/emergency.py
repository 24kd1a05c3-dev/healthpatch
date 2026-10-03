from fastapi import APIRouter, Depends, HTTPException
from app.models.emergency import EmergencyCreate, EmergencyResponse
from app.services.health_service import get_latest
from app.services.alert_service import create_alert
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user
from app.authz import ensure_patient_access, ensure_patient_exists
from app.websocket_manager import manager
from app.services.notify_service import notify_watchers
from datetime import datetime, timezone
import pymongo

router = APIRouter(prefix="/emergency", tags=["emergency"])

@router.post("/", response_model=EmergencyResponse)
async def create_emergency(data: EmergencyCreate, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("emergency_events").database)):
    ensure_patient_access(current_user, data.user_id)
    await ensure_patient_exists(data.user_id, db)
    latest = await get_latest(data.user_id, db)
    snapshot = latest.model_dump(mode="json") if latest else {}
    
    doc = {
        "user_id": data.user_id,
        "triggered_by": 'patient' if current_user.role == 'patient' else 'caregiver',
        "actor_id": current_user.id,
        "health_snapshot": snapshot,
        "location": data.location,
        "notes": data.notes,
        "status": "active",
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db["emergency_events"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    
    await create_alert({
        "user_id": data.user_id,
        "alert_type": "Emergency",
        "level": "critical",
        "title": "EMERGENCY ACTIVATED",
        "message": f"Emergency triggered by {data.triggered_by}",
        "reasons": ["User triggered emergency mode"],
        "device_id": snapshot.get("device_id", "unknown"),
        "measurement_id": snapshot.get("id", "unknown"),
        "created_at": datetime.now(timezone.utc)
    }, db)
    
    resp = EmergencyResponse(**doc)
    message = {"type": "emergency", "data": resp.model_dump(mode="json")}
    await manager.send_to_user(data.user_id, message)
    await notify_watchers(data.user_id, message, db, manager)
    return resp

@router.get("/history", response_model=list[EmergencyResponse])
async def get_history(current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("emergency_events").database)):
    cursor = db["emergency_events"].find({"user_id": current_user.id}, sort=[("created_at", pymongo.DESCENDING)])
    docs = await cursor.to_list(length=100)
    for d in docs:
        d["id"] = str(d["_id"])
    return [EmergencyResponse(**d) for d in docs]
