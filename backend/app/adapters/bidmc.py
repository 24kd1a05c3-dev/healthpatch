import csv
import re
import math
import json
from hashlib import sha256
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.adapters.base import HealthDataSource, RecordingInfo
from app.config import settings
from app.models.telemetry import NormalizedTelemetry, Provenance, SourceType, Vitals, WaveformBatch


class DatasetFormatError(ValueError):
    pass


class BIDMCDatasetAdapter(HealthDataSource):
    source_type = SourceType.DATASET_REPLAY
    waveform_sample_rate_hz = 125.0
    numeric_sample_rate_hz = 1.0
    batch_samples = 25

    def __init__(self, root: str | Path | None = None):
        configured = Path(root or settings.DATASET_ROOT)
        if not configured.is_absolute():
            configured = Path(__file__).resolve().parents[2] / configured
        self.root = configured / "bidmc_csv" if (configured / "bidmc_csv").exists() else configured

    @staticmethod
    def canonical_record_id(value: str) -> str:
        match = re.fullmatch(r"bidmc_?(\d{2})", value.lower())
        if not match:
            raise DatasetFormatError("BIDMC record IDs must look like bidmc_01")
        return f"bidmc_{match.group(1)}"

    def _path(self, record_id: str, suffix: str) -> Path:
        return self.root / f"{self.canonical_record_id(record_id)}_{suffix}"

    def verify_integrity(self, record_id):
        manifest = json.loads(Path(__file__).with_name('bidmc_manifest.json').read_text(encoding='utf-8'))
        expected = manifest['records'].get(record_id)
        if not expected:
            raise DatasetFormatError('Record is not approved in the dataset integrity manifest')
        for suffix, digest in expected.items():
            path = self._path(record_id, suffix)
            if not path.is_file() or sha256(path.read_bytes()).hexdigest() != digest:
                raise DatasetFormatError(f'Dataset integrity check failed for {path.name}')

    def discover_recordings(self) -> list[RecordingInfo]:
        if not self.root.exists():
            return []
        recordings = []
        for signal_path in sorted(self.root.glob("bidmc_??_Signals.csv")):
            record_id = signal_path.name.removesuffix("_Signals.csv")
            if not self._path(record_id, "Numerics.csv").exists():
                continue
            recordings.append(RecordingInfo(
                dataset="BIDMC", record_id=record_id,
                duration_seconds=self._duration(signal_path),
                waveform_sample_rate_hz=self.waveform_sample_rate_hz,
                numeric_sample_rate_hz=self.numeric_sample_rate_hz,
                signals=["ppg", "ecg_ii", "ecg_v", "ecg_avr", "respiration", "heart_rate", "pulse_rate", "spo2", "respiratory_rate"],
                metadata=self._metadata(record_id),
            ))
        return recordings

    def _duration(self, path: Path) -> float:
        last = 0.0
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            for row in csv.DictReader(handle):
                last = self._number(row, ("Time [s]", "Time", "time")) or last
        return last

    def _metadata(self, record_id: str) -> dict[str, str]:
        path = self._path(record_id, "Fix.txt")
        if not path.exists():
            return {}
        values = {}
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key.strip()] = value.strip()
        return values

    @staticmethod
    def _number(row: dict[str, str], names: tuple[str, ...]) -> float | None:
        lowered = {key.strip().lower(): value for key, value in row.items() if key}
        for name in names:
            raw = lowered.get(name.lower())
            if raw not in (None, "", "NaN", "nan"):
                try:
                    value = float(raw)
                    if not math.isfinite(value):
                        raise ValueError('Non-finite measurement')
                    return value
                except ValueError as exc:
                    raise DatasetFormatError(f"Invalid numeric value for {name}: {raw}") from exc
        return None

    def _numerics(self, record_id: str) -> tuple[list[float], list[Vitals]]:
        path = self._path(record_id, "Numerics.csv")
        if not path.exists():
            raise DatasetFormatError(f"Missing numerics file: {path.name}")
        times, rows = [], []
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise DatasetFormatError(f"No columns found in {path.name}")
            for row in reader:
                timestamp = self._number(row, ("Time [s]", "Time", "time"))
                if timestamp is None:
                    raise DatasetFormatError('Numeric sample timestamp is missing')
                if times and not math.isclose(timestamp - times[-1], 1 / self.numeric_sample_rate_hz, abs_tol=0.0001):
                    raise DatasetFormatError('Numeric timestamps must follow the declared sample cadence')
                times.append(timestamp)
                rows.append(Vitals(
                    heart_rate=self._number(row, ("HR", "Heart Rate")),
                    pulse_rate=self._number(row, ("PULSE", "Pulse Rate", "PR")),
                    spo2=self._number(row, ("SpO2", "SPO2")),
                    respiratory_rate=self._number(row, ("RESP", "Respiratory Rate", "RR")),
                ))
        if not rows:
            raise DatasetFormatError(f"No numeric measurements found in {path.name}")
        return times, rows

    def stream(self, record_id: str, user_id: str, start_seconds: float = 0) -> Iterator[NormalizedTelemetry]:
        record_id = self.canonical_record_id(record_id)
        if settings.ENVIRONMENT.lower() == 'production':
            self.verify_integrity(record_id)
        path = self._path(record_id, "Signals.csv")
        if not path.exists():
            raise DatasetFormatError(f"Missing signals file: {path.name}")
        numeric_times, numeric_rows = self._numerics(record_id)
        batch: list[dict[str, str]] = []
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            columns = {name.strip().lower() for name in (reader.fieldnames or [])}
            if not {"time [s]", "pleth"}.issubset(columns):
                raise DatasetFormatError(f"{path.name} must contain Time [s] and PLETH columns")
            previous_offset = None
            for row in reader:
                offset = self._number(row, ("Time [s]", "Time", "time"))
                if offset is None:
                    raise DatasetFormatError('Waveform sample timestamp is missing')
                if previous_offset is not None and not math.isclose(offset - previous_offset, 1 / self.waveform_sample_rate_hz, abs_tol=0.0001):
                    raise DatasetFormatError('Waveform timestamps must follow the declared sample cadence')
                previous_offset = offset
                if offset < start_seconds:
                    continue
                batch.append(row)
                if len(batch) == self.batch_samples:
                    yield self._normalize_batch(record_id, user_id, batch, numeric_times, numeric_rows)
                    batch = []
            if batch:
                yield self._normalize_batch(record_id, user_id, batch, numeric_times, numeric_rows)

    def _normalize_batch(self, record_id, user_id, batch, numeric_times, numeric_rows):
        offset = self._number(batch[0], ("Time [s]", "Time", "time")) or 0.0
        numeric_index = max(0, bisect_right(numeric_times, offset) - 1)

        def values(names):
            return [self._number(row, names) for row in batch]

        replay_time = datetime.now(timezone.utc)
        return NormalizedTelemetry(
            device_id="DATASET-BIDMC-01", user_id=user_id,
            source_type=SourceType.DATASET_REPLAY, timestamp=replay_time,
            vitals=numeric_rows[numeric_index],
            waveforms=WaveformBatch(
                sample_rate_hz=self.waveform_sample_rate_hz,
                start_offset_seconds=offset,
                sample_interval_ms=1000 / self.waveform_sample_rate_hz,
                ppg=values(("PLETH", "PPG")), ecg=values(("II", "ECG")),
                ecg_v=values(("V",)), ecg_avr=values(("AVR", "aVR")),
                respiration=values(("RESP", "Respiration")),
            ),
            provenance=Provenance(
                source_type=SourceType.DATASET_REPLAY, dataset_name="BIDMC", record_id=record_id,
                original_timestamp=offset, replay_timestamp=replay_time,
                processing_version=settings.TELEMETRY_PROCESSING_VERSION,
            ),
        )
