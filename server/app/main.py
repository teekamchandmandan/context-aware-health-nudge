import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import coach, debug, members, nudges, system
from app.core.config import DEBUG
from app.meal_analysis import create_meal_draft
from app.persistence.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DEBUG:
        logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Context-Aware Health Nudge", lifespan=lifespan)

    if DEBUG:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(system.router)
    app.include_router(members.router)
    app.include_router(nudges.router)
    app.include_router(coach.router)

    if DEBUG:
        app.include_router(debug.router)

    return app


app = create_app()
