"""Auth service: register, login with DB. Returns JWT."""

from __future__ import annotations

import uuid

from app.core.security import create_access_token, get_password_hash, verify_password
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def register(self, email: str, password: str, full_name: str | None) -> tuple[str, uuid.UUID]:
        """Create user and return (access_token, user_id). Raises ValueError if email exists."""
        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")
        user = await self._user_repo.create(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
        )
        token = create_access_token(subject=str(user.id))
        return token, user.id

    async def login(self, email: str, password: str) -> tuple[str, uuid.UUID]:
        """Validate credentials and return (access_token, user_id). Raises ValueError if invalid."""
        user = await self._user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("Account disabled")
        token = create_access_token(subject=str(user.id))
        return token, user.id
