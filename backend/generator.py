import os

BASE_DIR = r"d:\Documents\healthpatch\backend"
os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app", "models"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app", "ai"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app", "services"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "app", "routers"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "simulator"), exist_ok=True)

files = {}

files["requirements.txt"] = """fastapi==0.115.12
uvicorn[standard]==0.34.3
motor==3.7.1
pymongo==4.12.1
python-jose[cryptography]==3.4.0
passlib[bcrypt]==1.7.4
pydantic[email-validator]==2.11.4
python-dotenv==1.1.0
websockets==15.0.1
bcrypt==4.3.0
"""

files["app/__init__.py"] = ""

files["app/config.py"] = """import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "healthpatch")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "healthpatch-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
"""

files["app/database.py"] = """from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db = None

db_manager = DatabaseManager()

async def connect_db():
    logger.info("Connecting to MongoDB...")
    db_manager.client = AsyncIOMotorClient(settings.MONGODB_URI)
    db_manager.db = db_manager.client[settings.DATABASE_NAME]
    logger.info("Connected to MongoDB.")

async def close_db():
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
    logger.info("Closed MongoDB connection.")

def get_collection(name: str):
    return db_manager.db[name]
"""

files["app/models/__init__.py"] = ""

files["app/models/user.py"] = """from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from typing_extensions import Literal

Role = Literal["patient", "caregiver", "doctor", "admin"]

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Role = "patient"
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    phone: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserInDB(BaseModel):
    id: str
    email: EmailStr
    hashed_password: str
    full_name: str
    role: Role
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    assigned_doctor_id: Optional[str] = None
    assigned_patients: List[str] = Field(default_factory=list)
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
"""

files["app/models/device.py"] = """from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from typing_extensions import Literal

DeviceStatus = Literal["ONLINE", "OFFLINE", "LOW_BATTERY", "SYNCING", "ERROR"]

class DeviceCreate(BaseModel):
    device_id: str
    firmware_version: str = "1.0.0"

class DeviceResponse(BaseModel):
    device_id: str
    user_id: Optional[str] = None
    status: DeviceStatus
    battery: Optional[int] = None
    signal_quality: Optional[float] = None
    last_seen: Optional[datetime] = None
    firmware_version: str
    model_name: str = "HealthPatch"
    model_config = ConfigDict(from_attributes=True)

class DevicePair(BaseModel):
    user_id: str
"""

files["app/models/health_data.py"] = """from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

class HealthMeasurement(BaseModel):
    device_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: float
    spo2: float
    temperature: float
    activity: str = "RESTING"
    battery: float
    signal_quality: float

    @field_validator("heart_rate")
    @classmethod
    def validate_hr(cls, v):
        if not (0 <= v <= 300):
            raise ValueError("Heart rate must be between 0 and 300")
        return v

    @field_validator("spo2")
    @classmethod
    def validate_spo2(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("SpO2 must be between 0 and 100")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temp(cls, v):
        if not (25 <= v <= 45):
            raise ValueError("Temperature must be between 25 and 45")
        return v

    @field_validator("battery")
    @classmethod
    def validate_battery(cls, v):
        if not (0 <= v <= 100):
            raise ValueError("Battery must be between 0 and 100")
        return v

    @field_validator("signal_quality")
    @classmethod
    def validate_signal(cls, v):
        if not (0.0 <= v <= 1.0):
            raise ValueError("Signal quality must be between 0.0 and 1.0")
        return v

class HealthDataResponse(HealthMeasurement):
    id: str
    analysis: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class ECGRecord(BaseModel):
    device_id: str
    user_id: str
    timestamp: datetime
    waveform_data: List[float]
    duration_seconds: float
    sample_rate: int

class BaselineResponse(BaseModel):
    user_id: str
    heart_rate_mean: float
    heart_rate_std: float
    heart_rate_min: float
    heart_rate_max: float
    spo2_mean: float
    spo2_std: float
    spo2_min: float
    spo2_max: float
    temperature_mean: float
    temperature_std: float
    temperature_min: float
    temperature_max: float
    data_points: int
    period_days: int
    calculated_at: datetime
"""

files["app/models/alert.py"] = """from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from typing_extensions import Literal

AlertLevel = Literal["info", "warning", "critical"]

class Alert(BaseModel):
    user_id: str
    alert_type: str
    level: AlertLevel = "info"
    title: str
    message: str
    reasons: List[str] = Field(default_factory=list)
    anomaly_score: Optional[float] = None
    device_id: str
    measurement_id: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AlertResponse(Alert):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AlertAcknowledge(BaseModel):
    acknowledged_by: Optional[str] = None
"""

files["app/models/emergency.py"] = """from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from typing_extensions import Literal

TriggerSource = Literal["patient", "system", "caregiver"]
EmergencyStatus = Literal["active", "responding", "resolved"]

class EmergencyCreate(BaseModel):
    user_id: str
    triggered_by: TriggerSource = "patient"
    location: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None

class EmergencyEvent(BaseModel):
    user_id: str
    triggered_by: TriggerSource
    health_snapshot: Dict[str, Any]
    location: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    status: EmergencyStatus = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class EmergencyResponse(EmergencyEvent):
    id: str
    model_config = ConfigDict(from_attributes=True)
"""

files["app/security.py"] = """from datetime import datetime, timedelta, timezone
from typing import Any, Union, List
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
from app.database import get_collection
from app.models.user import UserInDB
from bson import ObjectId

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users_collection = get_collection("users")
    user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user_doc is None:
        raise credentials_exception
    
    user_doc["id"] = str(user_doc["_id"])
    return UserInDB(**user_doc)

def require_role(*roles: str):
    def role_checker(current_user: UserInDB = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return current_user
    return role_checker
"""

files["app/websocket_manager.py"] = """from fastapi import WebSocket
from typing import Dict, List
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_json(message)

    async def broadcast(self, message: dict):
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_json(message)

manager = ConnectionManager()
"""

files["app/ai/__init__.py"] = ""

files["app/ai/rule_engine.py"] = """DEFAULT_THRESHOLDS = {
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
"""

files["app/ai/baseline.py"] = """from datetime import datetime, timedelta, timezone
from app.models.health_data import BaselineResponse
import math

async def calculate_baseline(user_id: str, db) -> BaselineResponse | None:
    collection = db["health_measurements"]
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    cursor = collection.find({"user_id": user_id, "timestamp": {"$gte": seven_days_ago}})
    measurements = await cursor.to_list(length=10000)
    
    if len(measurements) < 10:
        return None
        
    hrs = [m["heart_rate"] for m in measurements if "heart_rate" in m]
    spo2s = [m["spo2"] for m in measurements if "spo2" in m]
    temps = [m["temperature"] for m in measurements if "temperature" in m]
    
    def calc_stats(data):
        if not data:
            return 0, 0, 0, 0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std = math.sqrt(variance)
        return mean, std, min(data), max(data)
        
    hr_mean, hr_std, hr_min, hr_max = calc_stats(hrs)
    spo2_mean, spo2_std, spo2_min, spo2_max = calc_stats(spo2s)
    temp_mean, temp_std, temp_min, temp_max = calc_stats(temps)
    
    return BaselineResponse(
        user_id=user_id,
        heart_rate_mean=hr_mean, heart_rate_std=hr_std, heart_rate_min=hr_min, heart_rate_max=hr_max,
        spo2_mean=spo2_mean, spo2_std=spo2_std, spo2_min=spo2_min, spo2_max=spo2_max,
        temperature_mean=temp_mean, temperature_std=temp_std, temperature_min=temp_min, temperature_max=temp_max,
        data_points=len(measurements),
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
"""

files["app/ai/anomaly_detector.py"] = """def detect_anomaly(measurement: dict, rule_result: dict, baseline_comparison: dict) -> dict:
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
"""

files["app/ai/engine.py"] = """from app.ai.rule_engine import evaluate
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
"""

files["app/services/__init__.py"] = ""

files["app/services/auth_service.py"] = """from app.models.user import UserCreate, UserResponse, UserInDB, TokenResponse
from app.security import hash_password, verify_password, create_access_token
from bson import ObjectId
from datetime import datetime, timezone

async def get_user_by_email(email: str, db) -> UserInDB | None:
    user_doc = await db["users"].find_one({"email": email})
    if user_doc:
        user_doc["id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None

async def get_user_by_id(user_id: str, db) -> UserInDB | None:
    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user_doc:
        user_doc["id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None

async def register_user(user_data: UserCreate, db) -> UserResponse:
    doc = user_data.model_dump()
    doc["hashed_password"] = hash_password(doc.pop("password"))
    doc["created_at"] = datetime.now(timezone.utc)
    
    result = await db["users"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return UserResponse(**doc)

async def authenticate_user(email: str, password: str, db) -> TokenResponse | None:
    user = await get_user_by_email(email, db)
    if not user or not verify_password(password, user.hashed_password):
        return None
        
    token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user.model_dump())
    )
"""

files["app/services/health_service.py"] = """from app.models.health_data import HealthMeasurement, HealthDataResponse, BaselineResponse
from app.ai.engine import analyze_measurement
from datetime import datetime, timedelta, timezone
from app.services.device_service import update_device_status
import pymongo

async def ingest_measurement(measurement: HealthMeasurement, db) -> HealthDataResponse:
    doc = measurement.model_dump()
    analysis = await analyze_measurement(doc, db)
    doc["analysis"] = analysis
    
    result = await db["health_measurements"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    
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

async def get_history(user_id: str, period: str, db) -> list[HealthDataResponse]:
    periods = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    td = periods.get(period, timedelta(hours=24))
    since = datetime.now(timezone.utc) - td
    
    cursor = db["health_measurements"].find(
        {"user_id": user_id, "timestamp": {"$gte": since}},
        sort=[("timestamp", pymongo.ASCENDING)]
    )
    docs = await cursor.to_list(length=10000)
    for d in docs:
        d["id"] = str(d["_id"])
    return [HealthDataResponse(**d) for d in docs]

async def get_baseline(user_id: str, db) -> BaselineResponse | None:
    from app.ai.baseline import calculate_baseline
    return await calculate_baseline(user_id, db)
"""

files["app/services/alert_service.py"] = """from app.models.alert import Alert, AlertResponse
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
        
    cursor = db["alerts"].find(query, sort=[("created_at", pymongo.DESCENDING)]).limit(limit)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["id"] = str(d["_id"])
    return [AlertResponse(**d) for d in docs]

async def acknowledge_alert(alert_id: str, user_id: str, db) -> AlertResponse | None:
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
"""

files["app/services/device_service.py"] = """from app.models.device import DeviceCreate, DeviceResponse
from datetime import datetime, timezone

async def register_device(device_data: DeviceCreate, db) -> DeviceResponse:
    doc = device_data.model_dump()
    doc["status"] = "OFFLINE"
    doc["model_name"] = "HealthPatch"
    await db["devices"].insert_one(doc)
    return DeviceResponse(**doc)

async def pair_device(device_id: str, user_id: str, db) -> DeviceResponse | None:
    doc = await db["devices"].find_one_and_update(
        {"device_id": device_id},
        {"$set": {"user_id": user_id}},
        return_document=True
    )
    if doc:
        return DeviceResponse(**doc)
    return None

async def get_devices(user_id: str, db) -> list[DeviceResponse]:
    cursor = db["devices"].find({"user_id": user_id})
    docs = await cursor.to_list(length=100)
    return [DeviceResponse(**d) for d in docs]

async def get_device(device_id: str, db) -> DeviceResponse | None:
    doc = await db["devices"].find_one({"device_id": device_id})
    if doc:
        return DeviceResponse(**doc)
    return None

async def update_device_status(device_id: str, status: str, battery: float, signal_quality: float, db):
    await db["devices"].update_one(
        {"device_id": device_id},
        {"$set": {
            "status": status,
            "battery": battery,
            "signal_quality": signal_quality,
            "last_seen": datetime.now(timezone.utc)
        }}
    )
"""

files["app/routers/__init__.py"] = ""

files["app/routers/auth.py"] = """from fastapi import APIRouter, Depends, HTTPException, status
from app.models.user import UserCreate, TokenResponse, LoginRequest
from app.services.auth_service import register_user, authenticate_user, get_user_by_email
from app.database import get_collection

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db=Depends(lambda: get_collection("users").database)):
    existing = await get_user_by_email(user_data.email, db)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await register_user(user_data, db)
    return await authenticate_user(user_data.email, user_data.password, db)

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db=Depends(lambda: get_collection("users").database)):
    token = await authenticate_user(req.email, req.password, db)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token

@router.post("/refresh")
async def refresh():
    pass

@router.post("/logout")
async def logout():
    return {"status": "success"}
"""

files["app/routers/users.py"] = """from fastapi import APIRouter, Depends, HTTPException
from app.models.user import UserInDB, UserResponse
from app.security import get_current_user, require_role
from app.database import get_collection
from bson import ObjectId

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.get("/patients", response_model=list[UserResponse])
async def list_patients(current_user: UserInDB = Depends(require_role("doctor", "admin")), db=Depends(lambda: get_collection("users").database)):
    if current_user.role == "doctor":
        cursor = db["users"].find({"_id": {"$in": [ObjectId(pid) for pid in current_user.assigned_patients]}})
    else:
        cursor = db["users"].find({"role": "patient"})
        
    docs = await cursor.to_list(length=100)
    for d in docs:
        d["id"] = str(d["_id"])
    return [UserResponse(**d) for d in docs]
"""

files["app/routers/devices.py"] = """from fastapi import APIRouter, Depends, HTTPException
from app.models.device import DeviceCreate, DeviceResponse, DevicePair
from app.services.device_service import register_device, get_devices, get_device, pair_device
from app.models.user import UserInDB
from app.security import get_current_user
from app.database import get_collection

router = APIRouter(prefix="/devices", tags=["devices"])

@router.post("/", response_model=DeviceResponse)
async def create_device(device_data: DeviceCreate, db=Depends(lambda: get_collection("devices").database)):
    existing = await get_device(device_data.device_id, db)
    if existing:
        raise HTTPException(status_code=409, detail="Device already exists")
    return await register_device(device_data, db)

@router.get("/", response_model=list[DeviceResponse])
async def list_devices(current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("devices").database)):
    return await get_devices(current_user.id, db)

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device_info(device_id: str, db=Depends(lambda: get_collection("devices").database)):
    dev = await get_device(device_id, db)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    return dev

@router.post("/{device_id}/pair", response_model=DeviceResponse)
async def pair(device_id: str, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("devices").database)):
    dev = await pair_device(device_id, current_user.id, db)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    return dev
"""

files["app/routers/health_data.py"] = """from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.models.health_data import HealthMeasurement, HealthDataResponse, BaselineResponse
from app.services.health_service import ingest_measurement, get_latest, get_history, get_baseline
from app.services.alert_service import create_alert_from_analysis
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user
from app.websocket_manager import manager

router = APIRouter(prefix="/health-data", tags=["health"])

@router.post("/", response_model=HealthDataResponse)
async def ingest(measurement: HealthMeasurement, db=Depends(lambda: get_collection("health_measurements").database)):
    response = await ingest_measurement(measurement, db)
    
    # Broadcast
    await manager.send_to_user(measurement.user_id, {"type": "health_data", "data": response.model_dump(mode="json")})
    
    # Create alert if needed
    if response.analysis and response.analysis.get("risk_level") in ["WARNING", "CRITICAL"]:
        alert = await create_alert_from_analysis(
            measurement.user_id,
            measurement.device_id,
            response.id,
            response.analysis,
            db
        )
        if alert:
            await manager.send_to_user(measurement.user_id, {"type": "alert", "data": alert.model_dump(mode="json")})
            
    return response

@router.get("/latest", response_model=Optional[HealthDataResponse])
async def latest(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    return await get_latest(uid, db)

@router.get("/history", response_model=list[HealthDataResponse])
async def history(period: str = "24h", user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    return await get_history(uid, period, db)

@router.get("/baseline", response_model=Optional[BaselineResponse])
async def baseline(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    return await get_baseline(uid, db)

@router.get("/analysis")
async def analysis(user_id: Optional[str] = None, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("health_measurements").database)):
    uid = user_id or current_user.id
    latest_data = await get_latest(uid, db)
    if latest_data and latest_data.analysis:
        return latest_data.analysis
    raise HTTPException(status_code=404, detail="No analysis found")
"""

files["app/routers/alerts.py"] = """from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.models.alert import AlertResponse, AlertAcknowledge
from app.services.alert_service import get_alerts, acknowledge_alert
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("/", response_model=list[AlertResponse])
async def list_alerts(level: Optional[str] = None, user_id: Optional[str] = None, limit: int = 50, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("alerts").database)):
    uid = user_id or current_user.id
    return await get_alerts(db, uid, level, limit)

@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: str, db=Depends(lambda: get_collection("alerts").database)):
    from bson import ObjectId
    doc = await db["alerts"].find_one({"_id": ObjectId(alert_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Alert not found")
    doc["id"] = str(doc["_id"])
    return AlertResponse(**doc)

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def ack_alert(alert_id: str, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("alerts").database)):
    alert = await acknowledge_alert(alert_id, current_user.id, db)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert
"""

files["app/routers/emergency.py"] = """from fastapi import APIRouter, Depends, HTTPException
from app.models.emergency import EmergencyCreate, EmergencyResponse
from app.services.health_service import get_latest
from app.services.alert_service import create_alert
from app.database import get_collection
from app.models.user import UserInDB
from app.security import get_current_user
from app.websocket_manager import manager
from datetime import datetime, timezone
import pymongo

router = APIRouter(prefix="/emergency", tags=["emergency"])

@router.post("/", response_model=EmergencyResponse)
async def create_emergency(data: EmergencyCreate, current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("emergency_events").database)):
    latest = await get_latest(data.user_id, db)
    snapshot = latest.model_dump(mode="json") if latest else {}
    
    doc = {
        "user_id": data.user_id,
        "triggered_by": data.triggered_by,
        "health_snapshot": snapshot,
        "location": data.location,
        "notes": data.notes,
        "status": "active",
        "created_at": datetime.now(timezone.utc)
    }
    
    result = await db["emergency_events"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    
    await create_alert({
        "user_id": data.user_id,
        "alert_type": "Emergency",
        "level": "critical",
        "title": "EMERGENCY ACTIVATED",
        "message": f"Emergency triggered by {data.triggered_by}",
        "reasons": ["User triggered emergency mode"],
        "device_id": snapshot.get("device_id", "unknown"),
        "measurement_id": snapshot.get("id", "unknown"),
        "created_at": datetime.now(timezone.utc)
    }, db)
    
    resp = EmergencyResponse(**doc)
    await manager.broadcast({"type": "emergency", "data": resp.model_dump(mode="json")})
    return resp

@router.get("/history", response_model=list[EmergencyResponse])
async def get_history(current_user: UserInDB = Depends(get_current_user), db=Depends(lambda: get_collection("emergency_events").database)):
    cursor = db["emergency_events"].find({"user_id": current_user.id}, sort=[("created_at", pymongo.DESCENDING)])
    docs = await cursor.to_list(length=100)
    for d in docs:
        d["id"] = str(d["_id"])
    return [EmergencyResponse(**d) for d in docs]
"""

files["app/routers/websocket.py"] = """from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket_manager import manager
from jose import jwt, JWTError
from app.config import settings

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str):
    try:
        jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
"""

files["app/main.py"] = """from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_db, close_db
from app.routers import auth, users, devices, health_data, alerts, emergency, websocket

app = FastAPI(title="HealthPatch API", description="Backend for HealthPatch monitoring system", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Should use settings.CORS_ORIGINS in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_event_handler("startup", connect_db)
app.add_event_handler("shutdown", close_db)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(devices.router)
app.include_router(health_data.router)
app.include_router(alerts.router)
app.include_router(emergency.router)
app.include_router(websocket.router)

@app.get("/")
async def root():
    return {"message": "Welcome to HealthPatch API"}

@app.get("/health")
async def health():
    return {"status": "ok"}
"""

files["simulator/__init__.py"] = ""

files["simulator/sensor_simulator.py"] = """import asyncio
import aiohttp
import argparse
import random
import sys
import threading
from datetime import datetime, timezone
import json

try:
    import msvcrt
    has_msvcrt = True
except ImportError:
    has_msvcrt = False
    import select

class Simulator:
    def __init__(self, device_id, email, password, url, interval):
        self.device_id = device_id
        self.email = email
        self.password = password
        self.url = url
        self.interval = interval
        self.mode = "n"
        self.battery = 100.0
        self.running = True
        self.token = None
        self.user_id = None
        
    async def login(self, session):
        print(f"Logging in as {self.email}...")
        async with session.post(f"{self.url}/auth/login", json={"email": self.email, "password": self.password}) as resp:
            if resp.status == 200:
                data = await resp.json()
                self.token = data["access_token"]
                self.user_id = data["user"]["id"]
                print("Login successful.")
                return True
            else:
                print(f"Login failed: {await resp.text()}")
                return False

    def get_readings(self):
        hr_base = 72
        spo2_base = 98
        temp_base = 36.6
        
        if self.mode == "t" or self.mode == "a":
            hr_base = 135
        if self.mode == "h" or self.mode == "a":
            spo2_base = 88
        if self.mode == "f" or self.mode == "a":
            temp_base = 38.8
            
        hr = hr_base + random.uniform(-3, 3)
        spo2 = min(100, max(0, spo2_base + random.uniform(-1, 1)))
        temp = temp_base + random.uniform(-0.2, 0.2)
        
        self.battery = max(0.0, self.battery - 0.1)
        signal = random.uniform(0.85, 0.99)
        if random.random() < 0.05:
            signal = random.uniform(0.3, 0.7)
            
        return {
            "device_id": self.device_id,
            "user_id": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heart_rate": round(hr, 1),
            "spo2": round(spo2, 1),
            "temperature": round(temp, 1),
            "battery": round(self.battery, 1),
            "signal_quality": round(signal, 2),
            "activity": "RESTING"
        }

    async def run(self):
        async with aiohttp.ClientSession() as session:
            if not await self.login(session):
                return
                
            headers = {"Authorization": f"Bearer {self.token}"}
            
            while self.running:
                data = self.get_readings()
                try:
                    async with session.post(f"{self.url}/health-data/", json=data, headers=headers) as resp:
                        if resp.status == 200:
                            print(f"Sent: HR={data['heart_rate']} SpO2={data['spo2']} Temp={data['temperature']} Batt={data['battery']}")
                        else:
                            print(f"Failed to send: {await resp.text()}")
                except Exception as e:
                    print(f"Error sending data: {e}")
                    
                await asyncio.sleep(self.interval)

def keyboard_listener(sim):
    print("Press 't' for tachycardia, 'h' for hypoxemia, 'f' for fever, 'a' for all, 'n' for normal, 'q' to quit")
    while sim.running:
        key = None
        if has_msvcrt:
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
        else:
            dr, _, _ = select.select([sys.stdin], [], [], 0.1)
            if dr:
                key = sys.stdin.read(1).lower()
                
        if key:
            if key == 'q':
                sim.running = False
            elif key in ['t', 'h', 'f', 'a', 'n']:
                sim.mode = key
                print(f"\\nMode changed to: {key}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", default="SHP-ESP32-0001")
    parser.add_argument("--email", default="patient@healthpatch.io")
    parser.add_argument("--password", default="demo123")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--interval", type=float, default=2.0)
    args = parser.parse_args()
    
    sim = Simulator(args.device_id, args.email, args.password, args.url, args.interval)
    
    t = threading.Thread(target=keyboard_listener, args=(sim,))
    t.daemon = True
    t.start()
    
    await sim.run()

if __name__ == "__main__":
    asyncio.run(main())
"""

files["seed.py"] = """from pymongo import MongoClient, ASCENDING, DESCENDING
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
"""

for path, content in files.items():
    filepath = os.path.join(BASE_DIR, path)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Files generated successfully!")
