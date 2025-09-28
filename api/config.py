import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"

load_dotenv(dotenv_path=env_path)


class Settings:
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", 5432)
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "tdd")
    POSTGRES_SSLMODE: str = os.getenv("POSTGRES_SSLMODE", "prefer")
    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode={POSTGRES_SSLMODE}"


settings = Settings()
