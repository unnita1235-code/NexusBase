from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from asyncpg import Pool

from app.domain.users import UserCreate, UserResponse, Token
from app.services.auth_service import register_user, authenticate_user
from app.core.security import create_access_token
from app.infrastructure.database import get_pool

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate, pool: Pool = Depends(get_pool)):
    return await register_user(user_in, pool)

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), pool: Pool = Depends(get_pool)):
    user = await authenticate_user(form_data.username, form_data.password, pool)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(subject=user.email, role=user.role)
    return {"access_token": access_token, "token_type": "bearer"}
