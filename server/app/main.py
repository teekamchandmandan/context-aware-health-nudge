from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import DEBUG
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Context-Aware Health Nudge", lifespan=lifespan)


if DEBUG:
    from app.seed import reset_and_seed

    @app.post("/debug/reset-seed")
    def debug_reset_seed() -> dict[str, str]:
        reset_and_seed()
        return {"status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
