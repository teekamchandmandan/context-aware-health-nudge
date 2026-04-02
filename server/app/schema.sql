CREATE TABLE IF NOT EXISTS members (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    goal_type   TEXT NOT NULL,
    profile_json TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id           TEXT PRIMARY KEY,
    member_id    TEXT NOT NULL REFERENCES members(id),
    signal_type  TEXT NOT NULL,
    payload_json TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nudges (
    id                     TEXT PRIMARY KEY,
    member_id              TEXT NOT NULL REFERENCES members(id),
    nudge_type             TEXT NOT NULL,
    content                TEXT,
    explanation            TEXT,
    matched_reason         TEXT,
    confidence             REAL,
    escalation_recommended INTEGER DEFAULT 0,
    status                 TEXT NOT NULL,
    generated_by           TEXT NOT NULL DEFAULT 'rule_engine',
    phrasing_source        TEXT NOT NULL DEFAULT 'template',
    created_at             TEXT NOT NULL,
    delivered_at           TEXT
);

CREATE TABLE IF NOT EXISTS nudge_actions (
    id            TEXT PRIMARY KEY,
    nudge_id      TEXT NOT NULL REFERENCES nudges(id),
    action_type   TEXT NOT NULL,
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    id          TEXT PRIMARY KEY,
    nudge_id    TEXT REFERENCES nudges(id),
    member_id   TEXT NOT NULL REFERENCES members(id),
    reason      TEXT,
    source      TEXT,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id           TEXT PRIMARY KEY,
    event_type   TEXT NOT NULL,
    entity_type  TEXT,
    entity_id    TEXT,
    payload_json TEXT,
    created_at   TEXT NOT NULL
);
