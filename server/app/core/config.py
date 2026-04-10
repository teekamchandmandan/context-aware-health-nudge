import os
from pathlib import Path

from dotenv import load_dotenv


SERVER_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(SERVER_ROOT / ".env")

DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(SERVER_ROOT / "nudge.db"))
DEBUG: bool = os.getenv("DEBUG", "").lower() == "true"
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
PHRASING_TIMEOUT_SECONDS: float = float(os.getenv("PHRASING_TIMEOUT_SECONDS", "20"))
MEAL_ANALYSIS_TIMEOUT_SECONDS: float = float(os.getenv("MEAL_ANALYSIS_TIMEOUT_SECONDS", "12"))


def get_openai_api_key() -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    return api_key.strip() if api_key else None