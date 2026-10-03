DEFAULT_THRESHOLDS = {
    "heart_rate": {
        "warning": {"min": 50, "max": 100},
        "critical": {"min": 40, "max": 150}
    },
    "spo2": {
        "warning": {"min": 94},
        "critical": {"min": 90}
    },
    "temperature": {
        "warning": {"min": 35.5, "max": 37.5},
        "critical": {"min": 35.0, "max": 39.0}
    },
    "battery": {
        "warning": {"min": 20},
        "critical": {"min": 10}
    }
}

def evaluate(measurement: dict) -> dict:
    if measurement.get("signal_quality", 1.0) < 0.5:
        return {"violations": [], "max_level": "low_quality", "details": {}}
        
    violations = []
    max_level = "normal"
    details = {}
    
    hr = measurement.get("heart_rate")
    if hr is not None:
        level = "normal"
        msg = ""
        if hr < DEFAULT_THRESHOLDS["heart_rate"]["critical"]["min"] or hr > DEFAULT_THRESHOLDS["heart_rate"]["critical"]["max"]:
            level = "critical"
            msg = f"Critical heart rate: {hr}"
        elif hr < DEFAULT_THRESHOLDS["heart_rate"]["warning"]["min"] or hr > DEFAULT_THRESHOLDS["heart_rate"]["warning"]["max"]:
            level = "warning"
            msg = f"Warning heart rate: {hr}"
        if level != "normal":
            violations.append({"metric": "heart_rate", "value": hr, "level": level, "message": msg})
            if max_level != "critical":
                max_level = level
        details["heart_rate"] = level
        
    spo2 = measurement.get("spo2")
    if spo2 is not None:
        level = "normal"
        msg = ""
        if spo2 < DEFAULT_THRESHOLDS["spo2"]["critical"]["min"]:
            level = "critical"
            msg = f"Critical SpO2: {spo2}"
        elif spo2 < DEFAULT_THRESHOLDS["spo2"]["warning"]["min"]:
            level = "warning"
            msg = f"Warning SpO2: {spo2}"
        if level != "normal":
            violations.append({"metric": "spo2", "value": spo2, "level": level, "message": msg})
            if level == "critical":
                max_level = "critical"
            elif level == "warning" and max_level != "critical":
                max_level = "warning"
        details["spo2"] = level
        
    temp = measurement.get("temperature")
    if temp is not None:
        level = "normal"
        msg = ""
        if temp < DEFAULT_THRESHOLDS["temperature"]["critical"]["min"] or temp > DEFAULT_THRESHOLDS["temperature"]["critical"]["max"]:
            level = "critical"
            msg = f"Critical temperature: {temp}"
        elif temp < DEFAULT_THRESHOLDS["temperature"]["warning"]["min"] or temp > DEFAULT_THRESHOLDS["temperature"]["warning"]["max"]:
            level = "warning"
            msg = f"Warning temperature: {temp}"
        if level != "normal":
            violations.append({"metric": "temperature", "value": temp, "level": level, "message": msg})
            if level == "critical":
                max_level = "critical"
            elif level == "warning" and max_level != "critical":
                max_level = "warning"
        details["temperature"] = level
        
    batt = measurement.get("battery")
    if batt is not None:
        level = "normal"
        msg = ""
        if batt < DEFAULT_THRESHOLDS["battery"]["critical"]["min"]:
            level = "critical"
            msg = f"Critical battery: {batt}"
        elif batt < DEFAULT_THRESHOLDS["battery"]["warning"]["min"]:
            level = "warning"
            msg = f"Warning battery: {batt}"
        if level != "normal":
            violations.append({"metric": "battery", "value": batt, "level": level, "message": msg})
            if level == "critical":
                max_level = "critical"
            elif level == "warning" and max_level != "critical":
                max_level = "warning"
        details["battery"] = level
        
    return {
        "violations": violations,
        "max_level": max_level,
        "details": details
    }
