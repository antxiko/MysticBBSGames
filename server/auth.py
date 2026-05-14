"""Bearer token auth para FastAPI."""
from fastapi import Header, HTTPException, status
from typing import Annotated

from . import db


async def verify_token(authorization: Annotated[str | None, Header()] = None):
    """Dependency: extrae el Bearer token y devuelve la BBS asociada.
    Lanza 401 si no hay token o no es valido / la BBS esta desactivada."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header (expected 'Bearer <token>')",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = parts[1].strip()
    bbs = db.find_bbs_by_token(token)
    if bbs is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or disabled BBS token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return bbs
