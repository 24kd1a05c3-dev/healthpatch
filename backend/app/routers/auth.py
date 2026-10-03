import logging
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from bson import ObjectId
from app.services.session_service import COOKIE, fingerprint, check_origin, set_cookie, issue_session, audit
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import secrets
from app.models.user import UserCreate, TokenResponse, LoginRequest, UserInDB, UserResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import register_user, authenticate_user, get_user_by_email
from app.services.auth_service import password_work
from app.security import create_access_token, get_current_user, hash_password
from app.database import get_collection
from app.config import settings
from app.rate_limit import auth_rate_limit
from app.services.email_service import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

@router.post("/register", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
async def register(user_data: UserCreate, request: Request, response: Response, db=Depends(lambda: get_collection("users").database)):
    check_origin(request)
    if user_data.role != "patient":
        raise HTTPException(status_code=403, detail="Privileged accounts must be created by an administrator")
    existing = await get_user_by_email(user_data.email, db)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    try:
        user = await register_user(user_data, db)
    except DuplicateKeyError:
        raise HTTPException(409, 'Email already registered')
    await audit(db, user.id, 'register', user.id)
    return await issue_session(user, db, response)

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
async def login(req: LoginRequest, request: Request, response: Response, db=Depends(lambda: get_collection("users").database)):
    check_origin(request)
    token = await authenticate_user(req.email, req.password, db)
    if not token:
        await audit(db, 'anonymous', 'login', 'authentication', 'denied')
        raise HTTPException(status_code=401, detail="Invalid credentials")
    await audit(db, token.user.id, 'login', token.user.id)
    return await issue_session(token.user, db, response)

@router.post("/refresh", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
async def refresh(request: Request, response: Response, db=Depends(lambda: get_collection('users').database)):
    check_origin(request)
    old_token = request.cookies.get(COOKIE, '')
    now = datetime.now(timezone.utc)
    new_token = secrets.token_urlsafe(48)
    session = await db['sessions'].find_one_and_update(
        {'refresh_hash': fingerprint(old_token), 'revoked': False, 'expires_at': {'$gt': now}},
        {'$set': {'refresh_hash': fingerprint(new_token)}, '$addToSet': {'used_hashes': fingerprint(old_token)}})
    if not session:
        await db['sessions'].update_many({'used_hashes': fingerprint(old_token)}, {'$set': {'revoked': True}})
        raise HTTPException(401, 'Session expired. Sign in again.')
    doc = await db['users'].find_one({'_id': ObjectId(session['user_id'])})
    if not doc:
        raise HTTPException(401, 'Session expired. Sign in again.')
    doc['id'] = str(doc['_id'])
    set_cookie(response, new_token)
    return TokenResponse(access_token=create_access_token({'sub': doc['id'], 'sid': session['sid']}), token_type='bearer', user=UserResponse(**doc))

@router.post("/logout")
async def logout(request: Request, response: Response, db=Depends(lambda: get_collection('users').database)):
    check_origin(request)
    session = await db['sessions'].find_one_and_update({'refresh_hash': fingerprint(request.cookies.get(COOKIE, ''))}, {'$set': {'revoked': True}})
    if session:
        await audit(db, session['user_id'], 'logout', session['sid'])
    response.delete_cookie(COOKIE, path='/')
    return {"status": "success"}

@router.post("/forgot-password", dependencies=[Depends(auth_rate_limit)])
async def forgot_password(req: ForgotPasswordRequest, db=Depends(lambda: get_collection("users").database)):
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        raise HTTPException(503, 'Password reset email is not configured on this deployment')
    user = await get_user_by_email(req.email, db)
    if not user:
        return {"status": "success", "message": "If that email exists, a reset link has been sent."}

    token = secrets.token_urlsafe(32)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    await db["password_resets"].update_one(
        {"email": req.email},
        {"$set": {
            "email": req.email,
            "token_hash": token_hash,
            "created_at": now,
            "expires_at": now + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        }},
        upsert=True,
    )
    try:
        await send_password_reset_email(user.email, token)
    except Exception:
        logger.exception("Password reset email delivery failed")
        raise HTTPException(status_code=503, detail="Password reset email could not be sent")

    response = {
        "status": "success",
        "message": "If that email exists, a reset link has been sent.",
    }
    return response

@router.post("/reset-password", dependencies=[Depends(auth_rate_limit)])
async def reset_password(req: ResetPasswordRequest, db=Depends(lambda: get_collection("users").database)):
    reset_doc = await db["password_resets"].find_one_and_delete({
        "token_hash": sha256(req.token.encode("utf-8")).hexdigest(),
        "expires_at": {"$gt": datetime.now(timezone.utc)},
    })
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    await db["users"].update_one(
        {"email": reset_doc["email"]},
        {"$set": {"hashed_password": await password_work(hash_password, req.new_password)}},
    )
    await db["password_resets"].delete_one({"_id": reset_doc["_id"]})
    user = await get_user_by_email(reset_doc['email'], db)
    if user:
        await db['sessions'].update_many({'user_id': user.id}, {'$set': {'revoked': True}})
    return {"status": "success", "message": "Password updated successfully"}
