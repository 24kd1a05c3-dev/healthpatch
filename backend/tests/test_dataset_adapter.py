import csv

import pytest

from app.adapters.bidmc import BIDMCDatasetAdapter, DatasetFormatError
from app.models.telemetry import SourceType


def write_csv(path, headers, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def test_bidmc_discovers_and_normalizes_batches(tmp_path):
    write_csv(
        tmp_path / "bidmc_01_Signals.csv",
        ["Time [s]", "PLETH", "II", "V", "AVR", "RESP"],
        [[index / 125, index, index + 100, index + 150, index + 175, index + 200] for index in range(30)],
    )
    write_csv(
        tmp_path / "bidmc_01_Numerics.csv",
        ["Time [s]", "HR", "PULSE", "RESP", "SpO2"],
        [[0, 72, 71, 16, 98]],
    )

    adapter = BIDMCDatasetAdapter(tmp_path)
    recordings = adapter.discover_recordings()
    assert len(recordings) == 1
    assert recordings[0].record_id == "bidmc_01"

    batches = list(adapter.stream("bidmc01", "patient-1"))
    assert [len(batch.waveforms.ppg) for batch in batches] == [25, 5]
    assert batches[0].vitals.heart_rate == 72
    assert batches[0].waveforms.sample_interval_ms == 8
    assert batches[0].waveforms.ecg_v[0] == 150
    assert batches[0].waveforms.ecg_avr[0] == 175
    assert batches[0].source_type == SourceType.DATASET_REPLAY
    assert batches[0].provenance.original_timestamp == 0
    assert batches[0].provenance.record_id == "bidmc_01"


def test_bidmc_rejects_missing_required_columns(tmp_path):
    write_csv(tmp_path / "bidmc_01_Signals.csv", ["Time [s]", "II"], [[0, 1]])
    write_csv(tmp_path / "bidmc_01_Numerics.csv", ["Time [s]", "HR"], [[0, 72]])
    adapter = BIDMCDatasetAdapter(tmp_path)
    with pytest.raises(DatasetFormatError, match="PLETH"):
        list(adapter.stream("bidmc_01", "patient-1"))
