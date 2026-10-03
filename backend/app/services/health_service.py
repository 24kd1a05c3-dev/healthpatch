from app.models.health_data import HealthMeasurement, HealthDataResponse, BaselineResponse
from app.ai.engine import analyze_measurement
from datetime import datetime, timedelta, timezone
from app.services.device_service import update_device_status
import pymongo
from app.models.telemetry import NormalizedTelemetry, Vitals
from app.services.telemetry_service import ingest_normalized

async def ingest_measurement(measurement: HealthMeasurement, db) -> HealthDataResponse:
    doc = measurement.model_dump()
    analysis = await analyze_measurement(doc, db)
    doc["analysis"] = analysis
    
    result = await db["health_measurements"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    timestamp = measurement.timestamp
    await ingest_normalized(NormalizedTelemetry(user_id=measurement.user_id, device_id=measurement.device_id,
        stream_id=f'{measurement.source_type.value}:{measurement.device_id}:{timestamp.date().isoformat()}',
        sequence_number=int(timestamp.timestamp() * 1000000), timestamp=timestamp,
        source_type=measurement.source_type, provenance=measurement.provenance,
        vitals=Vitals(heart_rate=measurement.heart_rate, spo2=measurement.spo2, temperature=measurement.temperature),
        signal_quality=measurement.signal_quality), db)
    
    await update_device_status(
        measurement.device_id,
        "ONLINE",
        measurement.battery,
        measurement.signal_quality,
        db
    )
    
    return HealthDataResponse(**doc)

async def get_latest(user_id: str, db) -> HealthDataResponse | None:
    doc = await db["health_measurements"].find_one({"user_id": user_id}, sort=[("timestamp", pymongo.DESCENDING)])
    if doc:
        doc["id"] = str(doc["_id"])
        return HealthDataResponse(**doc)
    return None

async def get_history(user_id: str, period: str, db, limit: int = 1000) -> list[HealthDataResponse]:
    periods = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    td = periods.get(period, timedelta(hours=24))
    since = datetime.now(timezone.utc) - td
    
    bounded_limit = max(1, min(limit, 5000))
    cursor = db["health_measurements"].find(
        {"user_id": user_id, "timestamp": {"$gte": since}},
        sort=[("timestamp", pymongo.ASCENDING)]
    ).limit(bounded_limit)
    docs = await cursor.to_list(length=bounded_limit)
    for d in docs:
        d["id"] = str(d["_id"])
    return [HealthDataResponse(**d) for d in docs]

async def get_baseline(user_id: str, db) -> BaselineResponse | None:
    from app.ai.baseline import calculate_baseline
    return await calculate_baseline(user_id, db)
