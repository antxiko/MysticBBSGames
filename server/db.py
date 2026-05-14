"""SQLite helpers para el servidor de scores."""
import os
import secrets
import sqlite3
import hashlib
from contextlib import contextmanager
from typing import Optional, Iterator

DB_PATH = os.environ.get(
    "BBS_SCORES_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "scores.db"),
)
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def hash_token(token: str) -> str:
    """SHA-256 hex del token plain. Tokens son aleatorios largos, SHA256 vale."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: bytes = None) -> str:
    """PBKDF2-HMAC-SHA256 con 100k iteraciones. Devuelve 'salt_hex:digest_hex'."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + digest.hex()


def verify_password(password: str, stored: str) -> bool:
    """Verifica un password plain contra el hash almacenado."""
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return secrets.compare_digest(computed, expected)
    except Exception:
        return False


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Conexion SQLite con foreign keys y row factory de dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea las tablas si no existen. Idempotente."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()
    with get_conn() as conn:
        conn.executescript(schema)


def find_bbs_by_token(token: str) -> Optional[sqlite3.Row]:
    """Devuelve la BBS asociada al token plain, o None si no match o desactivada."""
    h = hash_token(token)
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, short_name, full_name, enabled FROM bbs WHERE token_hash = ?",
            (h,),
        ).fetchone()
        if row and row["enabled"]:
            return row
    return None


def list_bbses() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, short_name, full_name, enabled, created_at FROM bbs ORDER BY short_name"
        ).fetchall()


def find_bbs_by_short_name(short_name: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, short_name, full_name, enabled FROM bbs WHERE short_name = ?",
            (short_name.upper(),),
        ).fetchone()


def insert_bbs(short_name: str, full_name: str, token_hash: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO bbs (short_name, full_name, token_hash) VALUES (?, ?, ?)",
            (short_name.upper(), full_name, token_hash),
        )
        return cur.lastrowid


def set_bbs_enabled(short_name: str, enabled: bool) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE bbs SET enabled = ? WHERE short_name = ?",
            (1 if enabled else 0, short_name.upper()),
        )
        return cur.rowcount > 0


def update_bbs_token(short_name: str, token_hash: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE bbs SET token_hash = ? WHERE short_name = ?",
            (token_hash, short_name.upper()),
        )
        return cur.rowcount > 0


def delete_bbs(short_name: str) -> tuple[bool, int]:
    """Elimina una BBS y todos sus scores (cascade). Devuelve (ok, scores_borrados)."""
    with get_conn() as conn:
        bbs = conn.execute(
            "SELECT id FROM bbs WHERE short_name = ?", (short_name.upper(),)
        ).fetchone()
        if bbs is None:
            return False, 0
        scores_count = conn.execute(
            "SELECT COUNT(*) FROM scores WHERE bbs_id = ?", (bbs["id"],)
        ).fetchone()[0]
        conn.execute("DELETE FROM bbs WHERE id = ?", (bbs["id"],))
        return True, scores_count


def count_scores_for_bbs(bbs_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM scores WHERE bbs_id = ?", (bbs_id,)
        ).fetchone()
        return row["n"] if row else 0


# --- admin ---

def find_admin(username: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, password_hash FROM admin WHERE username = ?",
            (username,),
        ).fetchone()


def upsert_admin(username: str, password_hash: str) -> str:
    """Crea o actualiza el password del admin. Devuelve 'created' o 'updated'."""
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM admin WHERE username = ?", (username,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE admin SET password_hash = ? WHERE username = ?",
                (password_hash, username),
            )
            return "updated"
        conn.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (username, password_hash),
        )
        return "created"


def list_admins() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, username, created_at FROM admin ORDER BY username"
        ).fetchall()


def insert_score(game: str, bbs_id: int, handle: str, score: int, extra: Optional[str]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scores (game, bbs_id, handle, score, extra) VALUES (?, ?, ?, ?, ?)",
            (game, bbs_id, handle, score, extra),
        )
        return cur.lastrowid


PERIOD_FILTERS = {
    "all": "",
    "week": "AND s.created_at >= datetime('now', '-7 days')",
    "month": "AND s.created_at >= datetime('now', '-30 days')",
}


def top_scores_global(game: str, limit: int = 10, ascending: bool = False,
                     period: str = "all") -> list[sqlite3.Row]:
    """Top N a nivel global. period: 'all' | 'week' | 'month'."""
    order = "ASC" if ascending else "DESC"
    period_clause = PERIOD_FILTERS.get(period, "")
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT s.handle, s.score, s.extra, s.created_at, b.short_name AS bbs_short_name
                FROM scores s JOIN bbs b ON s.bbs_id = b.id
                WHERE s.game = ? {period_clause}
                ORDER BY s.score {order}, s.created_at ASC
                LIMIT ?""",
            (game, limit),
        ).fetchall()


def top_scores_bbs(game: str, bbs_short_name: str, limit: int = 10, ascending: bool = False,
                   period: str = "all") -> list[sqlite3.Row]:
    """Top N de una BBS concreta. period: 'all' | 'week' | 'month'."""
    order = "ASC" if ascending else "DESC"
    period_clause = PERIOD_FILTERS.get(period, "")
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT s.handle, s.score, s.extra, s.created_at, b.short_name AS bbs_short_name
                FROM scores s JOIN bbs b ON s.bbs_id = b.id
                WHERE s.game = ? AND b.short_name = ? {period_clause}
                ORDER BY s.score {order}, s.created_at ASC
                LIMIT ?""",
            (game, bbs_short_name.upper(), limit),
        ).fetchall()


def list_games() -> list[str]:
    """Distinct game names que tienen al menos un score."""
    with get_conn() as conn:
        return [r[0] for r in conn.execute(
            "SELECT DISTINCT game FROM scores ORDER BY game"
        ).fetchall()]


def stats_globales() -> dict:
    """Resumen para la landing publica."""
    with get_conn() as conn:
        bbs_activas = conn.execute("SELECT COUNT(*) FROM bbs WHERE enabled = 1").fetchone()[0]
        scores_total = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        juegos = conn.execute("SELECT COUNT(DISTINCT game) FROM scores").fetchone()[0]
        return {
            "bbs_activas": bbs_activas,
            "scores_total": scores_total,
            "juegos": juegos,
        }
