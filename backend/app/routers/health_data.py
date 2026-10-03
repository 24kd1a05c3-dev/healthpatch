from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from typing_extensions import Literal
from app.models.health_data import HealthMeasurement, HealthDataResponse, BaselineResponse
from app.services.health_service import ingest_measurement, get_latest, get_history, get_baseline
from app.services.alert_service import create_alert_from_analysis
from app.services.notify_service import notify_watchers
from app.services.auth_service import get_user_by_id
from app.ai.insights import build_insights
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user
from app.authz import ensure_patient_access
from app.websocket_manager import manager

router = APIRouter(prefix="/health-data", tags=["health"])

@router.post("/", response_model=HealthDataResponse)
async def ingest(
    measurement: HealthMeasurement,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(lambda: get_collection("health_measurements").database),
):
    if current_user.id != measurement.user_id:
        raise HTTPException(status_code=403, detail="Measurements can only be submitted for the authenticated user")
    device = await db["devices"].find_one({"device_id": measurement.device_id, "user_id": current_user.id})
    if not device:
        raise HTTPException(status_code=403, detail="Device is not paired to the authenticated user")
    response = await ingest_measurement(measurement, db)
    payload = response.model_dump(mode="json")

    await manager.send_to_user(measurement.user_id, {"type": "health_data", "data": payload})
    await notify_watchers(measurement.user_id, {"type": "health_data", "data": payload}, db, manager)

    device_status = {
        "id": measurement.device_id,
        "battery": measurement.battery,
        "signal": round(measurement.signal_quality * 100),
        "status": "ONLINE",
    }
    await manager.send_to_user(measurement.user_id, {"type": "device_status", "data": device_status})
    await notify_watchers(measurement.user_id, {"type": "device_status", "data": device_status}, db, manager)

    if response.analysis and response.analysis.get("risk_level") in ["WARNING", "CRITICAL"]:
        alert = await create_alert_from_analysis(
            measurement.user_id,
            measurement.device_id,
            response.id,
            response.analysis,
            db
        )
        if alert:
            alert_payload = alert.model_dump(mode="json")
            await manager.send_to_user(measurement.user_id, {"type": "alert", "data": alert_payload})
            await notify_watchers(measurement.user_id, {"type": "alert", "data": alert_payload}, db, manager)

    return response

@router.get("/latest", response_model=Optional[HealthDataResponse])
async def latest(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    return await get_latest(uid, db)

@router.get("/history", response_model=list[HealthDataResponse])
async def history(
    period: Literal["1h", "6h", "24h", "7d", "30d"] = "24h",
    user_id: Optional[str] = None,
    limit: int = 1000,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(lambda: get_collection("health_measurements").database),
):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    return await get_history(uid, period, db, limit)

@router.get("/baseline", response_model=Optional[BaselineResponse])
async def baseline(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    return await get_baseline(uid, db)

@router.get("/analysis")
async def analysis(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    latest_data = await get_latest(uid, db)
    if latest_data and latest_data.analysis:
        baseline = await get_baseline(uid, db)
        patient = await get_user_by_id(uid, db)
        name = patient.full_name.split()[0] if patient else "Patient"
        return build_insights(latest_data.analysis, baseline, name)
    raise HTTPException(status_code=404, detail="No analysis found")
