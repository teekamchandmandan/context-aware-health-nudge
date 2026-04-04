import sqlite3

from .common import COOLDOWN_HOURS, DAILY_CAP, NudgeCandidate, _now, _ts, timedelta
from .evaluators import ALL_EVALUATORS


def get_active_nudge(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM nudges WHERE member_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
        (member_id,),
    ).fetchone()


def has_newer_signal(conn: sqlite3.Connection, member_id: str, created_at: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM signals WHERE member_id = ? AND created_at > ? LIMIT 1",
        (member_id, created_at),
    ).fetchone()
    return row is not None


def supersede_active_nudge(conn: sqlite3.Connection, nudge_id: str) -> None:
    conn.execute(
        "UPDATE nudges SET status = 'superseded' WHERE id = ?",
        (nudge_id,),
    )


def check_cooldown(conn: sqlite3.Connection, member_id: str, nudge_type: str) -> bool:
    cutoff = _ts(_now() - timedelta(hours=COOLDOWN_HOURS))
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudge_actions na
           JOIN nudges n ON na.nudge_id = n.id
           WHERE n.member_id = ? AND n.nudge_type = ?
             AND na.action_type IN ('act_now', 'dismiss')
             AND na.created_at >= ?""",
        (member_id, nudge_type, cutoff),
    ).fetchone()
    return row["cnt"] > 0


def count_today_nudges(conn: sqlite3.Connection, member_id: str) -> int:
    today_start = _ts(_now().replace(hour=0, minute=0, second=0, microsecond=0))
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM nudges
           WHERE member_id = ? AND created_at >= ?
             AND status IN ('active', 'acted', 'dismissed', 'superseded')""",
        (member_id, today_start),
    ).fetchone()
    return row["cnt"]


def apply_fatigue(
    conn: sqlite3.Connection, member_id: str, candidates: list[NudgeCandidate]
) -> list[NudgeCandidate]:
    today_count = count_today_nudges(conn, member_id)
    result = []
    for candidate in candidates:
        if candidate.nudge_type == "support_risk":
            result.append(candidate)
            continue
        if check_cooldown(conn, member_id, candidate.nudge_type):
            continue
        if today_count >= DAILY_CAP:
            continue
        result.append(candidate)
    return result


def select_nudge(conn: sqlite3.Connection, member_id: str) -> NudgeCandidate | None:
    candidates = []
    for evaluator in ALL_EVALUATORS:
        candidate = evaluator(conn, member_id)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
        return None

    candidates = apply_fatigue(conn, member_id, candidates)
    if not candidates:
        return None

    candidates.sort(key=lambda candidate: candidate.latest_signal_ts, reverse=True)
    candidates.sort(key=lambda candidate: (candidate.priority, -candidate.confidence))
    return candidates[0]