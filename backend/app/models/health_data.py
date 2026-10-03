from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from app.config import settings
from app.models.telemetry import Provenance, SourceType

class HealthMeasurement(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    device_id: str = Field(min_length=3, max_length=80, pattern=r"^[A-Za-z0-9._:-]+$")
    user_id: str = Field(min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    heart_rate: float
    spo2: float
    temperature: float
    activity: str = Field(default="RESTING", max_length=40)
    battery: float
    signal_quality: float
    source_type: SourceType = SourceType.SYNTHETIC_SIMULATOR
    provenance: Provenance | None = None

    @model_validator(mode="after")
    def ensure_provenance(self):
        if self.timestamp.tzinfo is None:
            raise ValueError('Measurement timestamp must include a timezone')
        if self.source_type == SourceType.LIVE_DEVICE:
            age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
            if age < -300 or age > 86400:
                raise ValueError('Live measurement clock must be within the previous day and not over five minutes ahead')
        if self.provenance is None:
            self.provenance = Provenance(
                source_type=self.source_type,
                replay_timestamp=self.timestamp,
                processing_version=settings.TELEMETRY_PROCESSING_VERSION,
            )
        elif self.provenance.source_type != self.source_type:
            raise ValueError("Measurement source_type must match provenance source_type")
        return self

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
