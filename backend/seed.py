from pymongo import MongoClient, ASCENDING, DESCENDING
import bcrypt
from datetime import datetime, timedelta, timezone
import random

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def seed():
    client = MongoClient("mongodb://localhost:27017")
    db = client["healthpatch"]
    
    print("Dropping existing collections...")
    db.users.drop()
    db.devices.drop()
    db.health_measurements.drop()
    db.alerts.drop()
    db.emergency_events.drop()
    
    print("Creating indexes...")
    db.users.create_index("email", unique=True)
    db.devices.create_index("device_id", unique=True)
    db.health_measurements.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    db.alerts.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.emergency_events.create_index("user_id")
    
    print("Seeding users...")
    hashed_pwd = hash_password("demo123")
    now = datetime.now(timezone.utc)
    
    patient_id = db.users.insert_one({
        "email": "patient@healthpatch.io",
        "hashed_password": hashed_pwd,
        "full_name": "James Kowalski",
        "role": "patient",
        "blood_type": "O+",
        "medical_conditions": ["Hypertension", "Atrial Fibrillation"],
        "medications": ["Lisinopril 10mg", "Metoprolol 25mg"],
        "allergies": ["Penicillin"],
        "created_at": now
    }).inserted_id
    
    db.users.insert_one({
        "email": "doctor@healthpatch.io",
        "hashed_password": hashed_pwd,
        "full_name": "Dr. Elena Rivera",
        "role": "doctor",
        "assigned_patients": [str(patient_id)],
        "created_at": now
    })
    
    db.users.insert_one({
        "email": "caregiver@healthpatch.io",
        "hashed_password": hashed_pwd,
        "full_name": "Sarah Kowalski",
        "role": "caregiver",
        "assigned_patients": [str(patient_id)],
        "created_at": now
    })
    
    db.users.insert_one({
        "email": "admin@healthpatch.io",
        "hashed_password": hashed_pwd,
        "full_name": "System Admin",
        "role": "admin",
        "created_at": now
    })
    
    print("Seeding device...")
    db.devices.insert_one({
        "device_id": "SHP-ESP32-0001",
        "user_id": str(patient_id),
        "status": "ONLINE",
        "battery": 84,
        "firmware_version": "1.0.0",
        "model_name": "HealthPatch"
    })
    
    print("Seeding 24 hours of health data...")
    measurements = []
    alerts = []
    start_time = now - timedelta(hours=24)
    
    for i in range(720):
        t = start_time + timedelta(minutes=i*2)
        
        hr = 70 + 5 * random.random()
        spo2 = 98 + random.random()
        temp = 36.5 + 0.2 * random.random()
        
        # Add circadian
        hour = t.hour
        if 0 <= hour < 6:
            hr -= 10
        elif 14 <= hour < 18:
            hr += 10
            
        # Add anomaly
        if 300 < i < 305:
            hr = 135
            spo2 = 92
            if i == 302:
                alerts.append({
                    "user_id": str(patient_id),
                    "alert_type": "HealthAnomaly",
                    "level": "warning",
                    "title": "WARNING Health Alert",
                    "message": "Warning heart rate, Warning SpO2",
                    "device_id": "SHP-ESP32-0001",
                    "measurement_id": "seeded",
                    "created_at": t,
                    "acknowledged": False
                })
                
        measurements.append({
            "device_id": "SHP-ESP32-0001",
            "user_id": str(patient_id),
            "timestamp": t,
            "heart_rate": hr,
            "spo2": spo2,
            "temperature": temp,
            "activity": "RESTING",
            "battery": 84 - (i/720)*10,
            "signal_quality": 0.95
        })
        
    db.health_measurements.insert_many(measurements)
    if alerts:
        db.alerts.insert_many(alerts)
        
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed()
