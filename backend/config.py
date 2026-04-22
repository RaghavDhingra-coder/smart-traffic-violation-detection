# TODO for backend-configuration: add environment-specific settings profiles and secrets management before production.
from urllib.parse import unquote, urlparse

from pydantic import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:1234@localhost:5432/traffic"
    backend_cors_origins: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def psycopg2_dsn(self) -> str:
        normalized_url = self.database_url.replace("postgresql+psycopg2://", "postgresql://", 1)
        parsed = urlparse(normalized_url)

        dbname = parsed.path.lstrip("/")
        user = unquote(parsed.username or "")
        password = unquote(parsed.password or "")
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432

        return (
            f"dbname={dbname} "
            f"user={user} "
            f"password={password} "
            f"host={host} "
            f"port={port}"
        )


settings = Settings()
