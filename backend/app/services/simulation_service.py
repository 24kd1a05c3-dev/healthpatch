"""Deterministic, explicitly labeled research scenario stream."""
import asyncio
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.models.telemetry import NormalizedTelemetry, Provenance, SourceType, Vitals
from app.services.telemetry_service import ingest_normalized

TARGETS = {
    'RESTING': (72, 98, 16, 36.7), 'WALKING': (95, 98, 22, 36.9),
    'RUNNING': (140, 97, 32, 37.2), 'SLEEPING': (60, 97, 12, 36.4),
    'STRESS': (105, 98, 24, 36.8), 'FEVER': (100, 97, 23, 38.5),
    'TACHYCARDIA': (135, 97, 24, 36.8), 'BRADYCARDIA': (42, 97, 13, 36.6),
    'LOW_SPO2': (100, 87, 27, 36.8), 'RECOVERY': (78, 98, 17, 36.8),
}


@dataclass
class Simulation:
    user_id: str
    scenario: str = 'RESTING'
    speed: int = 1
    stream_id: str = field(default_factory=lambda: str(uuid4()))
    state: str = 'PLAYING'
    second: int = 0
    values: list[float] = field(default_factory=lambda: list(TARGETS['RESTING']))
    signal_quality: float = 0.95
    battery: float = 100.0
    task: asyncio.Task | None = None

    def public(self):
        return {'state': self.state, 'scenario': self.scenario, 'speed': self.speed, 'second': self.second,
                'stream_id': self.stream_id, 'source_type': 'SYNTHETIC_SIMULATOR',
                'signal_quality': self.signal_quality, 'battery': self.battery}

    def sample(self):
        target = TARGETS[self.scenario]
        for i, goal in enumerate(target):
            self.values[i] += (goal - self.values[i]) * 0.035
        noise = math.sin(self.second * 0.37) * 0.6
        self.second += 1
        self.battery = max(0, self.battery - 0.002)
        return NormalizedTelemetry(user_id=self.user_id, device_id='SIMULATED-PATCH',
            stream_id=self.stream_id, sequence_number=self.second,
            source_type=SourceType.SYNTHETIC_SIMULATOR,
            vitals=Vitals(heart_rate=self.values[0] + noise, pulse_rate=self.values[0] + noise * 0.9,
                spo2=self.values[1] + noise * 0.05, respiratory_rate=self.values[2] + noise * 0.2,
                temperature=self.values[3] + noise * 0.01), signal_quality=self.signal_quality,
            provenance=Provenance(source_type=SourceType.SYNTHETIC_SIMULATOR, original_timestamp=self.second,
                record_id=self.scenario, processing_version='scenario-v1'))


sessions: dict[str, Simulation] = {}


async def run(sim: Simulation, db):
    try:
        while sim.second < 3600:
            if sim.state in ('PAUSED', 'DISCONNECTED'):
                await asyncio.sleep(0.2)
                continue
            if sim.state != 'PLAYING':
                break
            await ingest_normalized(sim.sample(), db)
            await asyncio.sleep(1 / sim.speed)
        sim.state = 'STOPPED'
    except asyncio.CancelledError:
        sim.state = 'STOPPED'
        raise
    except Exception:
        sim.state = 'ERROR'
