from typing import Iterator

from app.adapters.base import HealthDataSource, RecordingInfo
from app.models.telemetry import NormalizedTelemetry, SourceType


class SyntheticSimulatorAdapter(HealthDataSource):
    source_type = SourceType.SYNTHETIC_SIMULATOR

    def discover_recordings(self) -> list[RecordingInfo]:
        return []

    def stream(self, record_id: str, user_id: str, start_seconds: float = 0) -> Iterator[NormalizedTelemetry]:
        raise NotImplementedError("Synthetic telemetry is produced by the simulator process")
