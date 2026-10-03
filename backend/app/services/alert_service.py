from app.models.alert import Alert, AlertResponse
from datetime import datetime, timezone
from bson import ObjectId
import pymongo

async def create_alert(alert_data: dict, db) -> AlertResponse:
    result = await db["alerts"].insert_one(alert_data)
    alert_data["id"] = str(result.inserted_id)
    return AlertResponse(**alert_data)

async def create_alert_from_analysis(user_id: str, device_id: str, measurement_id: str, analysis: dict, db) -> AlertResponse | None:
    risk = analysis.get("risk_level", "NORMAL")
    if risk in ["WARNING", "CRITICAL"]:
        level = "warning" if risk == "WARNING" else "critical"
        alert_data = Alert(
            user_id=user_id,
            alert_type="HealthAnomaly",
            level=level,
            title=f"{risk} Health Alert",
            message=", ".join(analysis.get("reasons", [])),
            reasons=analysis.get("reasons", []),
            anomaly_score=analysis.get("anomaly_score"),
            device_id=device_id,
            measurement_id=measurement_id
        ).model_dump()
        return await create_alert(alert_data, db)
    return None

async def get_alerts(db, user_id: str = None, level: str = None, limit: int = 50) -> list[AlertResponse]:
    query = {}
    if user_id:
        query["user_id"] = user_id
    if level:
        query["level"] = level
        
    bounded_limit = max(1, min(limit, 200))
    cursor = db["alerts"].find(query, sort=[("created_at", pymongo.DESCENDING)]).limit(bounded_limit)
    docs = await cursor.to_list(length=bounded_limit)
    for d in docs:
        d["id"] = str(d["_id"])
    return [AlertResponse(**d) for d in docs]

async def acknowledge_alert(alert_id: str, user_id: str, db) -> AlertResponse | None:
    if not ObjectId.is_valid(alert_id):
        return None
    doc = await db["alerts"].find_one_and_update(
        {"_id": ObjectId(alert_id)},
        {"$set": {
            "acknowledged": True,
            "acknowledged_by": user_id,
            "acknowledged_at": datetime.now(timezone.utc)
        }},
        return_document=pymongo.ReturnDocument.AFTER
    )
    if doc:
        doc["id"] = str(doc["_id"])
        return AlertResponse(**doc)
    return None
