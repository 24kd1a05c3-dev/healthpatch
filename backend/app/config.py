from typing import Any
from urllib.parse import urlparse, parse_qs

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    MONGODB_URI: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "healthpatch"
    JWT_SECRET_KEY: str = "healthpatch-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_URL_BASE: str = "http://localhost:5173/reset-password"
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_AUTH_MAX_ATTEMPTS: int = 10
    RATE_LIMIT_BACKEND: str = 'memory'
    NOTIFICATIONS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None
    TWILIO_VERIFY_SERVICE_SID: str | None = None
    NOTIFICATION_PUBLIC_BASE: str | None = None
    ALLOWED_HOSTS: list[str] = ['localhost', '127.0.0.1', 'testserver']
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_USE_TLS: bool = True
    DATASET_ROOT: str = "datasets"
    TELEMETRY_PROCESSING_VERSION: str = "1.0.0"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:3000", "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            database_url = urlparse(self.MONGODB_URI)
            database_options = parse_qs(database_url.query)
            tls = database_url.scheme == 'mongodb+srv' or database_options.get('tls') == ['true']
            if not database_url.username or not database_url.password or not tls or database_options.get('tls') == ['false']:
                raise ValueError('Production MongoDB requires authenticated TLS access')
            secret = self.JWT_SECRET_KEY.strip()
            if len(secret) < 32 or secret == "healthpatch-secret-key-change-in-production" or secret.lower().startswith("replace-"):
                raise ValueError("JWT_SECRET_KEY must be a private random secret of at least 32 characters in production")
            if "*" in self.CORS_ORIGINS:
                raise ValueError("CORS_ORIGINS cannot include '*' in production")
            if not self.CORS_ORIGINS or any(urlparse(origin).scheme != 'https' or not urlparse(origin).hostname
                                          or urlparse(origin).path not in ('', '/') for origin in self.CORS_ORIGINS):
                raise ValueError('Production CORS origins must be explicit HTTPS origins')
            if not self.ALLOWED_HOSTS or any(host in ('*', 'testserver', 'localhost', '127.0.0.1') for host in self.ALLOWED_HOSTS):
                raise ValueError('Production ALLOWED_HOSTS must name the deployment hosts')
            if self.RATE_LIMIT_BACKEND != 'mongo':
                raise ValueError('Production requires the shared mongo rate limiter')
            if not self.SMTP_USE_TLS or urlparse(self.PASSWORD_RESET_URL_BASE).scheme != 'https':
                raise ValueError('Production requires SMTP TLS and an HTTPS password reset URL')
            required_smtp = [self.SMTP_HOST, self.SMTP_USERNAME, self.SMTP_PASSWORD, self.SMTP_FROM_EMAIL]
            if any(not value or not value.strip() for value in required_smtp):
                raise ValueError("SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL are required in production")
        if self.RATE_LIMIT_BACKEND not in ('memory', 'mongo'):
            raise ValueError('RATE_LIMIT_BACKEND must be memory or mongo')
        if self.RATE_LIMIT_WINDOW_SECONDS < 1 or self.RATE_LIMIT_AUTH_MAX_ATTEMPTS < 1:
            raise ValueError('Rate limit settings must be positive')
        if self.JWT_ALGORITHM != 'HS256':
            raise ValueError('This deployment supports only the HS256 JWT signing configuration')
        if self.NOTIFICATIONS_ENABLED:
            required = [self.TWILIO_ACCOUNT_SID, self.TWILIO_AUTH_TOKEN, self.TWILIO_FROM_NUMBER,
                        self.TWILIO_VERIFY_SERVICE_SID, self.NOTIFICATION_PUBLIC_BASE]
            if any(not value or value.startswith('replace-') for value in required):
                raise ValueError('Enabled notifications require Twilio credentials, sender, Verify service and public base URL')
            if urlparse(self.NOTIFICATION_PUBLIC_BASE).scheme != 'https':
                raise ValueError('Notification callback base must use HTTPS')
        return self

settings = Settings()
