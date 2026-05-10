from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./app.db"
    # jwt_secret tiene default solo para dev/tests; en producción debe overridearse vía GADS_JWT_SECRET.
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    initial_admin_user: str | None = None
    initial_admin_password: str | None = None
    initial_admin_email: str | None = None
    initial_empresa_razon_social: str | None = None
    initial_empresa_cuit: str | None = None

    default_timezone: str = "America/Argentina/Buenos_Aires"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GADS_", extra="ignore")


settings = Settings()
