from fastapi import APIRouter

from app.seed import reset_and_seed

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/reset-seed")
def debug_reset_seed() -> dict[str, str]:
    reset_and_seed()
    return {"status": "ok"}