"""Tests for AuthService with in-memory DB pattern (use real DB in integration)."""

import uuid
import pytest
from unittest.mock import AsyncMock

from app.services.auth_service import AuthService
from app.repositories.user_repository import UserRepository
from app.core.security import get_password_hash


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def user_repo(mock_session):
    return UserRepository(mock_session)


@pytest.fixture
def auth_service(user_repo):
    return AuthService(user_repo)


@pytest.mark.asyncio
async def test_register_creates_user(auth_service, user_repo):
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.create = AsyncMock(return_value=type("User", (), {"id": uuid.uuid4()})())
    token, uid = await auth_service.register("test@example.com", "password123", "Test User")
    assert token
    assert uid
    user_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_raises_if_email_exists(auth_service, user_repo):
    user_repo.get_by_email = AsyncMock(return_value=type("User", (), {"id": uuid.uuid4()})())
    with pytest.raises(ValueError, match="already registered"):
        await auth_service.register("test@example.com", "password123", None)


@pytest.mark.asyncio
async def test_login_returns_token(auth_service, user_repo):
    from app.core.security import get_password_hash
    hashed = get_password_hash("password123")
    user = type("User", (), {"id": uuid.uuid4(), "hashed_password": hashed, "is_active": True})()
    user_repo.get_by_email = AsyncMock(return_value=user)
    token, uid = await auth_service.login("test@example.com", "password123")
    assert token
    assert uid == user.id


@pytest.mark.asyncio
async def test_login_raises_invalid(auth_service, user_repo):
    user_repo.get_by_email = AsyncMock(return_value=None)
    with pytest.raises(ValueError, match="Invalid"):
        await auth_service.login("test@example.com", "wrong")
