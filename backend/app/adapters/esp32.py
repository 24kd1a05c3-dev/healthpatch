from typing import Iterator

from app.adapters.base import HealthDataSource, RecordingInfo
from app.models.telemetry import NormalizedTelemetry, SourceType


class ESP32Adapter(HealthDataSource):
    source_type = SourceType.LIVE_DEVICE

    @property
    def available(self) -> bool:
        return False

    def discover_recordings(self) -> list[RecordingInfo]:
        return []

    def stream(self, record_id: str, user_id: str, start_seconds: float = 0) -> Iterator[NormalizedTelemetry]:
        raise NotImplementedError("Physical patch transport is reserved for future hardware")
