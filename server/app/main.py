import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEBUG
from app.database import get_db, init_db
from app.engine import evaluate_member
from app.models import (
    ActionRequest,
    ActionResponse,
    CoachEscalationItem,
    CoachEscalationListResponse,
    CoachNudgeItem,
    CoachNudgeListResponse,
    MemberNudgeResponse,
    MemberRef,
    NudgeDetail,
    NudgeState,
    SignalRequest,
    SignalResponse,
)

DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Context-Aware Health Nudge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if DEBUG:
    from app.seed import reset_and_seed

    @app.post("/debug/reset-seed")
    def debug_reset_seed() -> dict[str, str]:
        reset_and_seed()
        return {"status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_member(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    return row


def _get_nudge(conn: sqlite3.Connection, nudge_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Nudge not found")
    return row


TERMINAL_STATUSES = {"acted", "dismissed", "escalated"}


# ── GET /api/members/{member_id}/nudge ───────────────────────────────────────


@app.get("/api/members/{member_id}/nudge")
def get_member_nudge(
    member_id: Annotated[str, Path()],
    conn: DbDep,
) -> MemberNudgeResponse:
    member = _get_member(conn, member_id)
    member_ref = MemberRef(id=member["id"], name=member["name"])

    result = evaluate_member(conn, member_id)

    if result["state"] == "active":
        n = result["nudge"]
        return MemberNudgeResponse(
            state=NudgeState.active,
            member=member_ref,
            nudge=NudgeDetail(
                id=n["id"],
                nudge_type=n["nudge_type"],
                content=n["content"],
                explanation=n["explanation"],
                matched_reason=n["matched_reason"],
                confidence=n["confidence"],
                escalation_recommended=bool(n["escalation_recommended"]),
                status=n["status"],
                phrasing_source=n["phrasing_source"],
                created_at=n["created_at"],
            ),
        )
    elif result["state"] == "escalated":
        return MemberNudgeResponse(
            state=NudgeState.escalated,
            member=member_ref,
            nudge=None,
            escalation_created=True,
        )
    else:
        return MemberNudgeResponse(
            state=NudgeState.no_nudge,
            member=member_ref,
            nudge=None,
        )


# ── POST /api/nudges/{nudge_id}/action ──────────────────────────────────────


@app.post("/api/nudges/{nudge_id}/action")
def post_nudge_action(
    nudge_id: Annotated[str, Path()],
    body: ActionRequest,
    conn: DbDep,
) -> ActionResponse:
    nudge = _get_nudge(conn, nudge_id)

    if nudge["status"] in TERMINAL_STATUSES:
        raise HTTPException(status_code=409, detail="Nudge is already in a terminal state")

    action_type = body.action_type.value
    status_map = {
        "act_now": "acted",
        "dismiss": "dismissed",
        "ask_for_help": "escalated",
    }
    new_status = status_map[action_type]

    # Update nudge status
    conn.execute("UPDATE nudges SET status = ? WHERE id = ?", (new_status, nudge_id))

    # Record action
    action_id = uuid4().hex
    now = _ts()
    conn.execute(
        "INSERT INTO nudge_actions (id, nudge_id, action_type, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (action_id, nudge_id, action_type, None, now),
    )

    # ask_for_help side-effect: create escalation
    escalation_created = False
    if action_type == "ask_for_help":
        esc_id = uuid4().hex
        conn.execute(
            """INSERT INTO escalations (id, nudge_id, member_id, reason, source, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (esc_id, nudge_id, nudge["member_id"], "Member requested help", "member_action", "open", now),
        )
        escalation_created = True

    conn.commit()

    return ActionResponse(
        nudge_id=nudge_id,
        action_type=action_type,
        nudge_status=new_status,
        escalation_created=escalation_created,
        recorded_at=now,
    )


# ── POST /api/members/{member_id}/signals ────────────────────────────────────


@app.post("/api/members/{member_id}/signals")
def post_member_signal(
    member_id: Annotated[str, Path()],
    body: SignalRequest,
    conn: DbDep,
) -> SignalResponse:
    _get_member(conn, member_id)

    signal_id = uuid4().hex
    now = _ts()
    payload_dict = body.payload.model_dump(exclude_none=True)

    conn.execute(
        "INSERT INTO signals (id, member_id, signal_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (signal_id, member_id, body.signal_type.value, json.dumps(payload_dict), now),
    )
    conn.commit()

    return SignalResponse(
        id=signal_id,
        member_id=member_id,
        signal_type=body.signal_type.value,
        payload=payload_dict,
        created_at=now,
    )


# ── GET /api/coach/nudges ───────────────────────────────────────────────────


@app.get("/api/coach/nudges")
def get_coach_nudges(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachNudgeListResponse:
    rows = conn.execute(
        """SELECT n.id, n.member_id, m.name AS member_name, n.nudge_type,
                  n.content, n.explanation, n.matched_reason, n.confidence,
                  n.escalation_recommended, n.status, n.created_at
           FROM nudges n
           JOIN members m ON n.member_id = m.id
           ORDER BY n.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    items: list[CoachNudgeItem] = []
    for r in rows:
        # Latest action for this nudge
        action_row = conn.execute(
            "SELECT action_type FROM nudge_actions WHERE nudge_id = ? ORDER BY created_at DESC LIMIT 1",
            (r["id"],),
        ).fetchone()
        items.append(
            CoachNudgeItem(
                nudge_id=r["id"],
                member_id=r["member_id"],
                member_name=r["member_name"],
                nudge_type=r["nudge_type"],
                content=r["content"],
                explanation=r["explanation"],
                matched_reason=r["matched_reason"],
                confidence=r["confidence"],
                escalation_recommended=bool(r["escalation_recommended"]),
                status=r["status"],
                latest_action=action_row["action_type"] if action_row else None,
                created_at=r["created_at"],
            )
        )

    return CoachNudgeListResponse(items=items, limit=limit, count=len(items))


# ── GET /api/coach/escalations ───────────────────────────────────────────────


@app.get("/api/coach/escalations")
def get_coach_escalations(
    conn: DbDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> CoachEscalationListResponse:
    rows = conn.execute(
        """SELECT e.id, e.member_id, m.name AS member_name, e.reason,
                  e.source, e.status, e.created_at
           FROM escalations e
           JOIN members m ON e.member_id = m.id
           WHERE e.status = 'open'
           ORDER BY e.created_at DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    items = [
        CoachEscalationItem(
            escalation_id=r["id"],
            member_id=r["member_id"],
            member_name=r["member_name"],
            reason=r["reason"],
            source=r["source"],
            status=r["status"],
            created_at=r["created_at"],
        )
        for r in rows
    ]

    return CoachEscalationListResponse(items=items, limit=limit, count=len(items))
