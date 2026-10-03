from fastapi import APIRouter, Depends, HTTPException
from app.models.user import AdminUserCreate, PatientAssignment, UserInDB, UserResponse, UserUpdate
from app.services.auth_service import get_user_by_email, register_user
from app.security import get_current_user, require_role
from app.database import get_collection
from bson import ObjectId
import pymongo
from app.services.session_service import audit

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_me(
    updates: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(lambda: get_collection("users").database),
):
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        return current_user
    if 'phone' in update_data and update_data['phone'] != current_user.phone:
        update_data.update({'verified_notification_phone': None, 'notification_preferences': {'sms': False, 'voice': False}})

    await db["users"].update_one({"_id": ObjectId(current_user.id)}, {"$set": update_data})
    await audit(db, current_user.id, 'profile_updated', current_user.id)
    doc = await db["users"].find_one({"_id": ObjectId(current_user.id)})
    doc["id"] = str(doc["_id"])
    return UserResponse(**doc)

@router.get("/patients", response_model=list[UserResponse])
async def list_patients(
    current_user: UserInDB = Depends(require_role("doctor", "admin", "caregiver")),
    db=Depends(lambda: get_collection("users").database),
):
    if current_user.role == "admin":
        cursor = db["users"].find({"role": "patient"}, sort=[("created_at", pymongo.DESCENDING)]).limit(100)
    else:
        patient_ids = [ObjectId(pid) for pid in current_user.assigned_patients if ObjectId.is_valid(pid)]
        cursor = db["users"].find({"_id": {"$in": patient_ids}}).limit(100)

    docs = await cursor.to_list(length=100)
    for d in docs:
        d["id"] = str(d["_id"])
    return [UserResponse(**d) for d in docs]

@router.post("/", response_model=UserResponse)
async def admin_create_user(
    user_data: AdminUserCreate,
    current_user: UserInDB = Depends(require_role("admin")),
    db=Depends(lambda: get_collection("users").database),
):
    existing = await get_user_by_email(user_data.email, db)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    return await register_user(user_data, db)

@router.post("/{staff_id}/patients", response_model=UserResponse)
async def assign_patient(
    staff_id: str,
    assignment: PatientAssignment,
    current_user: UserInDB = Depends(require_role("admin")),
    db=Depends(lambda: get_collection("users").database),
):
    if not ObjectId.is_valid(staff_id) or not ObjectId.is_valid(assignment.patient_id):
        raise HTTPException(status_code=404, detail="User not found")

    staff = await db["users"].find_one({"_id": ObjectId(staff_id), "role": {"$in": ["doctor", "caregiver"]}})
    patient = await db["users"].find_one({"_id": ObjectId(assignment.patient_id), "role": "patient"})
    if not staff or not patient:
        raise HTTPException(status_code=404, detail="User not found")

    updated = await db["users"].find_one_and_update(
        {"_id": ObjectId(staff_id)},
        {"$addToSet": {"assigned_patients": assignment.patient_id}},
        return_document=pymongo.ReturnDocument.AFTER,
    )
    updated["id"] = str(updated["_id"])
    return UserResponse(**updated)

@router.delete("/{staff_id}/patients/{patient_id}", response_model=UserResponse)
async def unassign_patient(
    staff_id: str,
    patient_id: str,
    current_user: UserInDB = Depends(require_role("admin")),
    db=Depends(lambda: get_collection("users").database),
):
    if not ObjectId.is_valid(staff_id) or not ObjectId.is_valid(patient_id):
        raise HTTPException(status_code=404, detail="User not found")

    updated = await db["users"].find_one_and_update(
        {"_id": ObjectId(staff_id), "role": {"$in": ["doctor", "caregiver"]}},
        {"$pull": {"assigned_patients": patient_id}},
        return_document=pymongo.ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    updated["id"] = str(updated["_id"])
    return UserResponse(**updated)
