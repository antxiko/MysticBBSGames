"""Cliente compartido para el scoreboard online de MysticBBSGames.

Transparente al juego: si no se pasa `game=`, se autodetecta del directorio
del script que llama. Convencion: cada juego vive en `<game>/<game>.py` y su
top local va a `<game>/<game>_scores.txt`. Asi, añadir un juego nuevo no
requiere tocar nada de este modulo ni del server.

API minima:
- submit(handle, score, extra=None)          -> manda al server, fire-and-forget
- save_local(handle, score, ascending=False) -> guarda local y devuelve top
- top_local(limit=10, ascending=False)       -> top de la BBS local
- top_global(limit=10, ascending=False)      -> top mundial (red, fallback local)
- top_bbs(limit=10, ascending=False)         -> top de tu BBS via red (fallback local)
- entra_en_top_local(score, ascending=False) -> bool
- is_online()                                -> True si el server respondio

Todas las funciones aceptan `game=` explicito para overridear la autodeteccion.

Si no hay config (scores_config.json) o el server no responde, todo cae al modo
local-only y los juegos siguen funcionando igual que antes.
"""
from __future__ import annotations

import inspect
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(REPO_ROOT, "scores_config.json")
PENDING_PATH = os.path.join(REPO_ROOT, "pending_submissions.jsonl")


@dataclass
class ScoreEntry:
    handle: str
    bbs_short_name: str
    score: int
    date: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def display_handle(self) -> str:
        """Para listas globales mostramos INICIALES@BBS_SHORT. Si la BBS coincide
        con la local, los juegos pueden decidir no enseñar el sufijo."""
        return f"{self.handle}@{self.bbs_short_name}" if self.bbs_short_name else self.handle


@dataclass
class Config:
    server_url: str = ""
    bbs_short_name: str = "LOCAL"
    full_name: str = ""
    api_token: str = ""
    timeout_seconds: float = 2.0
    cache_seconds: int = 60

    @classmethod
    def load(cls) -> "Config":
        if not os.path.exists(CONFIG_PATH):
            return cls()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(
                server_url=data.get("server_url", "").rstrip("/"),
                bbs_short_name=data.get("bbs_short_name", "LOCAL").upper(),
                full_name=data.get("full_name", ""),
                api_token=data.get("api_token", ""),
                timeout_seconds=float(data.get("timeout_seconds", 2.0)),
                cache_seconds=int(data.get("cache_seconds", 60)),
            )
        except Exception:
            return cls()

    @property
    def online_enabled(self) -> bool:
        return bool(self.server_url and self.api_token)


# Lazy singleton
_config: Optional[Config] = None
_online_state = {"last_check_ok": None, "last_check_at": 0.0}
_top_cache: dict[tuple[str, str, int, bool], tuple[float, list[ScoreEntry]]] = {}


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def is_online() -> bool:
    return _online_state["last_check_ok"] is True


# ---------- autodeteccion del juego ----------

def _detect_caller() -> tuple[str, str]:
    """Devuelve (game_name, caller_dir) del script que llamo a este modulo.
    game_name = filename del script sin extension (ej. 'dino' de dino.py).
    caller_dir = directorio absoluto donde vive el script.
    Funciona tanto en layout flat (todos .py juntos) como en subdirs."""
    for frame_info in inspect.stack()[1:]:
        f = frame_info.filename
        if os.path.abspath(f) == os.path.abspath(__file__):
            continue
        caller_dir = os.path.dirname(os.path.abspath(f))
        stem = os.path.splitext(os.path.basename(f))[0]
        if stem:
            return stem.lower(), caller_dir
    return "unknown", REPO_ROOT


def _resolve_caller(game: Optional[str]) -> tuple[str, str]:
    """Devuelve (game_name, scores_dir). Si pasas `game` explicito se respeta
    pero el dir se sigue autodetectando del caller."""
    detected_game, caller_dir = _detect_caller()
    if game:
        return game.lower(), caller_dir
    return detected_game, caller_dir


def _scores_path(game: str, scores_dir: str) -> str:
    return os.path.join(scores_dir, f"{game}_scores.txt")


# ---------- fichero local ----------

def top_local(limit: int = 10, ascending: bool = False, *, game: str | None = None) -> list[ScoreEntry]:
    """Top de la BBS local desde el fichero. Tolera separadores tab y semicolon
    para compatibilidad con ficheros historicos del repo."""
    game, scores_dir = _resolve_caller(game)
    path = _scores_path(game, scores_dir)
    if not os.path.exists(path):
        return []
    out: list[ScoreEntry] = []
    bbs_name = get_config().bbs_short_name
    try:
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                parts = ln.split("\t") if "\t" in ln else ln.split(";")
                if len(parts) < 3:
                    continue
                handle = parts[0]
                try:
                    score = int(parts[1])
                except ValueError:
                    continue
                date = parts[2] if len(parts) > 2 else ""
                extra: dict[str, Any] = {}
                if len(parts) > 3:
                    extra = {"raw": "\t".join(parts[3:])}
                out.append(ScoreEntry(handle=handle, bbs_short_name=bbs_name,
                                      score=score, date=date, extra=extra))
    except Exception:
        return []
    out.sort(key=lambda e: e.score, reverse=not ascending)
    return out[:limit]


def save_local(handle: str, score: int, extra: dict[str, Any] | None = None,
               max_top: int = 10, ascending: bool = False,
               *, game: str | None = None) -> list[ScoreEntry]:
    """Inserta un score en el fichero local y devuelve el top actualizado."""
    from datetime import date as _date
    game, scores_dir = _resolve_caller(game)
    path = _scores_path(game, scores_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = top_local(limit=10_000, ascending=ascending, game=game)
    existing.append(ScoreEntry(
        handle=handle,
        bbs_short_name=get_config().bbs_short_name,
        score=score,
        date=_date.today().isoformat(),
        extra=extra or {},
    ))
    existing.sort(key=lambda e: e.score, reverse=not ascending)
    existing = existing[:max_top]
    try:
        with open(path, "w", encoding="utf-8") as f:
            for e in existing:
                f.write(f"{e.handle}\t{e.score}\t{e.date}\n")
    except Exception:
        pass
    return existing


def entra_en_top_local(score: int, max_top: int = 10, ascending: bool = False,
                       *, game: str | None = None) -> bool:
    top = top_local(limit=max_top, ascending=ascending, game=game)
    if len(top) < max_top:
        return True
    return (score < top[-1].score) if ascending else (score > top[-1].score)


# ---------- red ----------

def _request(method: str, path: str, body: dict | None = None) -> Any:
    cfg = get_config()
    url = cfg.server_url + path
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cfg.api_token:
        headers["Authorization"] = f"Bearer {cfg.api_token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=cfg.timeout_seconds) as r:
            payload = r.read().decode("utf-8")
            _mark_online(True)
            return json.loads(payload) if payload else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
        _mark_online(False)
        raise


def _mark_online(ok: bool):
    _online_state["last_check_ok"] = ok
    _online_state["last_check_at"] = time.time()


# ---------- pending queue ----------

def _enqueue_pending(payload: dict):
    try:
        with open(PENDING_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


def _drain_pending():
    if not os.path.exists(PENDING_PATH):
        return
    if not get_config().online_enabled:
        return
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
    except Exception:
        return
    remaining = []
    for ln in lines:
        try:
            payload = json.loads(ln)
        except json.JSONDecodeError:
            continue
        try:
            _request("POST", "/api/scores", payload)
        except Exception:
            remaining.append(ln)
    try:
        if remaining:
            with open(PENDING_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(remaining) + "\n")
        else:
            os.unlink(PENDING_PATH)
    except Exception:
        pass


# ---------- API publica ----------

def submit(handle: str, score: int, extra: dict[str, Any] | None = None,
           *, game: str | None = None) -> bool:
    """Sube el score al server en un thread daemon. Si no hay red o no hay
    config, escribe a pending. Nunca lanza. Devuelve True si quedo entregado."""
    game, _ = _resolve_caller(game)
    cfg = get_config()
    payload: dict[str, Any] = {"game": game, "handle": handle.upper(), "score": int(score)}
    if extra:
        payload["extra"] = extra
    if not cfg.online_enabled:
        return False

    result = {"ok": False}

    def _worker():
        try:
            _drain_pending()
            _request("POST", "/api/scores", payload)
            result["ok"] = True
        except Exception:
            _enqueue_pending(payload)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=cfg.timeout_seconds + 0.5)
    return result["ok"]


def _fetch_top(game: str, scope: str, limit: int, ascending: bool) -> list[ScoreEntry]:
    cfg = get_config()
    if not cfg.online_enabled:
        return []
    params = {"scope": scope, "limit": str(limit), "order": "asc" if ascending else "desc"}
    if scope == "bbs":
        params["bbs"] = cfg.bbs_short_name
    qs = urllib.parse.urlencode(params)
    payload = _request("GET", f"/api/scores/{game}?{qs}")
    out = []
    for item in payload or []:
        out.append(ScoreEntry(
            handle=item["handle"],
            bbs_short_name=item["bbs_short_name"],
            score=item["score"],
            date=(item.get("created_at") or "")[:10],
            extra=item.get("extra") or {},
        ))
    return out


def _cached_top(game: str, scope: str, limit: int, ascending: bool) -> list[ScoreEntry]:
    cfg = get_config()
    key = (game, scope, limit, ascending)
    now = time.time()
    cached = _top_cache.get(key)
    if cached and (now - cached[0]) < cfg.cache_seconds:
        return cached[1]
    try:
        data = _fetch_top(game, scope, limit, ascending)
        _top_cache[key] = (now, data)
        return data
    except Exception:
        return []


def top_global(limit: int = 10, ascending: bool = False, *, game: str | None = None) -> list[ScoreEntry]:
    """Top mundial via red. Cache cache_seconds. Si falla, devuelve top local."""
    game, _ = _resolve_caller(game)
    data = _cached_top(game, "global", limit, ascending)
    if data:
        return data
    return top_local(limit, ascending=ascending, game=game)


def top_bbs(limit: int = 10, ascending: bool = False, *, game: str | None = None) -> list[ScoreEntry]:
    """Top de tu BBS via red. Si falla, devuelve top local."""
    game, _ = _resolve_caller(game)
    data = _cached_top(game, "bbs", limit, ascending)
    if data:
        return data
    return top_local(limit, ascending=ascending, game=game)


def get_top_for_mode(modo: str, limit: int = 10, ascending: bool = False,
                     *, game: str | None = None) -> tuple[list[ScoreEntry], str, bool]:
    """Helper para el toggle L/G de las pantalla_final.
    Devuelve (scores, etiqueta, online_real). Si modo=global y no hay red,
    cae a local con etiqueta indicandolo."""
    game, _ = _resolve_caller(game)
    if modo == "global":
        scores = top_global(limit, ascending=ascending, game=game)
        online = is_online()
        if online:
            return scores, " TOP GLOBAL ", True
        return top_local(limit, ascending=ascending, game=game), " TOP GLOBAL (sin conexion) ", False
    return top_local(limit, ascending=ascending, game=game), " TOP LOCAL ", True


def invalidate_cache(game: str | None = None):
    """Borra cache de tops para forzar refresh."""
    if game is None:
        _top_cache.clear()
    else:
        for k in list(_top_cache.keys()):
            if k[0] == game.lower():
                del _top_cache[k]


def ping() -> bool:
    cfg = get_config()
    if not cfg.online_enabled:
        _mark_online(False)
        return False
    try:
        _request("GET", "/api/health")
        return True
    except Exception:
        return False


# Self-test
if __name__ == "__main__":
    cfg = get_config()
    print(f"Config: server={cfg.server_url or '(none)'} bbs={cfg.bbs_short_name}")
    print(f"online_enabled={cfg.online_enabled}, ping={ping()}")
    print(f"Local dino top: {top_local(game='dino')}")
