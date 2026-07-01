from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MOCK_")

    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str = "sqlite+aiosqlite:///./mock_server.db"
    admin_path: str = "/admin"
    log_retention_days: int = 7
    max_request_body_size: int = 20 * 1024 * 1024  # 20MB (20971520, 支持 base64 图片)


settings = Settings()
