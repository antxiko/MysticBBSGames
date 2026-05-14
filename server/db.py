"""SQLite helpers para el servidor de scores."""
import os
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
    """SHA-256 hex del token plain."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


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


def insert_score(game: str, bbs_id: int, handle: str, score: int, extra: Optional[str]) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO scores (game, bbs_id, handle, score, extra) VALUES (?, ?, ?, ?, ?)",
            (game, bbs_id, handle, score, extra),
        )
        return cur.lastrowid


def top_scores_global(game: str, limit: int = 10, ascending: bool = False) -> list[sqlite3.Row]:
    """Top N a nivel global. Si ascending=True (movida), ordena ascendente."""
    order = "ASC" if ascending else "DESC"
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT s.handle, s.score, s.extra, s.created_at, b.short_name AS bbs_short_name
                FROM scores s JOIN bbs b ON s.bbs_id = b.id
                WHERE s.game = ?
                ORDER BY s.score {order}, s.created_at ASC
                LIMIT ?""",
            (game, limit),
        ).fetchall()


def top_scores_bbs(game: str, bbs_short_name: str, limit: int = 10, ascending: bool = False) -> list[sqlite3.Row]:
    """Top N de una BBS concreta."""
    order = "ASC" if ascending else "DESC"
    with get_conn() as conn:
        return conn.execute(
            f"""SELECT s.handle, s.score, s.extra, s.created_at, b.short_name AS bbs_short_name
                FROM scores s JOIN bbs b ON s.bbs_id = b.id
                WHERE s.game = ? AND b.short_name = ?
                ORDER BY s.score {order}, s.created_at ASC
                LIMIT ?""",
            (game, bbs_short_name.upper(), limit),
        ).fetchall()
