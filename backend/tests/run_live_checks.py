"""Run against the local API; creates and cleans up its own isolated QA account."""
import asyncio
import math
from uuid import uuid4
from datetime import datetime, timezone
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.config import settings
from app.models.telemetry import NormalizedTelemetry, Provenance, Vitals, SourceType
from app.services.telemetry_service import ingest_normalized


async def main():
    marker = uuid4().hex
    user_id = None
    db_client = AsyncIOMotorClient(settings.MONGODB_URI, tz_aware=True)
    db = db_client[settings.DATABASE_NAME]
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=20) as client:
        try:
            payload = {'email': f'qa-{marker}@example.com', 'password': f'QA-{marker}', 'full_name': 'Registration QA',
                       'phone': '9876543210', 'additional_phones': ['+44 20 7946 0018'], 'address': 'QA address',
                       'date_of_birth': '2000-01-01', 'medical_conditions': ['Asthma'], 'medications': ['QA entry'],
                       'emergency_contact_name': 'QA contact', 'emergency_contact_phone': '01123456789'}
            response = await client.post('/auth/register', json=payload)
            response.raise_for_status()
            body = response.json()
            user_id = body['user']['id']
            assert body['user']['phone'] == '+919876543210'
            assert body['user']['address'] == 'QA address'
            assert 'httponly' in response.headers['set-cookie'].lower()
            old_access = body['access_token']
            old_refresh = client.cookies.get('hp_refresh')
            refreshed = await client.post('/auth/refresh')
            refreshed.raise_for_status()
            assert client.cookies.get('hp_refresh') != old_refresh
            headers = {'Authorization': f'Bearer {refreshed.json()["access_token"]}'}
            assert (await client.get('/users/me', headers=headers)).json()['medications'] == ['QA entry']
            denied = await client.get('/api/v1/workspace', params={'user_id': str(ObjectId())}, headers=headers)
            assert denied.status_code == 403
            print('PASS registration persistence, phone normalization, cookie rotation, patient isolation')
            datasets = (await client.get('/replay/datasets', headers=headers)).json()
            assert datasets[0]['records'][0]['record_id'] == 'bidmc_01'
            start = await client.post('/replay/start', headers=headers, json={'record_id': 'bidmc_01', 'speed': 5})
            start.raise_for_status()
            await asyncio.sleep(1)
            paused = await client.post('/replay/pause', headers=headers)
            assert paused.json()['state'] == 'PAUSED'
            workspace = (await client.get('/api/v1/workspace', headers=headers)).json()
            assert workspace['twin']['source_type'] == 'DATASET_REPLAY'
            assert datetime.fromisoformat(workspace['twin']['timestamp'].replace('Z', '+00:00')).tzinfo is not None
            assert workspace['twin']['vitals']['temperature'] is None
            assert workspace['history']
            await client.post('/replay/stop', headers=headers)
            print('PASS actual dataset replay, persistence, pause, source metadata')
            stream = uuid4().hex
            for i in range(90):
                packet = NormalizedTelemetry(user_id=user_id, device_id='QA-SIMULATED', stream_id=stream,
                    sequence_number=i, source_type=SourceType.SYNTHETIC_SIMULATOR,
                    vitals=Vitals(heart_rate=72 + math.sin(i) if i < 60 else 110), signal_quality=0.95,
                    provenance=Provenance(source_type=SourceType.SYNTHETIC_SIMULATOR, original_timestamp=i,
                                          record_id='QA-SCENARIO', processing_version='test'))
                assert await ingest_normalized(packet, db)
            assert not await ingest_normalized(packet, db)
            workspace = (await client.get('/api/v1/workspace', headers=headers)).json()
            assert workspace['twin']['statistics']['contributors']
            assert len(workspace['alerts']) == 1
            alert_id = workspace['alerts'][0]['id']
            ack = await client.post(f'/alerts/{alert_id}/acknowledge', headers=headers)
            assert ack.json()['acknowledged']
            assert await db['audit_events'].find_one({'actor': user_id, 'action': 'alert_acknowledged'})
            report = await client.get('/api/v1/reports/telemetry.csv', headers=headers)
            assert report.status_code == 200 and 'SYNTHETIC_SIMULATOR' in report.text
            print('PASS twin statistics, deduplication, sustained alert, acknowledgment, audit, CSV export')
            from app.services import telemetry_service
            recovery_packet = NormalizedTelemetry(user_id=user_id, device_id='QA-RECOVERY', stream_id=f'recovery-{marker}',
                source_type=SourceType.SYNTHETIC_SIMULATOR, vitals=Vitals(heart_rate=72),
                provenance=Provenance(source_type=SourceType.SYNTHETIC_SIMULATOR, processing_version='test'))
            original_derivation = telemetry_service.derive_normalized
            async def interrupted_derivation(*args):
                raise RuntimeError('Injected QA failure')
            telemetry_service.derive_normalized = interrupted_derivation
            try:
                assert await ingest_normalized(recovery_packet, db)
            finally:
                telemetry_service.derive_normalized = original_derivation
            identity = {'user_id': user_id, 'stream_id': recovery_packet.stream_id}
            pending = await db['normalized_telemetry'].find_one(identity)
            assert pending['derivation']['state'] == 'pending'
            await db['normalized_telemetry'].update_one(identity, {'$set': {'derivation.available_at': datetime.now(timezone.utc)}})
            for _ in range(30):
                recovered = await db['normalized_telemetry'].find_one(identity)
                if recovered['derivation']['state'] == 'completed':
                    break
                await asyncio.sleep(0.2)
            assert recovered['derivation']['state'] == 'completed'
            assert await db['patient_twins'].find_one(identity)
            prefs = await client.get('/notifications/preferences', headers=headers)
            assert prefs.status_code == 200 and prefs.json()['sms'] is False and prefs.json()['voice'] is False
            assert (await client.post('/notifications/verification/start', headers=headers, json={'channel': 'sms'})).status_code == 503
            assert (await client.get('/ops/status', headers=headers)).status_code == 403
            print('PASS persisted derivation recovers from failure; notifications disabled; operations admin-only')
            sim = await client.post('/api/v1/simulation', headers=headers, json={'action': 'start'})
            assert sim.status_code == 200
            await asyncio.sleep(0.3)
            assert (await client.post('/api/v1/simulation', headers=headers, json={'action': 'pause'})).json()['state'] == 'PAUSED'
            await client.post('/api/v1/simulation', headers=headers, json={'action': 'stop'})
            assert (await client.post('/auth/logout', headers=headers)).status_code == 200
            assert (await client.get('/users/me', headers={'Authorization': f'Bearer {old_access}'})).status_code == 401
            assert (await client.post('/auth/refresh')).status_code == 401
            print('PASS simulation controls, logout revocation, expired refresh rejection')
        finally:
            if user_id:
                for collection in ['sessions', 'normalized_telemetry', 'telemetry_seconds', 'digital_twins', 'patient_twins', 'alerts']:
                    await db[collection].delete_many({'user_id': user_id})
                await db['audit_events'].delete_many({'actor': user_id})
                await db['users'].delete_one({'_id': ObjectId(user_id)})
            db_client.close()


if __name__ == '__main__':
    asyncio.run(main())
