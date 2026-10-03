import asyncio
from datetime import datetime, timezone
from urllib.parse import parse_qsl
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from starlette.datastructures import FormData
from twilio.request_validator import RequestValidator
from twilio.base.exceptions import TwilioRestException

from app.config import settings
from app.database import get_collection
from app.security import get_current_user
from app.rate_limit import check_limit
from app.services.session_service import audit
from app.services.telephone_service import provider, callback_url

router = APIRouter(prefix='/notifications', tags=['notifications'])


def configured():
    if not settings.NOTIFICATIONS_ENABLED:
        raise HTTPException(503, 'SMS and voice delivery are not enabled on this deployment')


class VerificationStart(BaseModel):
    channel: Literal['sms', 'call'] = 'sms'


class VerificationCheck(BaseModel):
    code: str = Field(pattern=r'^\d{4,10}$')


class Preferences(BaseModel):
    sms: bool = False
    voice: bool = False


@router.get('/preferences')
async def preferences(user=Depends(get_current_user), db=Depends(lambda: get_collection('users').database)):
    doc = await db['users'].find_one({'_id': ObjectId(user.id)})
    deliveries = await db['alerts'].find({'user_id': user.id, 'notifications': {'$exists': True}},
        {'notifications': 1, 'created_at': 1}).sort('created_at', -1).limit(20).to_list(20)
    return {'enabled': settings.NOTIFICATIONS_ENABLED, 'phone': user.phone,
            'verified': bool(user.phone and doc.get('verified_notification_phone') == user.phone),
            'sms': doc.get('notification_preferences', {}).get('sms', False),
            'voice': doc.get('notification_preferences', {}).get('voice', False),
            'deliveries': [{'id': str(row['_id']), 'created_at': row['created_at'],
                            'notifications': row['notifications']} for row in deliveries]}


@router.post('/verification/start')
async def start(body: VerificationStart, user=Depends(get_current_user)):
    configured()
    if not user.phone:
        raise HTTPException(400, 'Save a primary phone number in your profile first')
    await check_limit(f'verification-start:{user.id}', 3, 600)
    try:
        result = await asyncio.to_thread(lambda: provider().verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
                                        .verifications.create(to=user.phone, channel=body.channel))
    except Exception:
        raise HTTPException(503, 'Verification provider unavailable') from None
    return {'status': result.status}


@router.post('/verification/check')
async def check(body: VerificationCheck, user=Depends(get_current_user), db=Depends(lambda: get_collection('users').database)):
    configured()
    if not user.phone:
        raise HTTPException(400, 'A saved primary phone number is required')
    await check_limit(f'verification-check:{user.id}', 5, 600)
    try:
        result = await asyncio.to_thread(lambda: provider().verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)
                                        .verification_checks.create(to=user.phone, code=body.code))
    except TwilioRestException as error:
        if error.status in (400, 404):
            raise HTTPException(400, 'Verification code is invalid or expired') from None
        raise HTTPException(503, 'Verification provider unavailable') from None
    except Exception:
        raise HTTPException(503, 'Verification provider unavailable') from None
    if result.status != 'approved':
        raise HTTPException(400, 'Verification code is invalid or expired')
    result = await db['users'].update_one({'_id': ObjectId(user.id), 'phone': user.phone},
        {'$set': {'verified_notification_phone': user.phone, 'notification_phone_verified_at': datetime.now(timezone.utc)}})
    if not result.matched_count:
        raise HTTPException(409, 'Phone number changed during verification; verify the new number')
    await audit(db, user.id, 'notification_phone_verified', user.id)
    return {'verified': True}


@router.put('/preferences')
async def save(body: Preferences, user=Depends(get_current_user), db=Depends(lambda: get_collection('users').database)):
    doc = await db['users'].find_one({'_id': ObjectId(user.id)})
    if body.sms or body.voice:
        configured()
        if not user.phone or doc.get('verified_notification_phone') != user.phone:
            raise HTTPException(400, 'Verify your primary phone number before enabling delivery')
    await db['users'].update_one({'_id': ObjectId(user.id)}, {'$set': {
        'notification_preferences': body.model_dump(), 'notification_consent_at': datetime.now(timezone.utc)}})
    await audit(db, user.id, 'notification_consent_updated', user.id)
    return body


@router.post('/callback/{alert_id}/{channel}')
async def callback(alert_id: str, channel: Literal['sms', 'voice'], request: Request,
                   db=Depends(lambda: get_collection('users').database)):
    configured()
    if not ObjectId.is_valid(alert_id) or request.headers.get('content-type', '').split(';')[0] != 'application/x-www-form-urlencoded':
        raise HTTPException(400, 'Invalid callback')
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 16384:
            raise HTTPException(413, 'Callback too large')
    form = FormData(parse_qsl(content.decode('utf-8'), keep_blank_values=True))
    if not RequestValidator(settings.TWILIO_AUTH_TOKEN).validate(callback_url(alert_id, channel), form,
                                                               request.headers.get('x-twilio-signature', '')):
        raise HTTPException(403, 'Invalid provider signature')
    sid = form.get('MessageSid' if channel == 'sms' else 'CallSid')
    status = form.get('MessageStatus' if channel == 'sms' else 'CallStatus')
    allowed = {'queued', 'sending', 'sent', 'delivered', 'undelivered', 'failed', 'accepted', 'scheduled', 'canceled'} if channel == 'sms' else {'queued', 'initiated', 'ringing', 'in-progress', 'completed', 'busy', 'failed', 'no-answer', 'canceled'}
    if form.get('AccountSid') != settings.TWILIO_ACCOUNT_SID or not sid or status not in allowed:
        raise HTTPException(400, 'Invalid callback fields')
    field = f'notifications.{channel}'
    terminal = ['delivered', 'undelivered', 'failed', 'canceled'] if channel == 'sms' else ['completed', 'busy', 'failed', 'no-answer', 'canceled']
    await db['alerts'].update_one({'_id': ObjectId(alert_id), f'{field}.state': {'$exists': True},
        f'{field}.provider_status': {'$nin': terminal},
        '$or': [{f'{field}.provider_sid': sid}, {f'{field}.provider_sid': {'$exists': False}}]},
        {'$set': {f'{field}.provider_sid': sid, f'{field}.provider_status': status,
                  f'{field}.callback_at': datetime.now(timezone.utc)}})
    return Response(status_code=204)
