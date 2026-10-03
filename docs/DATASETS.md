# Physiological datasets

HealthPatch supports de-identified, previously recorded data as **dataset replay**. Dataset replay is never evidence of a currently connected patient or device. The three source labels used throughout the system are:

- `SYNTHETIC_SIMULATOR`
- `DATASET_REPLAY`
- `LIVE_DEVICE` (reserved for future physical hardware)

## BIDMC PPG and Respiration Dataset

**Source:** PhysioNet, BIDMC PPG and Respiration Dataset v1.0.0  
**Dataset page:** https://physionet.org/content/bidmc/1.0.0/  
**Version DOI:** https://doi.org/10.13026/C2208R  
**License:** Open Data Commons Attribution License v1.0. The files are openly accessible subject to that license. HealthPatch does not redistribute them.

The dataset contains 53 eight-minute recordings derived from critically ill patients at Beth Israel Deaconess Medical Center. Waveforms are sampled at 125 Hz; numeric physiological parameters are sampled at 1 Hz.

### Signals used

| Source column | Normalized field | Sampling |
| --- | --- | --- |
| `PLETH` | `waveforms.ppg` | 125 Hz |
| `II` | `waveforms.ecg` | 125 Hz |
| `V` | `waveforms.ecg_v` | 125 Hz |
| `AVR` | `waveforms.ecg_avr` | 125 Hz |
| `RESP` in Signals CSV | `waveforms.respiration` | 125 Hz |
| `HR` | `vitals.heart_rate` | 1 Hz |
| `PULSE` | `vitals.pulse_rate` | 1 Hz |
| `SpO2` | `vitals.spo2` | 1 Hz |
| `RESP` in Numerics CSV | `vitals.respiratory_rate` | 1 Hz |

### Installation

Download the CSV representation from PhysioNet after reviewing its license. Place files under:

```text
backend/datasets/bidmc_csv/
  bidmc_01_Signals.csv
  bidmc_01_Numerics.csv
  bidmc_01_Breaths.csv
  bidmc_01_Fix.txt
  ...
```

Alternatively, set `DATASET_ROOT` to the directory containing `bidmc_csv`. Restart the API after adding records. Dataset files are intentionally excluded from this repository.

Record `bidmc_01` is installed in this local workspace. Dataset files are ignored by version control; source and license attribution must accompany any future distribution. Only installed records appear in the selector.

### Import and normalization

The importer discovers matching Signals and Numerics CSV pairs. It validates the required `Time [s]` and `PLETH` waveform columns, parses optional ECG and respiration columns, normalizes record IDs, and reads fixed metadata when present. Numeric rows are retained only as the small 1 Hz lookup series. Waveforms are streamed from disk in 25-sample batches; a full recording is never loaded into browser memory.

Original offsets are preserved as `provenance.original_timestamp`. Wall-clock emission time is stored as `provenance.replay_timestamp`; the dataset, record ID, source type, and processing version accompany every batch. No interpolation or synthetic jitter is applied to dataset-derived values.

Missing waveform samples are retained as null positions, not removed. The Signal Lab keeps a bounded 2,500-sample buffer per channel and uses extrema-preserving display decimation. Buckets containing gaps remain gaps. Display decimation is not used to alter stored source samples.

### Playback and limitations

At 1x speed, 25 samples at 125 Hz are emitted every 200 ms, preserving the original 8 ms sample interval. Speeds of 2x and 5x change delivery timing, not the recorded values or timestamps. Packet loss, latency, duplication, and temporary disconnects are injected after normalization in the transport layer and never modify source physiology.

Dataset replay is retrospective engineering and research data. It is not a live patient feed, is not intended for diagnosis, and may contain missing or invalid values from the source recording. HealthPatch does not infer unavailable temperature or activity values.

### Citation

Pimentel, M. A. F., Johnson, A. E. W., Charlton, P. H., Birrenkott, D., Watkinson, P. J., Tarassenko, L., & Clifton, D. A. (2017). *Toward a Robust Estimation of Respiratory Rate From Pulse Oximeters*. IEEE Transactions on Biomedical Engineering, 64(8), 1914-1923. https://doi.org/10.1109/TBME.2016.2613124
