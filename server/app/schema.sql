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
    confidence             REAL CHECK(confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    confidence_factors_json TEXT,
    escalation_recommended INTEGER DEFAULT 0 CHECK(escalation_recommended IN (0, 1)),
    status                 TEXT NOT NULL CHECK(status IN ('active', 'acted', 'dismissed', 'escalated', 'superseded')),
    generated_by           TEXT NOT NULL DEFAULT 'rule_engine',
    phrasing_source        TEXT NOT NULL DEFAULT 'template',
    created_at             TEXT NOT NULL,
    delivered_at           TEXT
);

CREATE TABLE IF NOT EXISTS nudge_actions (
    id            TEXT PRIMARY KEY,
    nudge_id      TEXT NOT NULL REFERENCES nudges(id),
    action_type   TEXT NOT NULL CHECK(action_type IN ('act_now', 'dismiss', 'ask_for_help')),
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    id          TEXT PRIMARY KEY,
    nudge_id    TEXT REFERENCES nudges(id),
    member_id   TEXT NOT NULL REFERENCES members(id),
    reason      TEXT,
    source      TEXT CHECK(source IS NULL OR source IN ('rule_engine', 'member_action')),
    status      TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open', 'resolved')),
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

-- Prevent duplicate active nudges for the same member (guards against concurrent evaluate_member calls)
-- Repair legacy duplicates before enforcing the one-active-nudge invariant.
-- Keep the newest active nudge per member and mark older ones as superseded.
WITH ranked_active_nudges AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY member_id
            ORDER BY created_at DESC, id DESC
        ) AS row_num
    FROM nudges
    WHERE status = 'active'
)
UPDATE nudges
SET status = 'superseded'
WHERE id IN (
    SELECT id
    FROM ranked_active_nudges
    WHERE row_num > 1
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_nudge_per_member ON nudges(member_id) WHERE status = 'active';

-- Performance indexes for frequent query patterns
CREATE INDEX IF NOT EXISTS idx_signals_member_type ON signals(member_id, signal_type, created_at);
CREATE INDEX IF NOT EXISTS idx_nudges_member_status ON nudges(member_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_nudge_actions_nudge ON nudge_actions(nudge_id, created_at);
CREATE INDEX IF NOT EXISTS idx_escalations_member_status ON escalations(member_id, status, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type, created_at);
