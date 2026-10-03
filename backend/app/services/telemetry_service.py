"""Persist normalized streams and derive explainable research statistics."""
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev
import asyncio
import logging
from uuid import uuid4
from pymongo import ReturnDocument
from app.models.telemetry import NormalizedTelemetry

from pymongo.errors import DuplicateKeyError
from app.websocket_manager import manager
from app.services.notify_service import notify_watchers
from app.services.session_service import audit

METRICS = ('heart_rate', 'pulse_rate', 'spo2', 'respiratory_rate', 'temperature')
logger = logging.getLogger(__name__)


def summarize(rows: list[dict]) -> dict:
    features = {}
    for metric in METRICS:
        values = [row['vitals'][metric] for row in rows if row.get('vitals', {}).get(metric) is not None]
        if not values:
            continue
        baseline = values[:-30] if len(values) >= 60 else []
        reference = mean(baseline) if baseline else None
        spread = pstdev(baseline) if baseline else None
        recent = values[-30:]
        z = (mean(recent) - reference) / spread if spread and spread > 0.01 else None
        features[metric] = {'current': values[-1], 'mean': mean(values), 'min': min(values), 'max': max(values),
            'samples': len(values), 'baseline': reference, 'standard_deviation': spread,
            'recent_mean': mean(recent), 'z_score': z,
            'trend': 'rising' if len(values) > 1 and values[-1] > values[0] else 'falling' if len(values) > 1 and values[-1] < values[0] else 'stable'}
    # A repeated statistical deviation is a review signal, never a diagnosis.
    recent_rows = rows[-30:]
    continuous = len(recent_rows) == 30 and all(b.get('second', i + 1) - a.get('second', i) == 1 for i, (a, b) in enumerate(zip(recent_rows, recent_rows[1:])))
    contributors = [f'{key}: last 30 samples average differs by {value["z_score"]:.1f} standard deviations'
                    for key, value in features.items() if value['z_score'] is not None and abs(value['z_score']) >= 3
                    and all(row.get('vitals', {}).get(key) is not None for row in recent_rows)]
    if not continuous:
        contributors = []
    if any(row.get('signal_quality') is not None and row['signal_quality'] < 0.7 for row in recent_rows):
        contributors = []
    return {'features': features, 'contributors': contributors, 'baseline_ready': any(v['baseline'] is not None for v in features.values()),
            'method': 'Within-stream 300-sample window; baseline excludes last 30 samples; review threshold |z| >= 3.',
            'classification': 'statistical observation', 'sample_count': len(rows)}


async def ingest_normalized(telemetry, db):
    doc = telemetry.model_dump()
    doc['derivation'] = {'state': 'pending', 'attempts': 0, 'available_at': datetime.now(timezone.utc)}
    try:
        await db['normalized_telemetry'].insert_one(doc)
    except DuplicateKeyError:
        return False
    await process_pending(db, {'user_id': telemetry.user_id, 'stream_id': telemetry.stream_id,
                               'sequence_number': telemetry.sequence_number})
    return True


async def process_pending(db, identity=None):
    now = datetime.now(timezone.utc)
    owner = str(uuid4())
    query = {'derivation.state': {'$in': ['pending', 'processing']}, 'derivation.available_at': {'$lte': now}}
    if identity:
        query.update(identity)
    doc = await db['normalized_telemetry'].find_one_and_update(query, {'$set': {
        'derivation.state': 'processing', 'derivation.owner': owner,
        'derivation.available_at': now + timedelta(minutes=2)}, '$inc': {'derivation.attempts': 1}},
        sort=[('timestamp', 1)], return_document=ReturnDocument.AFTER)
    if not doc:
        return False
    claim = {'_id': doc['_id'], 'derivation.owner': owner}
    try:
        await derive_normalized(NormalizedTelemetry(**doc), db)
        await db['normalized_telemetry'].update_one(claim, {'$set': {
            'derivation.state': 'completed', 'derivation.completed_at': datetime.now(timezone.utc)}})
    except asyncio.CancelledError:
        raise
    except Exception as error:
        delay = min(300, 2 ** min(doc['derivation']['attempts'], 8))
        state = 'failed' if doc['derivation']['attempts'] >= 10 else 'pending'
        await db['normalized_telemetry'].update_one(claim, {'$set': {'derivation.state': state,
            'derivation.available_at': datetime.now(timezone.utc) + timedelta(seconds=delay),
            'derivation.error_type': type(error).__name__}})
        logger.error('telemetry_derivation_retry', extra={'error_type': type(error).__name__})
    return True


async def recovery_loop(db):
    while True:
        try:
            processed = await process_pending(db)
            if not processed:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error('telemetry_recovery_unavailable', extra={'error_type': type(error).__name__})
            await asyncio.sleep(5)


async def derive_normalized(telemetry, db):
    packet = telemetry.model_dump(mode='json')
    await manager.send_to_user(telemetry.user_id, {'type': 'normalized_telemetry', 'data': packet})
    offset = telemetry.provenance.original_timestamp
    second = int(offset if offset is not None else telemetry.timestamp.timestamp())
    result = await db['telemetry_seconds'].update_one(
        {'user_id': telemetry.user_id, 'stream_id': telemetry.stream_id, 'second': second},
        {'$setOnInsert': {'timestamp': telemetry.timestamp, 'source_type': telemetry.source_type.value,
                         'record_id': telemetry.provenance.record_id, 'vitals': telemetry.vitals.model_dump(),
                         'signal_quality': telemetry.signal_quality}}, upsert=True)
    if result:
        rows = await db['telemetry_seconds'].find({'user_id': telemetry.user_id, 'stream_id': telemetry.stream_id,
            'second': {'$lte': second}}).sort('second', -1).limit(300).to_list(length=300)
        rows.reverse()
        statistics = summarize(rows)
        if telemetry.signal_quality is not None and telemetry.signal_quality < 0.7:
            statistics['contributors'] = []
            statistics['quality_note'] = 'Low signal quality; review detection suppressed'
        try:
            await db['patient_twins'].update_one({'user_id': telemetry.user_id, 'stream_id': telemetry.stream_id,
                '$or': [{'last_second': {'$lt': second}},
                        {'last_second': second, 'last_sequence': {'$lte': telemetry.sequence_number}},
                        {'last_second': {'$exists': False}}]},
                {'$set': {'last_second': second, 'last_sequence': telemetry.sequence_number,
                      'source_type': telemetry.source_type.value, 'record_id': telemetry.provenance.record_id,
                      'timestamp': telemetry.timestamp, 'vitals': telemetry.vitals.model_dump(),
                      'statistics': statistics, 'signal_quality': telemetry.signal_quality}}, upsert=True)
        except DuplicateKeyError:
            pass  # A newer sample already owns the stream twin; never regress it.
        if statistics['contributors']:
            now = datetime.now(timezone.utc)
            incident_key = f'{telemetry.user_id}:{telemetry.stream_id}:deviation:{second // 300}'
            alert = {'user_id': telemetry.user_id, 'incident_key': incident_key, 'source_type': telemetry.source_type.value,
                     'alert_type': 'StatisticalDeviation', 'level': 'warning', 'title': 'Sustained statistical deviation',
                     'message': '; '.join(statistics['contributors']), 'reasons': statistics['contributors'],
                     'device_id': telemetry.device_id, 'measurement_id': telemetry.stream_id,
                     'acknowledged': False, 'created_at': now}
            if telemetry.source_type.value == 'LIVE_DEVICE':
                alert['notifications'] = {'sms': {'state': 'pending'}, 'voice': {'state': 'pending'}}
            created = await db['alerts'].update_one({'incident_key': incident_key}, {'$setOnInsert': alert}, upsert=True)
            if created.upserted_id:
                alert['id'] = str(created.upserted_id)
                alert['created_at'] = now.isoformat()
                await audit(db, 'analytics', 'alert_created', alert['id'])
                await manager.send_to_user(telemetry.user_id, {'type': 'alert', 'data': alert})
                await notify_watchers(telemetry.user_id, {'type': 'alert', 'data': alert}, db, manager)
    return True
