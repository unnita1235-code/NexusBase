from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from asyncpg import Pool

from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.domain.users import UserCreate, UserInDB, UserResponse, Token
from app.infrastructure.database import get_pool

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/login")

async def get_user_by_email(email: str, pool: Pool) -> UserInDB | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE email = $1", email)
        if row:
            return UserInDB(**dict(row))
    return None

async def register_user(user_in: UserCreate, pool: Pool = Depends(get_pool)) -> UserResponse:
    existing_user = await get_user_by_email(user_in.email, pool)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_in.password)
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO users (email, hashed_password, role)
            VALUES ($1, $2, $3)
            RETURNING id, email, role, created_at
        ''', user_in.email, hashed_password, user_in.role.value)
        
    return UserResponse(**dict(row))

async def authenticate_user(email: str, password: str, pool: Pool) -> UserInDB | None:
    user = await get_user_by_email(email, pool)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], pool: Pool = Depends(get_pool)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await get_user_by_email(email, pool)
    if user is None:
        raise credentials_exception
    return user
