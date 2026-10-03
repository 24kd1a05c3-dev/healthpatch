from app.models.user import UserCreate, UserResponse, UserInDB, TokenResponse
from app.security import hash_password, verify_password, create_access_token
from bson import ObjectId
from datetime import datetime, timezone
import asyncio
from starlette.concurrency import run_in_threadpool

password_slots = asyncio.Semaphore(4)
dummy_hash = hash_password('dummy-verification-value-never-used-as-an-account-password')


async def password_work(function, *args):
    async with password_slots:
        return await run_in_threadpool(function, *args)

async def get_user_by_email(email: str, db) -> UserInDB | None:
    user_doc = await db["users"].find_one({"email": email.lower()})
    if user_doc:
        user_doc["id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None

async def get_user_by_id(user_id: str, db) -> UserInDB | None:
    if not ObjectId.is_valid(user_id):
        return None
    user_doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user_doc:
        user_doc["id"] = str(user_doc["_id"])
        return UserInDB(**user_doc)
    return None

async def register_user(user_data: UserCreate, db) -> UserResponse:
    doc = user_data.model_dump()
    doc["email"] = doc["email"].lower()
    doc["hashed_password"] = await password_work(hash_password, doc.pop("password"))
    doc["created_at"] = datetime.now(timezone.utc)
    
    result = await db["users"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return UserResponse(**doc)

async def authenticate_user(email: str, password: str, db) -> TokenResponse | None:
    user = await get_user_by_email(email, db)
    verified = await password_work(verify_password, password, user.hashed_password if user else dummy_hash)
    if not user or not verified:
        return None
        
    token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(**user.model_dump())
    )
