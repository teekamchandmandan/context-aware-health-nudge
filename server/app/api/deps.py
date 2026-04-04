from typing import Annotated

import sqlite3

from fastapi import Depends, HTTPException

from app.persistence.database import get_db

DbDep = Annotated[sqlite3.Connection, Depends(get_db)]


def get_member_or_404(conn: sqlite3.Connection, member_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Member not found")
    return row


def get_nudge_or_404(conn: sqlite3.Connection, nudge_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM nudges WHERE id = ?", (nudge_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Nudge not found")
    return row