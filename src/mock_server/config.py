from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MOCK_")

    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = "sqlite+aiosqlite:///./mock_server.db"
    admin_path: str = "/admin"
    log_retention_days: int = 7
    max_request_body_size: int = 1024 * 1024  # 1MB


settings = Settings()
