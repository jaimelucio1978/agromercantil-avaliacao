from pathlib import Path
from dataclasses import dataclass
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

@dataclass
class Settings:
    pg_user: str = os.getenv("POSTGRES_USER", "postgres")
    pg_password: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    pg_host: str = os.getenv("POSTGRES_HOST", "localhost")
    pg_port: str = os.getenv("POSTGRES_PORT", "5432")
    pg_db: str = os.getenv("POSTGRES_DB", "agromercantil")

    app_env: str = os.getenv("APP_ENV", "local")
    data_path: Path = ROOT / os.getenv("DATA_PATH", "data")
    source_name: str = os.getenv("SOURCE_NAME", "CEPEA")

    @property
    def sqlalchemy_url(self) -> str:
        # pg8000 (puro Python): não precisa de compilação
        return (
            f"postgresql+pg8000://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

SETTINGS = Settings()