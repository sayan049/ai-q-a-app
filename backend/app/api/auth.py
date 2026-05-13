# backend/app/api/auth.py

import logging
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
import httpx

from app.models.user import User
from app.models.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    MessageResponse,
)
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.rate_limiter import limiter
from app.services.cache_service import blacklist_token, is_token_blacklisted
from app.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, data: UserRegisterRequest):
    """Register a new user account."""
    # Check if email already exists
    existing = await User.find_one(User.email == data.email)
    if existing:
        raise ValidationError("Email already registered")

    # Check username
    existing_username = await User.find_one(User.username == data.username)
    if existing_username:
        raise ValidationError("Username already taken")

    # Create user
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
        is_verified=True,  # Auto-verify for simplicity
    )
    await user.insert()

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = create_refresh_token(user.id)

    logger.info(f"New user registered: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, data: UserLoginRequest):
    """Login with email and password."""
    user = await User.find_one(User.email == data.email)

    if not user:
        raise AuthenticationError("Invalid email or password")

    if not user.hashed_password:
        raise AuthenticationError("This account uses OAuth login. Please use GitHub login.")

    if not verify_password(data.password, user.hashed_password):
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = create_refresh_token(user.id)

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
async def refresh_token(request: Request, data: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    from jose import JWTError

    try:
        payload = verify_refresh_token(data.refresh_token)
    except JWTError as e:
        raise AuthenticationError(f"Invalid refresh token: {str(e)}")

    # Check if token is blacklisted
    jti = payload.get("jti", "")
    if await is_token_blacklisted(jti):
        raise AuthenticationError("Refresh token has been revoked")

    user_id = payload.get("sub")
    user = await User.find_one(User.id == user_id)
    if not user or not user.is_active:
        raise AuthenticationError("User not found or disabled")

    # Blacklist old refresh token
    await blacklist_token(jti, ttl_seconds=settings.refresh_token_expire_days * 86400)

    # Issue new tokens
    access_token = create_access_token(user.id, user.email)
    new_refresh_token, _ = create_refresh_token(user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """Logout: blacklist refresh token."""
    from jose import JWTError

    try:
        payload = verify_refresh_token(data.refresh_token)
        jti = payload.get("jti", "")
        await blacklist_token(jti, ttl_seconds=settings.refresh_token_expire_days * 86400)
    except JWTError:
        pass  # Ignore invalid tokens during logout

    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        is_active=current_user.is_active,
    )


# ── GitHub OAuth ──────────────────────────────────────────────────────────────

@router.get("/oauth/github")
async def github_oauth_redirect():
    """Redirect to GitHub OAuth authorization page."""
    if not settings.github_client_id:
        raise ValidationError("GitHub OAuth not configured")

    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        f"&redirect_uri={settings.github_redirect_uri}"
        f"&scope=user:email"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/oauth/github/callback")
@limiter.limit("10/minute")
async def github_oauth_callback(request: Request, code: str):
    """Handle GitHub OAuth callback."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise ValidationError("GitHub OAuth not configured")

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
        github_access_token = token_data.get("access_token")

        if not github_access_token:
            raise AuthenticationError("Failed to get GitHub access token")

        # Get user info from GitHub
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/json",
            },
        )
        github_user = user_response.json()

        # Get user emails
        email_response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/json",
            },
        )
        emails = email_response.json()

    # Get primary email
    email = github_user.get("email")
    if not email and emails:
        primary_emails = [e for e in emails if e.get("primary") and e.get("verified")]
        if primary_emails:
            email = primary_emails[0]["email"]
        elif emails:
            email = emails[0]["email"]

    if not email:
        raise AuthenticationError("Could not get email from GitHub account")

    github_id = str(github_user.get("id", ""))
    github_username = github_user.get("login", "")
    avatar_url = github_user.get("avatar_url", "")

    # Find or create user
    user = await User.find_one(User.email == email)

    if user:
        # Merge GitHub info into existing account
        user.github_id = github_id
        user.github_username = github_username
        if not user.avatar_url:
            user.avatar_url = avatar_url
        await user.save()
    else:
        # Create new user
        user = User(
            email=email,
            username=github_username or f"user_{github_id}",
            github_id=github_id,
            github_username=github_username,
            avatar_url=avatar_url,
            is_verified=True,
        )
        await user.insert()

    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = create_refresh_token(user.id)

    # Redirect to frontend with tokens
    frontend_url = settings.allowed_origins_list[0]
    redirect_url = (
        f"{frontend_url}/oauth-callback"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
    )
    return RedirectResponse(url=redirect_url)