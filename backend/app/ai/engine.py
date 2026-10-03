from app.ai.rule_engine import evaluate
from app.ai.baseline import calculate_baseline, compare_to_baseline
from app.ai.anomaly_detector import detect_anomaly

async def analyze_measurement(measurement: dict, db) -> dict:
    rule_result = evaluate(measurement)
    if rule_result["max_level"] == "low_quality":
        return {
            "risk_level": "INFO",
            "anomaly_score": 0.0,
            "reasons": ["Low signal quality, analysis skipped"],
            "confidence": 0.0,
            "details": {}
        }
        
    baseline = await calculate_baseline(measurement["user_id"], db)
    baseline_comp = compare_to_baseline(measurement, baseline)
    
    anomaly = detect_anomaly(measurement, rule_result, baseline_comp)
    return anomaly
