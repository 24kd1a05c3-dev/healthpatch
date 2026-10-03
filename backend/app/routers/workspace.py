from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
import csv
import io

from app.database import get_collection
from app.security import get_current_user
from app.authz import ensure_patient_access
from app.services.session_service import audit

router = APIRouter(prefix='/api/v1', tags=['patient workspace'])


@router.get('/workspace')
async def workspace(user_id: str | None = None, current_user=Depends(get_current_user)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    db = get_collection('patient_twins').database
    twin = await db['patient_twins'].find_one({'user_id': uid}, {'_id': 0}, sort=[('timestamp', -1)])
    history = []
    if twin:
        history = await db['telemetry_seconds'].find({'user_id': uid, 'stream_id': twin['stream_id']}, {'_id': 0}).sort('second', -1).limit(300).to_list(length=300)
        history.reverse()
        stamp = twin['timestamp'].replace(tzinfo=timezone.utc) if twin['timestamp'].tzinfo is None else twin['timestamp']
        twin['stale'] = datetime.now(timezone.utc) - stamp > timedelta(seconds=15)
    alerts = await db['alerts'].find({'user_id': uid}).sort('created_at', -1).limit(50).to_list(length=50)
    for item in alerts:
        item['id'] = str(item.pop('_id'))
    await audit(db, current_user.id, 'workspace_read', uid)
    return {'twin': twin, 'history': history, 'alerts': alerts}


@router.get('/reports/telemetry.csv')
async def report(user_id: str | None = None, current_user=Depends(get_current_user)):
    uid = user_id or current_user.id
    ensure_patient_access(current_user, uid)
    db = get_collection('telemetry_seconds').database
    # Bounded export of the latest stream keeps replay subjects separate.
    latest = await db['telemetry_seconds'].find_one({'user_id': uid}, sort=[('timestamp', -1)])
    rows = await db['telemetry_seconds'].find({'user_id': uid, 'stream_id': latest['stream_id']}).sort('second', 1).limit(10000).to_list(length=10000) if latest else []
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['timestamp', 'source', 'record', 'offset_seconds', 'heart_rate_bpm', 'pulse_rate_bpm', 'spo2_percent', 'respiratory_rate', 'temperature_c'])
    for row in rows:
        v = row['vitals']
        writer.writerow([row['timestamp'].isoformat(), row['source_type'], row.get('record_id'), row['second'], v.get('heart_rate'), v.get('pulse_rate'), v.get('spo2'), v.get('respiratory_rate'), v.get('temperature')])
    await audit(db, current_user.id, 'report_export', uid)
    return Response(buffer.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="healthpatch-telemetry.csv"'})
