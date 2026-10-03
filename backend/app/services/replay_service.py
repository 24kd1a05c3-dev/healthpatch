import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from app.services.telemetry_service import ingest_normalized

from app.adapters.bidmc import BIDMCDatasetAdapter, DatasetFormatError
from app.models.telemetry import FailureInjection, ReplayState
from app.websocket_manager import manager

logger = logging.getLogger(__name__)


@dataclass
class ReplaySession:
    user_id: str
    record_id: str
    speed: int
    failures: FailureInjection
    duration_seconds: float
    position_seconds: float = 0
    state: ReplayState = ReplayState.DATASET_LOADING
    task: asyncio.Task | None = None
    gate: asyncio.Event = field(default_factory=asyncio.Event)
    event_history: list[dict] = field(default_factory=list)
    stream_id: str = field(default_factory=lambda: str(uuid4()))

    def public(self) -> dict:
        return {
            "twin_id": "TWIN-DATASET-BIDMC-01",
            "stream_id": self.stream_id,
            "device_id": "DATASET-BIDMC-01",
            "source_type": "DATASET_REPLAY",
            "dataset": "BIDMC",
            "record_id": self.record_id,
            "state": self.state.value,
            "position_seconds": round(self.position_seconds, 3),
            "duration_seconds": self.duration_seconds,
            "speed": self.speed,
            "last_synchronization": datetime.now(timezone.utc).isoformat(),
            "events": self.event_history[-20:],
        }


class DatasetReplayEngine:
    def __init__(self):
        self.adapter = BIDMCDatasetAdapter()
        self.sessions: dict[str, ReplaySession] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def recordings(self) -> list[dict]:
        return [recording.__dict__ for recording in self.adapter.discover_recordings()]

    def status(self, user_id: str) -> dict:
        session = self.sessions.get(user_id)
        return session.public() if session else {
            "twin_id": "TWIN-DATASET-BIDMC-01", "source_type": "DATASET_REPLAY",
            "state": "STOPPED", "position_seconds": 0,
        }

    async def start(self, user_id: str, record_id: str, speed: int, failures: FailureInjection, db, position: float = 0):
        lock = self._locks.setdefault(user_id, asyncio.Lock())
        async with lock:
            await self._cancel(user_id)
            record_id = self.adapter.canonical_record_id(record_id)
            recording = next((r for r in self.adapter.discover_recordings() if r.record_id == record_id), None)
            if not recording:
                raise DatasetFormatError(f"Recording {record_id} was not found under {self.adapter.root}")
            if position > recording.duration_seconds:
                raise DatasetFormatError("Seek position exceeds recording duration")
            session = ReplaySession(user_id, record_id, speed, failures, recording.duration_seconds, position)
            session.gate.set()
            self.sessions[user_id] = session
            self._event(session, ReplayState.CONNECTED)
            session.task = asyncio.create_task(self._run(session, db))
            return session.public()

    async def pause(self, user_id: str, db):
        session = self._require(user_id)
        session.gate.clear()
        self._event(session, ReplayState.PAUSED)
        await self._sync_twin(session, db)
        await self._broadcast_state(session)
        return session.public()

    async def resume(self, user_id: str, db):
        session = self._require(user_id)
        session.gate.set()
        self._event(session, ReplayState.PLAYING)
        await self._sync_twin(session, db)
        await self._broadcast_state(session)
        return session.public()

    async def stop(self, user_id: str, db):
        session = self._require(user_id)
        await self._cancel(user_id)
        self._event(session, ReplayState.STOPPED)
        await self._sync_twin(session, db)
        await self._broadcast_state(session)
        return session.public()

    async def restart(self, user_id: str, db):
        session = self._require(user_id)
        return await self.start(user_id, session.record_id, session.speed, session.failures, db, 0)

    async def seek(self, user_id: str, position: float, db):
        session = self._require(user_id)
        was_paused = session.state == ReplayState.PAUSED
        result = await self.start(user_id, session.record_id, session.speed, session.failures, db, position)
        if was_paused:
            return await self.pause(user_id, db)
        return result

    async def set_speed(self, user_id: str, speed: int, db):
        session = self._require(user_id)
        session.speed = speed
        await self._sync_twin(session, db)
        return session.public()

    def _require(self, user_id: str) -> ReplaySession:
        session = self.sessions.get(user_id)
        if not session:
            raise DatasetFormatError("No replay session exists for this user")
        return session

    async def _cancel(self, user_id: str):
        existing = self.sessions.get(user_id)
        if existing and existing.task and not existing.task.done():
            existing.task.cancel()
            try:
                await existing.task
            except asyncio.CancelledError:
                pass

    def _event(self, session: ReplaySession, state: ReplayState, detail: str | None = None):
        session.state = state
        session.event_history.append({"state": state.value, "at": datetime.now(timezone.utc).isoformat(), "detail": detail})

    async def _run(self, session: ReplaySession, db):
        try:
            self._event(session, ReplayState.PLAYING)
            await self._broadcast_state(session)
            for sequence, telemetry in enumerate(self.adapter.stream(session.record_id, session.user_id, session.position_seconds), 1):
                await session.gate.wait()
                batch_started = time.monotonic()
                telemetry.stream_id = session.stream_id
                telemetry.sequence_number = sequence
                failures = session.failures
                if failures.disconnect_every_batches and sequence % failures.disconnect_every_batches == 0:
                    await manager.send_to_user(session.user_id, {"type": "replay_state", "data": {**session.public(), "state": "TEMPORARILY_DISCONNECTED"}})
                    await asyncio.sleep(failures.disconnect_duration_ms / 1000)
                if failures.latency_ms:
                    await asyncio.sleep(failures.latency_ms / 1000)
                session.position_seconds = telemetry.waveforms.start_offset_seconds if telemetry.waveforms else session.position_seconds
                if random.random() * 100 >= failures.packet_loss_percent:
                    payload = telemetry.model_dump(mode="json")
                    await ingest_normalized(telemetry, db)
                    if random.random() * 100 < failures.duplicate_percent:
                        await manager.send_to_user(session.user_id, {"type": "normalized_telemetry", "data": payload})
                if sequence % 5 == 0:
                    await self._sync_twin(session, db, telemetry.model_dump(mode="json"))
                    await self._broadcast_state(session)
                interval = (self.adapter.batch_samples / self.adapter.waveform_sample_rate_hz) / session.speed
                await asyncio.sleep(max(0, interval - (time.monotonic() - batch_started)))
            self._event(session, ReplayState.COMPLETED)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error('dataset_replay_failed', extra={'error_type': type(exc).__name__})
            self._event(session, ReplayState.ERROR, str(exc))
        finally:
            await self._sync_twin(session, db)
            await self._broadcast_state(session)

    async def _sync_twin(self, session: ReplaySession, db, telemetry: dict | None = None):
        document = session.public()
        document["user_id"] = session.user_id
        if telemetry:
            document["latest_telemetry"] = telemetry
            document["signal_quality"] = telemetry["signal_quality"]
            document["waveform_state"] = {key: len(value) for key, value in telemetry.get("waveforms", {}).items() if isinstance(value, list)}
        await db["digital_twins"].update_one({"twin_id": document["twin_id"], "user_id": session.user_id}, {"$set": document}, upsert=True)

    async def _broadcast_state(self, session: ReplaySession):
        await manager.send_to_user(session.user_id, {"type": "replay_state", "data": session.public()})


replay_engine = DatasetReplayEngine()
