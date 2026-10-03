import pytest
from fastapi import Response
from pydantic import ValidationError

from app.config import Settings
from app.services import session_service


def production_settings(**changes):
    values = dict(ENVIRONMENT='production', JWT_SECRET_KEY='a71b039ed65b0f21908cd432a68e745f',
                  SMTP_HOST='smtp.example.test', SMTP_USERNAME='account', SMTP_PASSWORD='private-password',
                  SMTP_FROM_EMAIL='sender@example.test', CORS_ORIGINS=['https://health.example.test'],
                  ALLOWED_HOSTS=['health.example.test', 'api'], RATE_LIMIT_BACKEND='mongo',
                  MONGODB_URI='mongodb+srv://test:test@db.example.test/healthpatch?w=majority',
                  PASSWORD_RESET_URL_BASE='https://health.example.test/reset-password')
    values.update(changes)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize('secret', ['short', ' ' * 40, 'replace-with-a-long-random-secret', 'healthpatch-secret-key-change-in-production'])
def test_production_rejects_default_short_and_placeholder_secrets(secret):
    with pytest.raises(ValidationError):
        production_settings(JWT_SECRET_KEY=secret)


def test_production_rejects_empty_smtp_credentials():
    with pytest.raises(ValidationError):
        production_settings(SMTP_USERNAME='')


def test_production_accepts_configured_secret_and_rejects_wildcard_origin():
    assert production_settings().ENVIRONMENT == 'production'
    with pytest.raises(ValidationError):
        production_settings(CORS_ORIGINS=['*'])


@pytest.mark.parametrize('environment', ['production', 'PRODUCTION'])
def test_production_cookie_is_always_secure(monkeypatch, environment):
    monkeypatch.setattr(session_service.settings, 'ENVIRONMENT', environment)
    response = Response()
    session_service.set_cookie(response, 'test-only-token')
    cookie = response.headers['set-cookie'].lower()
    assert 'secure' in cookie and 'httponly' in cookie and 'samesite=strict' in cookie
