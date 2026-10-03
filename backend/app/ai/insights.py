"""Build dashboard-friendly insights from raw analysis and baseline."""

from app.models.health_data import BaselineResponse


def build_insights(analysis: dict, baseline: BaselineResponse | None, user_name: str = "Patient") -> dict:
    score = max(0, min(100, int((1 - analysis.get("anomaly_score", 0)) * 100)))
    risk = analysis.get("risk_level", "INFO")

    if score >= 85:
        label = "Good"
    elif score >= 70:
        label = "Fair"
    elif score >= 50:
        label = "Attention"
    else:
        label = "Critical"

    reasons = analysis.get("reasons", [])
    warnings = []
    for reason in reasons:
        severity = "critical" if risk == "CRITICAL" else "warning" if risk == "WARNING" else "info"
        warnings.append({"title": "Health Anomaly", "desc": reason, "severity": severity})

    recommendations = []
    if risk in ("WARNING", "CRITICAL"):
        recommendations.append({
            "icon": "⚠️",
            "title": "Monitor Closely",
            "desc": "; ".join(reasons) if reasons else "Unusual pattern detected. Continue monitoring and consult a clinician if symptoms persist.",
            "priority": "High" if risk == "CRITICAL" else "Medium",
            "color": "#EF4444" if risk == "CRITICAL" else "#F59E0B",
        })
    else:
        recommendations.append({
            "icon": "✅",
            "title": "Vitals Stable",
            "desc": "Current measurements are within expected ranges based on your personal baseline.",
            "priority": "Low",
            "color": "#10B981",
        })

    hr_score = 88 if baseline else 75
    spo2_score = 92 if baseline else 80
    temp_score = 84 if baseline else 78

    if analysis.get("anomaly_score", 0) > 0.5:
        hr_score = max(40, hr_score - 20)

    radar = [
        {"metric": "Cardiac", "value": hr_score},
        {"metric": "Respiratory", "value": spo2_score},
        {"metric": "Metabolic", "value": temp_score},
        {"metric": "Neurological", "value": 84},
        {"metric": "Hydration", "value": 70},
        {"metric": "Sleep", "value": 65},
    ]

    baseline_summary = None
    if baseline:
        baseline_summary = {
            "heart_rate": f"{round(baseline.heart_rate_min)}–{round(baseline.heart_rate_max)} BPM",
            "spo2": f"{round(baseline.spo2_min)}–{round(baseline.spo2_max)}%",
            "temperature": f"{round(baseline.temperature_min, 1)}–{round(baseline.temperature_max, 1)}°C",
            "data_points": baseline.data_points,
            "period_days": baseline.period_days,
        }

    summary = f"{user_name}'s overall health score is {score}/100 ({label}). "
    if reasons:
        summary += f"Active concerns: {'; '.join(reasons[:2])}."
    else:
        summary += "All vitals are within personal baseline ranges."

    recommendation = reasons[0] if reasons else "Continue regular monitoring. All vitals appear stable."

    return {
        **analysis,
        "score": score,
        "score_label": label,
        "summary": summary,
        "recommendation": recommendation,
        "radar": radar,
        "recommendations": recommendations,
        "warnings": warnings,
        "baseline_summary": baseline_summary,
    }
