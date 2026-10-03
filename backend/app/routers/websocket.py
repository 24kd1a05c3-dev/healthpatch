from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.websocket_manager import manager
import jwt
from jwt import InvalidTokenError
from app.config import settings
from app.security import get_current_user
from fastapi import HTTPException
import asyncio
import time

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM],
                             options={'require': ['exp', 'sub', 'sid']})
        await get_current_user(token)
    except (InvalidTokenError, HTTPException):
        await websocket.close(code=1008)
        return
    if payload.get("sub") != user_id:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, user_id)
    next_validation = time.monotonic() + 15
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=max(0.01, next_validation - time.monotonic()))
            except asyncio.TimeoutError:
                data = None
            if time.monotonic() >= next_validation:
                try:
                    await get_current_user(token)
                except HTTPException:
                    await websocket.close(code=1008)
                    break
                next_validation = time.monotonic() + 15
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, user_id)
