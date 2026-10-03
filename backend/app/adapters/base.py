from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator

from app.models.telemetry import NormalizedTelemetry, SourceType


@dataclass(frozen=True)
class RecordingInfo:
    dataset: str
    record_id: str
    duration_seconds: float
    waveform_sample_rate_hz: float
    numeric_sample_rate_hz: float
    signals: list[str]
    metadata: dict[str, str]


class HealthDataSource(ABC):
    source_type: SourceType

    @abstractmethod
    def discover_recordings(self) -> list[RecordingInfo]: ...

    @abstractmethod
    def stream(self, record_id: str, user_id: str, start_seconds: float = 0) -> Iterator[NormalizedTelemetry]: ...


DeviceAdapter = HealthDataSource
