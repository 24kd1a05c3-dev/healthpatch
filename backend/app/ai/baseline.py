from datetime import datetime, timedelta, timezone
from app.models.health_data import BaselineResponse

async def calculate_baseline(user_id: str, db) -> BaselineResponse | None:
    collection = db["health_measurements"]
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    cursor = collection.aggregate([
        {"$match": {"user_id": user_id, "timestamp": {"$gte": seven_days_ago}}},
        {"$group": {
            "_id": "$user_id",
            "data_points": {"$sum": 1},
            "heart_rate_mean": {"$avg": "$heart_rate"},
            "heart_rate_std": {"$stdDevPop": "$heart_rate"},
            "heart_rate_min": {"$min": "$heart_rate"},
            "heart_rate_max": {"$max": "$heart_rate"},
            "spo2_mean": {"$avg": "$spo2"},
            "spo2_std": {"$stdDevPop": "$spo2"},
            "spo2_min": {"$min": "$spo2"},
            "spo2_max": {"$max": "$spo2"},
            "temperature_mean": {"$avg": "$temperature"},
            "temperature_std": {"$stdDevPop": "$temperature"},
            "temperature_min": {"$min": "$temperature"},
            "temperature_max": {"$max": "$temperature"},
        }},
    ])
    stats = await cursor.to_list(length=1)

    if not stats or stats[0]["data_points"] < 10:
        return None

    data = stats[0]
    return BaselineResponse(
        user_id=user_id,
        heart_rate_mean=data.get("heart_rate_mean") or 0,
        heart_rate_std=data.get("heart_rate_std") or 0,
        heart_rate_min=data.get("heart_rate_min") or 0,
        heart_rate_max=data.get("heart_rate_max") or 0,
        spo2_mean=data.get("spo2_mean") or 0,
        spo2_std=data.get("spo2_std") or 0,
        spo2_min=data.get("spo2_min") or 0,
        spo2_max=data.get("spo2_max") or 0,
        temperature_mean=data.get("temperature_mean") or 0,
        temperature_std=data.get("temperature_std") or 0,
        temperature_min=data.get("temperature_min") or 0,
        temperature_max=data.get("temperature_max") or 0,
        data_points=data["data_points"],
        period_days=7,
        calculated_at=datetime.now(timezone.utc)
    )

def compare_to_baseline(measurement: dict, baseline: BaselineResponse | None) -> dict:
    if not baseline:
        return {"deviations": {}}
        
    deviations = {}
    
    hr = measurement.get("heart_rate")
    if hr is not None and baseline.heart_rate_std > 0:
        z = (hr - baseline.heart_rate_mean) / baseline.heart_rate_std
        deviations["heart_rate"] = {
            "z_score": z,
            "direction": "high" if z > 0 else "low",
            "significant": abs(z) > 2.0
        }
        
    spo2 = measurement.get("spo2")
    if spo2 is not None and baseline.spo2_std > 0:
        z = (spo2 - baseline.spo2_mean) / baseline.spo2_std
        deviations["spo2"] = {
            "z_score": z,
            "direction": "high" if z > 0 else "low",
            "significant": abs(z) > 2.0
        }
        
    temp = measurement.get("temperature")
    if temp is not None and baseline.temperature_std > 0:
        z = (temp - baseline.temperature_mean) / baseline.temperature_std
        deviations["temperature"] = {
            "z_score": z,
            "direction": "high" if z > 0 else "low",
            "significant": abs(z) > 2.0
        }
        
    return {"deviations": deviations}
