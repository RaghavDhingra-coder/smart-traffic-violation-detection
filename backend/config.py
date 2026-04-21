# TODO for backend-configuration: add environment-specific settings profiles and secrets management before production.
from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://traffic_admin:traffic_password@postgres:5432/traffic_violation_db"
    redis_url: str = "redis://redis:6379/0"
    razorpay_key_id: str = "rzp_test_dummyKeyId"
    razorpay_key_secret: str = "dummyKeySecret"
    vaahan_api_key: str = "dummy_vaahan_api_key"
    ai_engine_url: str = "http://ai-engine:8001"
    backend_cors_origins: str = "*"
    upload_dir: str = "uploads"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
