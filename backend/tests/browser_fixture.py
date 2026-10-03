"""Disposable local browser QA fixture, never a production seed."""
import argparse
import asyncio
import json
from uuid import uuid4

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cleanup', help='Exact fixture user ID to remove')
    args = parser.parse_args()
    if settings.ENVIRONMENT.lower() != 'development':
        raise RuntimeError('Browser fixtures are development-only')
    if args.cleanup:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        try:
            db = client[settings.DATABASE_NAME]
            user = await db.users.find_one({'_id': ObjectId(args.cleanup), 'full_name': 'Disposable Browser QA'})
            if not user or not user['email'].startswith('browser-qa-'):
                raise RuntimeError('Not a browser QA fixture; refusing cleanup')
            for collection in ['sessions', 'normalized_telemetry', 'telemetry_seconds', 'patient_twins', 'digital_twins', 'alerts', 'emergency_events']:
                await db[collection].delete_many({'user_id': args.cleanup})
            await db.audit_events.delete_many({'actor': args.cleanup})
            await db.users.delete_one({'_id': user['_id']})
            print('Removed only the specified browser QA fixture')
        finally:
            client.close()
    else:
        credentials = {'email': f'browser-qa-{uuid4().hex}@example.com', 'password': uuid4().hex}
        async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as client:
            response = await client.post('/auth/register', json={**credentials, 'full_name': 'Disposable Browser QA'})
            response.raise_for_status()
            print(json.dumps({**credentials, 'user_id': response.json()['user']['id']}))


if __name__ == '__main__':
    asyncio.run(main())
