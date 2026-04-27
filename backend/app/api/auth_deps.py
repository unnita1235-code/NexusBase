"""
NexusBase — JWT Authentication Dependencies.

Validates Bearer tokens from the Authorization header using the
shared AUTH_SECRET. Used by protected endpoints like /v1/query.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("rag.api.auth")

security = HTTPBearer()


class User(BaseModel):
    email: str
    role: str


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    Validates the JWT token from the Authorization header.
    Expects a token signed with AUTH_SECRET (HS256).
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.auth_secret, algorithms=["HS256"]
        )

        email = payload.get("email")
        role = payload.get("role", "user")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing email",
            )

        return User(email=email, role=role)

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

