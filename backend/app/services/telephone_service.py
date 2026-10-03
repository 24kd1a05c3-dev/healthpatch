"""Opt-in, verified-recipient notifications. Recorded/synthetic data never dispatches."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.base.exceptions import TwilioRestException

from app.config import settings
from app.services.session_service import audit

logger = logging.getLogger(__name__)
MESSAGE = 'HealthPatch has a monitoring observation for review. Sign in to your account. This is not an emergency dispatch service.'


def provider():
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN,
                  http_client=TwilioHttpClient(timeout=10, max_retries=0))


def callback_url(alert_id, channel):
    return f'{settings.NOTIFICATION_PUBLIC_BASE.rstrip("/")}/notifications/callback/{alert_id}/{channel}'


def send_notification(channel, phone, alert_id):
    client = provider()
    callback = callback_url(alert_id, channel)
    if channel == 'sms':
        return client.messages.create(to=phone, from_=settings.TWILIO_FROM_NUMBER,
                                      body=MESSAGE, status_callback=callback).sid
    return client.calls.create(to=phone, from_=settings.TWILIO_FROM_NUMBER,
        twiml=f'<Response><Say>{MESSAGE}</Say></Response>', status_callback=callback,
        status_callback_event=['initiated', 'ringing', 'answered', 'completed'], timeout=20).sid


def eligible_recipient(user, channel):
    phone = user.get('phone')
    return bool(phone and phone == user.get('verified_notification_phone')
                and user.get('notification_preferences', {}).get(channel) is True)


async def dispatch_one(db, channel):
    now = datetime.now(timezone.utc)
    field = f'notifications.{channel}'
    await db['alerts'].update_many({f'{field}.state': 'pending', 'created_at': {'$lt': now - timedelta(minutes=15)}},
                                 {'$set': {f'{field}.state': 'expired'}})
    # A send interrupted after provider acceptance is ambiguous, not safe to repeat.
    await db['alerts'].update_many({f'{field}.state': 'sending', f'{field}.lease_until': {'$lt': now}},
                                 {'$set': {f'{field}.state': 'unknown'}})
    alert = await db['alerts'].find_one_and_update({'source_type': 'LIVE_DEVICE', 'acknowledged': False,
        'created_at': {'$gte': now - timedelta(minutes=15)}, f'{field}.state': 'pending'},
        {'$set': {f'{field}.state': 'sending', f'{field}.lease_until': now + timedelta(minutes=2)}},
        sort=[('created_at', 1)], return_document=ReturnDocument.AFTER)
    if not alert:
        return False
    update = {f'{field}.state': 'skipped'}
    user = await db['users'].find_one({'_id': ObjectId(alert['user_id'])}) if ObjectId.is_valid(alert['user_id']) else None
    if user and eligible_recipient(user, channel):
        key = f'{alert["user_id"]}:{channel}:{int(now.timestamp()) // 3600}'
        try:
            await db['notification_limits'].insert_one({'_id': key, 'expires_at': now + timedelta(days=1)})
        except DuplicateKeyError:
            update[f'{field}.state'] = 'rate_limited'
        else:
            try:
                sid = await asyncio.to_thread(send_notification, channel, user['phone'], str(alert['_id']))
                update = {f'{field}.state': 'accepted', f'{field}.provider_sid': sid}
            except TwilioRestException as error:
                update = {f'{field}.state': 'failed' if error.status and error.status < 500 else 'unknown',
                          f'{field}.error_code': str(error.code)}
            except Exception:
                update = {f'{field}.state': 'unknown'}
    # Preserve an earlier signed callback if it arrives before create() returns.
    await db['alerts'].update_one({'_id': alert['_id']}, {'$set': update})
    await audit(db, 'notification_worker', 'notification_attempt', str(alert['_id']), update[f'{field}.state'])
    return True


async def notification_loop(db):
    while True:
        try:
            if settings.NOTIFICATIONS_ENABLED:
                await dispatch_one(db, 'sms')
                await dispatch_one(db, 'voice')
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error('notification_worker_unavailable', extra={'error_type': type(error).__name__})
        await asyncio.sleep(2)
