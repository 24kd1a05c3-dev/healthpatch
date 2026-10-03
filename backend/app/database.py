from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
import logging
import pymongo

logger = logging.getLogger(__name__)

class DatabaseManager:
    client: AsyncIOMotorClient = None
    db = None

db_manager = DatabaseManager()

async def connect_db():
    logger.info("Connecting to MongoDB...")
    db_manager.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        waitQueueTimeoutMS=5000,
        maxPoolSize=100,
        uuidRepresentation="standard",
        tz_aware=True,
    )
    db_manager.db = db_manager.client[settings.DATABASE_NAME]
    await db_manager.client.admin.command("ping")
    await ensure_indexes()
    logger.info("Connected to MongoDB.")

async def close_db():
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
    logger.info("Closed MongoDB connection.")

def get_collection(name: str):
    return db_manager.db[name]

async def ensure_indexes():
    db = db_manager.db
    await db["users"].create_index("email", unique=True)
    await db['rate_limits'].create_index('expires_at', expireAfterSeconds=0)
    await db['notification_limits'].create_index('expires_at', expireAfterSeconds=0)
    await db['alerts'].create_index([('notifications.sms.state', 1), ('created_at', 1)])
    await db['alerts'].create_index([('notifications.voice.state', 1), ('created_at', 1)])
    await db['sessions'].create_index('sid', unique=True)
    await db['sessions'].create_index('refresh_hash', unique=True)
    await db['sessions'].create_index('used_hashes')
    await db['sessions'].create_index('expires_at', expireAfterSeconds=0)
    await db['audit_events'].create_index([('actor', 1), ('timestamp', -1)])
    await db["users"].create_index([("role", pymongo.ASCENDING), ("assigned_patients", pymongo.ASCENDING)])
    await db["devices"].create_index("device_id", unique=True)
    await db["devices"].create_index("user_id")
    await db["health_measurements"].create_index([("user_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
    await db["health_measurements"].create_index([("device_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
    await db["alerts"].create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
    await db["alerts"].create_index([("level", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
    await db["emergency_events"].create_index([("user_id", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)])
    await db["password_resets"].create_index("token_hash", unique=True)
    await db["password_resets"].create_index("expires_at", expireAfterSeconds=0)
    await db["normalized_telemetry"].create_index([("user_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
    await db['normalized_telemetry'].create_index('timestamp', expireAfterSeconds=7 * 86400)
    await db['normalized_telemetry'].create_index([('derivation.state', 1), ('derivation.available_at', 1), ('timestamp', 1)])
    await db['normalized_telemetry'].create_index([('user_id', 1), ('stream_id', 1), ('sequence_number', 1)], unique=True, partialFilterExpression={'stream_id': {'$exists': True}})
    await db['telemetry_seconds'].create_index([('user_id', 1), ('stream_id', 1), ('second', 1)], unique=True)
    await db['telemetry_seconds'].create_index([('user_id', 1), ('timestamp', -1)])
    await db['patient_twins'].create_index([('user_id', 1), ('stream_id', 1)], unique=True)
    await db['alerts'].create_index('incident_key', unique=True, partialFilterExpression={'incident_key': {'$exists': True}})
    await db["normalized_telemetry"].create_index([("provenance.dataset_name", pymongo.ASCENDING), ("provenance.record_id", pymongo.ASCENDING)])
    await db["digital_twins"].create_index([("twin_id", pymongo.ASCENDING), ("user_id", pymongo.ASCENDING)], unique=True)
