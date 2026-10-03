import asyncio
import json
import logging
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pymongo.errors import ConnectionFailure

from app.main import app
from app import database, rate_limit
from app.request_context import JsonFormatter, request_id_context
from app.services import session_service, telemetry_service
from app.config import settings
from test_production_config import production_settings


@pytest.mark.parametrize('changes', [
    {'CORS_ORIGINS': ['http://health.example.test']}, {'ALLOWED_HOSTS': ['*']},
    {'RATE_LIMIT_BACKEND': 'memory'}, {'SMTP_USE_TLS': False},
    {'PASSWORD_RESET_URL_BASE': 'http://health.example.test/reset-password'},
    {'MONGODB_URI': 'mongodb://localhost:27017'},
])
def test_insecure_production_configuration_rejected(changes):
    with pytest.raises(ValueError):
        production_settings(**changes)


def test_request_ids_and_error_headers():
    client = TestClient(app)
    response = client.get('/health', headers={'x-request-id': 'trusted-test_123'})
    assert response.headers['x-request-id'] == 'trusted-test_123'
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    invalid = client.get('/health', headers={'x-request-id': 'invalid id'})
    assert invalid.headers['x-request-id'] != 'invalid id'
    assert request_id_context.get() is None
    assert client.get('/health', headers={'Host': 'evil.example.test'}).status_code == 400


def test_logs_exclude_arbitrary_payload_and_query_fields():
    record = logging.LogRecord('test', logging.INFO, '', 0, 'request completed', (), None)
    record.request_id = 'correlation'
    record.token = 'SECRET'
    record.path = '/ws/patient?token=SECRET'
    data = JsonFormatter().format(record)
    assert 'SECRET' not in data and json.loads(data)['request_id'] == 'correlation'


def test_production_origin_is_required(monkeypatch):
    from starlette.requests import Request
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    with pytest.raises(HTTPException) as error:
        session_service.check_origin(Request({'type': 'http', 'headers': []}))
    assert error.value.status_code == 403


def test_shared_limiter_rejects_over_limit_and_db_outage(monkeypatch):
    collection = AsyncMock()
    collection.find_one_and_update.return_value = {'count': 3}
    monkeypatch.setattr(settings, 'RATE_LIMIT_BACKEND', 'mongo')
    monkeypatch.setattr(database, 'get_collection', lambda name: collection)
    with pytest.raises(HTTPException) as error:
        asyncio.run(rate_limit.check_limit('test-client', 2, 60))
    assert error.value.status_code == 429 and int(error.value.headers['Retry-After']) > 0
    assert 'test-client' not in str(collection.find_one_and_update.call_args)
    collection.find_one_and_update.side_effect = ConnectionFailure('private connection string')
    with pytest.raises(HTTPException) as error:
        asyncio.run(rate_limit.check_limit('test-client', 2, 60))
    assert error.value.status_code == 503 and 'private' not in error.value.detail


@pytest.mark.parametrize('fails', [False, True])
def test_durable_derivation_completes_or_requeues(monkeypatch, fails):
    from app.models.telemetry import NormalizedTelemetry, Provenance, SourceType, Vitals
    sample = NormalizedTelemetry(user_id='test', device_id='test', vitals=Vitals(heart_rate=72),
        source_type=SourceType.SYNTHETIC_SIMULATOR,
        provenance=Provenance(source_type=SourceType.SYNTHETIC_SIMULATOR, processing_version='test'))
    collection = AsyncMock()
    collection.find_one_and_update.return_value = {
        **sample.model_dump(), '_id': 'test-record', 'derivation': {'attempts': 1}}
    derive = AsyncMock(side_effect=RuntimeError('private payload') if fails else None)
    monkeypatch.setattr(telemetry_service, 'derive_normalized', derive)
    assert asyncio.run(telemetry_service.process_pending({'normalized_telemetry': collection}))
    update = collection.update_one.call_args.args[1]['$set']
    assert update['derivation.state'] == ('pending' if fails else 'completed')
    if fails:
        assert update['derivation.error_type'] == 'RuntimeError'
        assert 'private payload' not in str(update)


def test_audit_has_correlation_id():
    collection = AsyncMock()
    token = request_id_context.set('test-correlation')
    try:
        asyncio.run(session_service.audit({'audit_events': collection}, 'actor', 'read', 'resource'))
    finally:
        request_id_context.reset(token)
    assert collection.insert_one.call_args.args[0]['request_id'] == 'test-correlation'


def test_dataset_fingerprint_is_valid_for_installed_record():
    from app.adapters.bidmc import BIDMCDatasetAdapter
    adapter = BIDMCDatasetAdapter()
    if not adapter._path('bidmc_01', 'Signals.csv').exists():
        pytest.skip('Installed PhysioNet dataset is exercised by local integration checks')
    adapter.verify_integrity('bidmc_01')


def test_dataset_fingerprint_rejects_unapproved_or_modified_files(tmp_path):
    from app.adapters.bidmc import BIDMCDatasetAdapter, DatasetFormatError
    adapter = BIDMCDatasetAdapter(root=tmp_path)
    with pytest.raises(DatasetFormatError, match='integrity check failed'):
        adapter.verify_integrity('bidmc_01')
    with pytest.raises(DatasetFormatError, match='not approved'):
        adapter.verify_integrity('bidmc_02')


def test_unsigned_session_claims_are_not_accepted():
    import jwt
    from app.security import get_current_user
    token = jwt.encode({'sub': 'qa'}, settings.JWT_SECRET_KEY, algorithm='HS256')
    with pytest.raises(HTTPException) as error:
        asyncio.run(get_current_user(token))
    assert error.value.status_code == 401


def test_production_lifecycle_starts_and_stops_workers(monkeypatch):
    from app import main
    from app.services import telephone_service
    connect, close = AsyncMock(), AsyncMock()
    monkeypatch.setattr(main, 'connect_db', connect)
    monkeypatch.setattr(main, 'close_db', close)
    async def waiting_worker(db):
        await asyncio.sleep(60)
    monkeypatch.setattr(telemetry_service, 'recovery_loop', waiting_worker)
    monkeypatch.setattr(telephone_service, 'notification_loop', waiting_worker)
    async def exercise():
        async with main.lifespan(main.app):
            assert not main.app.state.recovery_task.done()
            assert not main.app.state.notification_task.done()
        assert main.app.state.recovery_task.cancelled()
        assert main.app.state.notification_task.cancelled()
    asyncio.run(exercise())
    connect.assert_awaited_once()
    close.assert_awaited_once()
