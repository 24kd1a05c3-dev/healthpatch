def detect_anomaly(measurement: dict, rule_result: dict, baseline_comparison: dict) -> dict:
    reasons = []
    base_score = 0.0
    
    for viol in rule_result.get("violations", []):
        reasons.append(viol["message"])
        if viol["level"] == "critical":
            base_score += 0.5
        elif viol["level"] == "warning":
            base_score += 0.25
            
    abnormal_vitals_count = 0
    deviations = baseline_comparison.get("deviations", {})
    for metric, dev in deviations.items():
        if dev["significant"]:
            reasons.append(f"Significant deviation in {metric}: z-score {dev['z_score']:.2f}")
            base_score += 0.2
            abnormal_vitals_count += 1
            
    if abnormal_vitals_count >= 2:
        reasons.append("Multi-signal correlation bonus")
        base_score += 0.2
        
    anomaly_score = min(base_score, 1.0)
    
    if anomaly_score >= 0.75:
        risk_level = "CRITICAL"
    elif anomaly_score >= 0.5:
        risk_level = "WARNING"
    elif anomaly_score >= 0.3:
        risk_level = "INFO"
    else:
        risk_level = "NORMAL"
        
    if not reasons and risk_level == "NORMAL":
        reasons = ["All metrics within normal ranges"]
        
    return {
        "risk_level": risk_level,
        "anomaly_score": anomaly_score,
        "reasons": reasons,
        "confidence": 0.85,
        "details": {
            "rules": rule_result,
            "baseline": baseline_comparison
        }
    }
