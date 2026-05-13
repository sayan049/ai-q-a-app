# backend/tests/test_dependencies.py

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.security import HTTPAuthorizationCredentials


@pytest.mark.asyncio
async def test_get_current_user_success(test_user, mock_db):
    from app.dependencies import get_current_user
    from app.core.auth import create_access_token

    token = create_access_token(test_user.id, test_user.email)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_current_user(credentials)
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_current_user_no_credentials(mock_db):
    from app.dependencies import get_current_user
    from app.core.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        await get_current_user(None)


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_db):
    from app.dependencies import get_current_user
    from app.core.exceptions import AuthenticationError

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid.token.here"
    )

    with pytest.raises(AuthenticationError):
        await get_current_user(credentials)


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user(mock_db):
    from app.dependencies import get_current_user
    from app.core.auth import create_access_token
    from app.core.exceptions import AuthenticationError

    token = create_access_token("nonexistent-user-id", "ghost@example.com")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(AuthenticationError):
        await get_current_user(credentials)


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(mock_db):
    from app.dependencies import get_current_user
    from app.core.auth import create_access_token, hash_password
    from app.core.exceptions import AuthenticationError
    from app.models.user import User

    inactive_user = User(
        id="inactive-user-id",
        email="inactive@example.com",
        username="inactiveuser",
        hashed_password=hash_password("Pass1234"),
        is_active=False,
    )
    await inactive_user.insert()

    token = create_access_token("inactive-user-id", "inactive@example.com")
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(AuthenticationError):
        await get_current_user(credentials)


@pytest.mark.asyncio
async def test_get_optional_user_returns_none_no_creds(mock_db):
    from app.dependencies import get_optional_user

    result = await get_optional_user(None)
    assert result is None


@pytest.mark.asyncio
async def test_get_optional_user_returns_user(test_user, mock_db):
    from app.dependencies import get_optional_user
    from app.core.auth import create_access_token

    token = create_access_token(test_user.id, test_user.email)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    user = await get_optional_user(credentials)
    assert user is not None
    assert user.id == test_user.id