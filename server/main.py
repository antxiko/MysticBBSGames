"""BBS Scores - servidor FastAPI.

Despliega con: uvicorn server.main:app --host 127.0.0.1 --port 8765
"""
import json
import re
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from . import db
from .auth import verify_token
from .admin_web import router as admin_router
from .public_web import router as public_router

# El server no conoce los juegos. El orden lo decide el cliente con ?order=
# (default 'desc'). El nombre de juego es un string opaco validado por regex.
VALID_GAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")
VALID_HANDLE_RE = re.compile(r"^[A-Z0-9]{1,10}$")


def _validate_game(game: str) -> str:
    if not VALID_GAME_RE.match(game):
        raise HTTPException(status_code=400, detail="invalid game name")
    return game


def _validate_handle(handle: str) -> str:
    h = handle.upper()
    if not VALID_HANDLE_RE.match(h):
        raise HTTPException(status_code=400, detail="invalid handle (1-10 chars A-Z 0-9)")
    return h


app = FastAPI(
    title="BBS Scores",
    description="Scoreboard global compartido entre BBSes para los juegos del repo MysticBBSGames.",
    version="1.0.0",
)


app.include_router(admin_router)
app.include_router(public_router)


@app.on_event("startup")
async def _startup():
    db.init_db()


# ---------- modelos ----------

class ScoreIn(BaseModel):
    game: str = Field(..., max_length=32)
    handle: str = Field(..., max_length=10)
    score: int
    extra: dict[str, Any] | None = None

    @field_validator("game")
    @classmethod
    def _game(cls, v: str) -> str:
        if not VALID_GAME_RE.match(v):
            raise ValueError("invalid game name")
        return v

    @field_validator("handle")
    @classmethod
    def _handle(cls, v: str) -> str:
        u = v.upper()
        if not VALID_HANDLE_RE.match(u):
            raise ValueError("invalid handle (1-10 chars A-Z 0-9)")
        return u


class ScoreOut(BaseModel):
    handle: str
    bbs_short_name: str
    score: int
    extra: dict[str, Any] | None = None
    created_at: str


class BBSOut(BaseModel):
    short_name: str
    full_name: str | None = None


# ---------- endpoints ----------

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/scores", status_code=201)
async def post_score(score: ScoreIn, bbs=Depends(verify_token)):
    extra_json = json.dumps(score.extra, separators=(",", ":")) if score.extra else None
    score_id = db.insert_score(
        game=score.game,
        bbs_id=bbs["id"],
        handle=score.handle,
        score=score.score,
        extra=extra_json,
    )
    return {"id": score_id, "bbs": bbs["short_name"]}


@app.get("/api/scores/{game}", response_model=list[ScoreOut])
async def get_scores(
    game: str,
    scope: Annotated[str, Query(pattern="^(global|bbs)$")] = "global",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "desc",
    period: Annotated[str, Query(pattern="^(all|week|month)$")] = "all",
    bbs: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
):
    game = _validate_game(game)
    ascending = (order == "asc")
    if scope == "bbs":
        if not bbs:
            raise HTTPException(status_code=400, detail="scope=bbs requires bbs param")
        rows = db.top_scores_bbs(game, bbs, limit, ascending=ascending, period=period)
    else:
        rows = db.top_scores_global(game, limit, ascending=ascending, period=period)
    return [
        ScoreOut(
            handle=r["handle"],
            bbs_short_name=r["bbs_short_name"],
            score=r["score"],
            extra=json.loads(r["extra"]) if r["extra"] else None,
            created_at=r["created_at"],
        )
        for r in rows
    ]


@app.get("/api/bbses", response_model=list[BBSOut])
async def get_bbses():
    rows = db.list_bbses()
    return [
        BBSOut(short_name=r["short_name"], full_name=r["full_name"])
        for r in rows if r["enabled"]
    ]
