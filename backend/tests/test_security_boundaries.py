import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.authz import ensure_patient_access, user_can_access_patient
from app.main import app
from app.models.user import UserInDB
from app.routers import auth as auth_router
from app.routers import devices as devices_router
from app.routers import health_data as health_router
from app.routers import users as users_router
from app.security import get_current_user


def user(user_id: str, role: str = "patient", assigned_patients: list[str] | None = None) -> UserInDB:
    return UserInDB(
        id=user_id,
        email=f"{user_id}@example.com",
        hashed_password="hash",
        full_name="Test User",
        role=role,
        assigned_patients=assigned_patients or [],
        created_at=datetime.now(timezone.utc),
    )


def test_patient_access_denies_unassigned_user():
    current_user = user("caller")

    assert user_can_access_patient(current_user, "other") is False
    with pytest.raises(Exception):
        ensure_patient_access(current_user, "other")


def test_patient_access_allows_assigned_doctor():
    current_user = user("doctor", role="doctor", assigned_patients=["patient-1"])

    assert user_can_access_patient(current_user, "patient-1") is True


def test_public_registration_cannot_create_admin(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None

    monkeypatch.setattr(auth_router, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_router, "get_collection", lambda name: type("C", (), {"database": object()})())

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "email": "admin-request@example.com",
                "password": "long-enough-for-test",
                "full_name": "Admin Request",
                "role": "admin",
            },
        )

    assert response.status_code == 403


def test_public_registration_cannot_create_caregiver(monkeypatch):
    async def fake_get_user_by_email(email, db):
        return None

    monkeypatch.setattr(auth_router, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_router, "get_collection", lambda name: type("C", (), {"database": object()})())

    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "email": "caregiver-request@example.com",
                "password": "long-enough-for-test",
                "full_name": "Caregiver Request",
                "role": "caregiver",
            },
        )

    assert response.status_code == 403


def test_forgot_password_does_not_return_token_in_production(monkeypatch):
    class FakePasswordResets:
        async def update_one(self, *args, **kwargs):
            return None

    class FakeDb:
        def __getitem__(self, name):
            assert name == "password_resets"
            return FakePasswordResets()

    async def fake_get_user_by_email(email, db):
        return user("patient")

    async def fake_send_password_reset_email(to_email, reset_token):
        return None

    monkeypatch.setattr(auth_router.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_router.settings, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(auth_router.settings, "SMTP_FROM_EMAIL", "noreply@example.test")
    monkeypatch.setattr(auth_router, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send_password_reset_email)
    monkeypatch.setattr(auth_router, "get_collection", lambda name: type("C", (), {"database": FakeDb()})())

    with TestClient(app) as client:
        response = client.post("/auth/forgot-password", json={"email": "patient@example.com"})

    assert response.status_code == 200
    assert "reset_token" not in response.json()


def test_health_ingest_rejects_mismatched_user(monkeypatch):
    async def fake_current_user():
        return user("caller")

    app.dependency_overrides[get_current_user] = fake_current_user
    monkeypatch.setattr(health_router, "get_collection", lambda name: type("C", (), {"database": object()})())

    try:
        with TestClient(app) as client:
            response = client.post(
                "/health-data/",
                json={
                    "device_id": "SHP-ESP32-0001",
                    "user_id": "other",
                    "heart_rate": 72,
                    "spo2": 98,
                    "temperature": 36.6,
                    "battery": 90,
                    "signal_quality": 0.95,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


class FakeDevicesCollection:
    async def find_one(self, query):
        return {
            "device_id": "SHP-ESP32-0001",
            "user_id": "other-patient",
            "status": "ONLINE",
            "firmware_version": "1.0.0",
        }


class FakeDb:
    def __getitem__(self, name):
        assert name == "devices"
        return FakeDevicesCollection()


def test_device_read_rejects_other_patient_device(monkeypatch):
    async def fake_current_user():
        return user("caller")

    app.dependency_overrides[get_current_user] = fake_current_user
    monkeypatch.setattr(devices_router, "get_collection", lambda name: type("C", (), {"database": FakeDb()})())

    try:
        with TestClient(app) as client:
            response = client.get("/devices/SHP-ESP32-0001")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_non_admin_cannot_create_privileged_user(monkeypatch):
    async def fake_current_user():
        return user("doctor", role="doctor")

    app.dependency_overrides[get_current_user] = fake_current_user
    monkeypatch.setattr(users_router, "get_collection", lambda name: type("C", (), {"database": object()})())

    try:
        with TestClient(app) as client:
            response = client.post(
                "/users/",
                json={
                    "email": "doctor2@example.com",
                    "password": "long-enough",
                    "full_name": "Doctor Two",
                    "role": "doctor",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
