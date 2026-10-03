from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from fastapi import HTTPException, Request, Response
from app.config import settings
from app.security import create_access_token
from app.models.user import TokenResponse, UserResponse
from app.request_context import request_id_context

COOKIE = 'hp_refresh'


def fingerprint(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def check_origin(request: Request):
    origin = request.headers.get('origin')
    if not origin and settings.ENVIRONMENT.lower() == 'production':
        raise HTTPException(403, 'Origin header is required for browser session operations')
    if origin and origin not in settings.CORS_ORIGINS:
        raise HTTPException(403, 'Origin is not allowed')


def set_cookie(response: Response, token: str):
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.ENVIRONMENT.lower() == 'production',
                        samesite='strict', max_age=7 * 86400, path='/')


async def issue_session(user, db, response: Response):
    now = datetime.now(timezone.utc)
    token = secrets.token_urlsafe(48)
    sid = secrets.token_urlsafe(24)
    await db['sessions'].insert_one({'sid': sid, 'user_id': user.id, 'refresh_hash': fingerprint(token),
        'created_at': now, 'expires_at': now + timedelta(days=7), 'revoked': False})
    set_cookie(response, token)
    return TokenResponse(access_token=create_access_token({'sub': user.id, 'sid': sid}),
                         token_type='bearer', user=UserResponse(**user.model_dump()))


async def audit(db, actor: str, action: str, resource: str, result='success'):
    await db['audit_events'].insert_one({'actor': actor, 'action': action, 'resource': resource,
                                       'result': result, 'request_id': request_id_context.get(),
                                       'timestamp': datetime.now(timezone.utc)})
