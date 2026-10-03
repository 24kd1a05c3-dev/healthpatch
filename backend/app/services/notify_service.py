"""Notify doctors and caregivers watching a patient."""

from app.services.auth_service import get_user_by_id


async def get_watchers_for_patient(patient_id: str, db) -> list[str]:
    watchers: set[str] = set()

    patient = await get_user_by_id(patient_id, db)
    if patient and patient.assigned_doctor_id:
        watchers.add(patient.assigned_doctor_id)

    cursor = db["users"].find({
        "role": {"$in": ["doctor", "caregiver", "admin"]},
        "assigned_patients": patient_id,
    })
    docs = await cursor.to_list(length=50)
    for doc in docs:
        watchers.add(str(doc["_id"]))

    return list(watchers)


async def notify_watchers(patient_id: str, message: dict, db, manager) -> None:
    for watcher_id in await get_watchers_for_patient(patient_id, db):
        if watcher_id != patient_id:
            await manager.send_to_user(watcher_id, message)
