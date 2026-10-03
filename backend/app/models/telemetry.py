from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict, model_validator


class SourceType(str, Enum):
    SYNTHETIC_SIMULATOR = "SYNTHETIC_SIMULATOR"
    DATASET_REPLAY = "DATASET_REPLAY"
    LIVE_DEVICE = "LIVE_DEVICE"


class ReplayState(str, Enum):
    DATASET_LOADING = "DATASET_LOADING"
    CONNECTED = "CONNECTED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class Provenance(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    source_type: SourceType
    dataset_name: str | None = None
    record_id: str | None = None
    original_timestamp: float | None = None
    replay_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_version: str


class Vitals(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    heart_rate: float | None = Field(default=None, ge=0, le=300)
    pulse_rate: float | None = Field(default=None, ge=0, le=300)
    spo2: float | None = Field(default=None, ge=0, le=100)
    respiratory_rate: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = Field(default=None, ge=25, le=45)


class WaveformBatch(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    sample_rate_hz: float = Field(gt=0)
    start_offset_seconds: float = Field(ge=0)
    sample_interval_ms: float = Field(gt=0)
    ppg: list[float | None] = Field(default_factory=list)
    ecg: list[float | None] = Field(default_factory=list)
    ecg_v: list[float | None] = Field(default_factory=list)
    ecg_avr: list[float | None] = Field(default_factory=list)
    respiration: list[float | None] = Field(default_factory=list)


class NormalizedTelemetry(BaseModel):
    stream_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_number: int = Field(default=0, ge=0)
    device_id: str
    user_id: str
    source_type: SourceType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    vitals: Vitals
    waveforms: WaveformBatch | None = None
    signal_quality: float | None = Field(default=None, ge=0, le=1)
    provenance: Provenance

    @model_validator(mode='after')
    def validate_source_and_clock(self):
        if self.source_type != self.provenance.source_type:
            raise ValueError('Telemetry source must match its provenance')
        if self.timestamp.tzinfo is None:
            raise ValueError('Telemetry timestamp must include a timezone')
        if self.source_type == SourceType.LIVE_DEVICE and self.provenance.original_timestamp is not None:
            raise ValueError('Live telemetry uses its UTC acquisition timestamp, not a replay offset')
        return self


class FailureInjection(BaseModel):
    packet_loss_percent: float = Field(default=0, ge=0, le=100)
    duplicate_percent: float = Field(default=0, ge=0, le=100)
    latency_ms: int = Field(default=0, ge=0, le=30_000)
    disconnect_every_batches: int | None = Field(default=None, ge=1)
    disconnect_duration_ms: int = Field(default=1000, ge=100, le=30_000)


class ReplayStartRequest(BaseModel):
    dataset: Literal["BIDMC"] = "BIDMC"
    record_id: str = Field(pattern=r"^bidmc_?\d{2}$")
    speed: Literal[1, 2, 5] = 1
    user_id: str | None = None
    failures: FailureInjection = Field(default_factory=FailureInjection)


class ReplaySeekRequest(BaseModel):
    position_seconds: float = Field(ge=0, le=480)


class ReplaySpeedRequest(BaseModel):
    speed: Literal[1, 2, 5]
