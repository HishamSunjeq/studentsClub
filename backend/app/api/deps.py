import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

DBSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)],
    db: DBSession,
) -> User:
    if not credentials:
        raise UnauthorizedError("Missing Authorization header")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Access token has expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Invalid access token")

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id_str = payload.get("sub")
    if not isinstance(user_id_str, str):
        raise UnauthorizedError("Malformed token")

    user = await db.get(User, uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
