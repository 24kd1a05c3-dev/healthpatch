from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_collection
from app.security import require_role
from app.services.session_service import audit

router = APIRouter(prefix='/ops', tags=['operations'])


@router.get('/status')
async def status(user=Depends(require_role('admin')), db=Depends(lambda: get_collection('users').database)):
    counts = {}
    for state in ('pending', 'processing', 'failed'):
        counts[state] = await db['normalized_telemetry'].count_documents({'derivation.state': state})
    unknown = await db['alerts'].count_documents({'$or': [
        {'notifications.sms.state': 'unknown'}, {'notifications.voice.state': 'unknown'}]})
    return {'telemetry_derivation': counts, 'ambiguous_notification_alerts': unknown}


@router.post('/telemetry/{record_id}/retry')
async def retry(record_id: str, user=Depends(require_role('admin')), db=Depends(lambda: get_collection('users').database)):
    if not ObjectId.is_valid(record_id):
        raise HTTPException(404, 'Failed record not found')
    result = await db['normalized_telemetry'].update_one({'_id': ObjectId(record_id), 'derivation.state': 'failed'},
        {'$set': {'derivation.state': 'pending', 'derivation.attempts': 0,
                  'derivation.available_at': datetime.now(timezone.utc)}})
    if not result.matched_count:
        raise HTTPException(404, 'Failed record not found')
    await audit(db, user.id, 'telemetry_retry_requested', record_id)
    return {'status': 'queued'}
