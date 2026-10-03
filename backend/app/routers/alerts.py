from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.models.alert import AlertResponse
from app.services.alert_service import get_alerts, acknowledge_alert
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user
from app.authz import ensure_patient_access, require_valid_object_id
from app.services.session_service import audit

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(level: Optional[str] = None, user_id: Optional[str] = None, limit: int = 50, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("alerts").database)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    return await get_alerts(db, uid, level, limit)

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("alerts").database)):
    doc = await db["alerts"].find_one({"_id": require_valid_object_id(alert_id, "Alert")})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")
    ensure_patient_access(current_user, doc["user_id"])
    doc["id"] = str(doc["_id"])
    return AlertResponse(**doc)

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def ack_alert(alert_id: str, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("alerts").database)):
    existing = await db["alerts"].find_one({"_id": require_valid_object_id(alert_id, "Alert")})
    if not existing:
        raise HTTPException(status_code=404, detail="Alert not found")
    ensure_patient_access(current_user, existing["user_id"])
    alert = await acknowledge_alert(alert_id, current_user.id, db)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await audit(db, current_user.id, 'alert_acknowledged', alert_id)
    return alert
