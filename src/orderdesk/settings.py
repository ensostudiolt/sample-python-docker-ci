from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://orderdesk:orderdesk@localhost:5432/orderdesk"
    app_env: str = "development"
    worker_poll_seconds: float = 2.0
    worker_batch_size: int = 10
    worker_heartbeat_path: str = "/tmp/orderdesk-worker-heartbeat"


settings = Settings()
