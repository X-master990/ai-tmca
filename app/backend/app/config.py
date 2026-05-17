"""應用程式設定（從環境變數讀）"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TMCA backend settings — 全部從 env / .env 讀。"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://tmca:changeme@db:5432/tmca"

    # JWT
    jwt_secret: str = "dev-secret-please-change"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 8

    # App
    timezone: str = "Asia/Taipei"
    frontend_origin: str = "http://localhost"

    # File paths (mounted volume)
    template_dir: str = "/var/tmca/templates"
    output_dir: str = "/var/tmca/output"


settings = Settings()
