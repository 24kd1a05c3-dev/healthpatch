from fastapi import APIRouter, Depends, HTTPException

from app.adapters.bidmc import DatasetFormatError
from app.authz import ensure_patient_access
from app.database import get_collection
from app.models.telemetry import ReplaySeekRequest, ReplaySpeedRequest, ReplayStartRequest
from app.models.user import UserInDB
from app.security import get_current_user
from app.services.replay_service import replay_engine

router = APIRouter(prefix="/replay", tags=["dataset replay"])


def database():
    return get_collection("normalized_telemetry").database


def target_user(current_user: UserInDB, requested: str | None = None) -> str:
    user_id = requested or current_user.id
    ensure_patient_access(current_user, user_id)
    return user_id


@router.get("/datasets")
async def datasets(current_user: UserInDB = Depends(get_current_user)):
    recordings = replay_engine.recordings()
    return [{"name": "BIDMC", "label": "BIDMC PPG and Respiration Dataset", "records": recordings, "installed": bool(recordings)}]


@router.get("/status")
async def status(user_id: str | None = None, current_user: UserInDB = Depends(get_current_user)):
    return replay_engine.status(target_user(current_user, user_id))


async def execute(operation):
    try:
        return await operation
    except DatasetFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/start")
async def start(request: ReplayStartRequest, current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    user_id = target_user(current_user, request.user_id)
    from app.services.simulation_service import sessions
    simulation = sessions.get(user_id)
    if simulation and simulation.task and not simulation.task.done():
        raise HTTPException(409, 'Stop the simulation before starting dataset replay')
    return await execute(replay_engine.start(user_id, request.record_id, request.speed, request.failures, db))


@router.post("/pause")
async def pause(current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.pause(current_user.id, db))


@router.post("/resume")
async def resume(current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.resume(current_user.id, db))


@router.post("/stop")
async def stop(current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.stop(current_user.id, db))


@router.post("/restart")
async def restart(current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.restart(current_user.id, db))


@router.post("/seek")
async def seek(request: ReplaySeekRequest, current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.seek(current_user.id, request.position_seconds, db))


@router.post("/speed")
async def speed(request: ReplaySpeedRequest, current_user: UserInDB = Depends(get_current_user), db=Depends(database)):
    return await execute(replay_engine.set_speed(current_user.id, request.speed, db))
