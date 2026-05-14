-- BBS Scores server schema (SQLite)
-- Run once: sqlite3 data/scores.db < schema.sql

CREATE TABLE IF NOT EXISTS bbs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    short_name  TEXT    UNIQUE NOT NULL,     -- "VALAR", uppercased
    full_name   TEXT,                         -- "Valar BBS"
    token_hash  TEXT    NOT NULL,             -- sha256 hex del token
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scores (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game        TEXT    NOT NULL,
    bbs_id      INTEGER NOT NULL REFERENCES bbs(id) ON DELETE CASCADE,
    handle      TEXT    NOT NULL,             -- "AGM"
    score       INTEGER NOT NULL,
    extra       TEXT,                          -- JSON serializado opcional
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_scores_game_score
    ON scores(game, score DESC);
CREATE INDEX IF NOT EXISTS idx_scores_bbs_game
    ON scores(bbs_id, game, score DESC);

-- Admins del panel web. Password almacenada como pbkdf2_hmac-sha256 con salt.
CREATE TABLE IF NOT EXISTS admin (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,         -- formato "salt_hex:digest_hex"
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
