import asyncio
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.database import get_collection
from app.security import get_current_user
from app.services import simulation_service as simulation
from app.services.session_service import audit
from app.services.replay_service import replay_engine

router = APIRouter(prefix='/api/v1/simulation', tags=['research simulation'])


class Control(BaseModel):
    action: Literal['start', 'pause', 'resume', 'stop', 'scenario', 'disconnect', 'reconnect', 'quality', 'speed']
    scenario: str = 'RESTING'
    speed: Literal[1, 2, 5] = 1
    quality: float = Field(default=0.95, ge=0, le=1)


@router.get('')
async def status(user=Depends(get_current_user)):
    session = simulation.sessions.get(user.id)
    return {'scenarios': list(simulation.TARGETS), **(session.public() if session else {'state': 'STOPPED', 'source_type': 'SYNTHETIC_SIMULATOR'})}


@router.post('')
async def control(request: Control, user=Depends(get_current_user)):
    if request.scenario not in simulation.TARGETS:
        raise HTTPException(422, 'Unknown scenario')
    db = get_collection('patient_twins').database
    session = simulation.sessions.get(user.id)
    if request.action == 'start':
        if replay_engine.status(user.id)['state'] in ('PLAYING', 'PAUSED', 'CONNECTED'):
            raise HTTPException(409, 'Stop the dataset replay before starting a simulated stream')
        if session and session.task and not session.task.done():
            raise HTTPException(409, 'A simulation is already active')
        session = simulation.Simulation(user.id, request.scenario, request.speed)
        simulation.sessions[user.id] = session
        session.task = asyncio.create_task(simulation.run(session, db))
    elif not session or not session.task or session.task.done():
        raise HTTPException(409, 'No active simulation')
    elif request.action == 'scenario':
        session.scenario = request.scenario
    elif request.action == 'quality':
        session.signal_quality = request.quality
    elif request.action == 'speed':
        session.speed = request.speed
    elif request.action == 'stop':
        session.task.cancel()
        try:
            await session.task
        except asyncio.CancelledError:
            pass
    else:
        session.state = {'pause': 'PAUSED', 'resume': 'PLAYING', 'disconnect': 'DISCONNECTED', 'reconnect': 'PLAYING'}[request.action]
    await audit(db, user.id, f'simulation_{request.action}', session.stream_id)
    return session.public()
