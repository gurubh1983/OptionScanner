"""Auth: register, login with DB. JWT."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.services.auth_service import AuthService
from app.api.v1.deps import get_auth_service

router = APIRouter()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(
    data: UserCreate,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register and return JWT. DB-backed."""
    try:
        token, user_id = await auth.register(data.email, data.password, data.full_name)
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Login and return JWT."""
    try:
        token, _ = await auth.login(data.email, data.password)
        return TokenResponse(access_token=token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
