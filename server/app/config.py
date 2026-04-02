import os
from pathlib import Path

DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "nudge.db"))
DEBUG: bool = os.getenv("DEBUG", "").lower() == "true"
