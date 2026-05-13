# backend/app/dependencies.py

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from typing import Optional
from app.core.auth import verify_access_token
from app.models.user import User
from app.core.exceptions import AuthenticationError

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """
    Dependency: extract and verify JWT, return current user.
    Raises 401 if token is invalid or user not found.
    """
    if not credentials:
        raise AuthenticationError("Authorization header missing")

    token = credentials.credentials

    try:
        payload = verify_access_token(token)
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    user = await User.find_one(User.id == user_id)
    if not user:
        raise AuthenticationError("User not found")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Optional auth — returns None if not authenticated."""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except Exception:
        return None