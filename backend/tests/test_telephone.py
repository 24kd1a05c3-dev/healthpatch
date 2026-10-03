import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from urllib.parse import urlencode

import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request
from twilio.request_validator import RequestValidator

from app.config import settings
from app.routers import notifications
from app.services import telephone_service as telephone


@pytest.mark.parametrize('changes,eligible', [({}, True), ({'verified_notification_phone': None}, False),
    ({'phone': '+442079460018'}, False), ({'notification_preferences': {'sms': False}}, False)])
def test_only_verified_consented_number_is_eligible(changes, eligible):
    user = {'phone': '+919876543210', 'verified_notification_phone': '+919876543210',
            'notification_preferences': {'sms': True}}
    assert telephone.eligible_recipient({**user, **changes}, 'sms') == eligible


def test_unconfigured_provider_returns_unavailable_without_sending(monkeypatch):
    monkeypatch.setattr(settings, 'NOTIFICATIONS_ENABLED', False)
    provider = Mock()
    monkeypatch.setattr(notifications, 'provider', provider)
    with pytest.raises(HTTPException) as error:
        asyncio.run(notifications.start(notifications.VerificationStart(), SimpleNamespace(id='qa', phone='+919876543210')))
    assert error.value.status_code == 503
    provider.assert_not_called()


@pytest.mark.parametrize('consented,state', [(True, 'accepted'), (False, 'skipped')])
def test_dispatch_is_live_only_and_honors_consent(monkeypatch, consented, state):
    alerts, users, limits, audits = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    alerts.find_one_and_update.return_value = {'_id': ObjectId(), 'user_id': str(ObjectId())}
    users.find_one.return_value = {'phone': '+919876543210', 'verified_notification_phone': '+919876543210',
                                 'notification_preferences': {'sms': consented}}
    sender = Mock(return_value='SM-test-only')
    monkeypatch.setattr(telephone, 'send_notification', sender)
    assert asyncio.run(telephone.dispatch_one({'alerts': alerts, 'users': users, 'notification_limits': limits,
                                              'audit_events': audits}, 'sms'))
    assert alerts.find_one_and_update.call_args.args[0]['source_type'] == 'LIVE_DEVICE'
    assert alerts.update_one.call_args.args[1]['$set']['notifications.sms.state'] == state
    assert sender.call_count == int(consented)


def test_provider_timeout_is_unknown_not_retried(monkeypatch):
    alerts, users = AsyncMock(), AsyncMock()
    alerts.find_one_and_update.return_value = {'_id': ObjectId(), 'user_id': str(ObjectId())}
    users.find_one.return_value = {'phone': '+919876543210', 'verified_notification_phone': '+919876543210',
                                 'notification_preferences': {'voice': True}}
    monkeypatch.setattr(telephone, 'send_notification', Mock(side_effect=TimeoutError('private data')))
    asyncio.run(telephone.dispatch_one({'alerts': alerts, 'users': users, 'notification_limits': AsyncMock(),
                                       'audit_events': AsyncMock()}, 'voice'))
    assert alerts.update_one.call_args.args[1]['$set'] == {'notifications.voice.state': 'unknown'}


@pytest.mark.parametrize('valid', [True, False])
def test_provider_callback_requires_exact_signed_public_url(monkeypatch, valid):
    monkeypatch.setattr(settings, 'NOTIFICATIONS_ENABLED', True)
    monkeypatch.setattr(settings, 'TWILIO_ACCOUNT_SID', 'AC-test-only')
    monkeypatch.setattr(settings, 'TWILIO_AUTH_TOKEN', 'test-only-secret')
    monkeypatch.setattr(settings, 'NOTIFICATION_PUBLIC_BASE', 'https://health.example.test/api')
    alert_id = str(ObjectId())
    params = {'AccountSid': 'AC-test-only', 'MessageSid': 'SM-test-only', 'MessageStatus': 'delivered'}
    signature = RequestValidator('test-only-secret').compute_signature(telephone.callback_url(alert_id, 'sms'), params)
    async def receive():
        return {'type': 'http.request', 'body': urlencode(params).encode(), 'more_body': False}
    request = Request({'type': 'http', 'headers': [(b'content-type', b'application/x-www-form-urlencoded'),
        (b'x-twilio-signature', (signature if valid else 'invalid').encode())]}, receive)
    alerts = AsyncMock()
    if valid:
        response = asyncio.run(notifications.callback(alert_id, 'sms', request, {'alerts': alerts}))
        assert response.status_code == 204
        assert alerts.update_one.call_args.args[1]['$set']['notifications.sms.provider_status'] == 'delivered'
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(notifications.callback(alert_id, 'sms', request, {'alerts': alerts}))
        assert error.value.status_code == 403
        alerts.update_one.assert_not_called()
