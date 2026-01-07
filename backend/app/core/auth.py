"""
Authentication dependencies and utilities.
"""
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.db.database import get_session
from app.db.models import User
from app.core.security import decode_token
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.config import settings


# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """
    Get the current authenticated user from JWT token.

    Args:
        credentials: JWT bearer token from Authorization header
        db: Database session

    Returns:
        Current user object

    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    if not credentials:
        raise AuthenticationError("Not authenticated")

    try:
        # Decode and validate token
        token_data = decode_token(credentials.credentials)

        # Get user from database
        result = await db.execute(
            select(User).where(User.id == token_data.sub)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise AuthenticationError("User not found")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        return user

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Could not validate credentials: {str(e)}")


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify the current user is active.

    Args:
        current_user: Current authenticated user

    Returns:
        Active user object

    Raises:
        AuthorizationError: If user is not active
    """
    if not current_user.is_active:
        raise AuthorizationError("Inactive user")
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Verify the current user is a superuser.

    Args:
        current_user: Current authenticated user

    Returns:
        Superuser object

    Raises:
        AuthorizationError: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise AuthorizationError("Not enough permissions")
    return current_user


async def get_optional_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise return None.

    This is useful for endpoints that can work both authenticated and unauthenticated.

    Args:
        credentials: Optional JWT bearer token
        db: Database session

    Returns:
        Current user or None
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None


async def validate_github_token(access_token: str) -> dict:
    """
    Validate a GitHub OAuth access token and get user info.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        GitHub user information

    Raises:
        AuthenticationError: If token is invalid
    """
    async with httpx.AsyncClient() as client:
        # Get user info from GitHub
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code != 200:
            raise AuthenticationError("Invalid GitHub token")

        user_data = response.json()

        # Get user email if not public
        if not user_data.get("email"):
            email_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )

            if email_response.status_code == 200:
                emails = email_response.json()
                # Get primary verified email
                for email in emails:
                    if email.get("primary") and email.get("verified"):
                        user_data["email"] = email.get("email")
                        break

        return user_data


class RateLimiter:
    """
    Thread-safe rate limiter with Redis support for distributed systems.
    Falls back to in-memory for development if Redis is unavailable.
    """

    def __init__(self, requests_per_minute: int = 10, redis_client=None):
        self.requests_per_minute = requests_per_minute
        self.redis = redis_client
        self.requests = {}  # Dict[str, List[datetime]] - fallback for no Redis

    async def check_rate_limit(self, key: str) -> bool:
        """
        Check if a request should be rate limited.

        Args:
            key: Unique key for rate limiting (e.g., IP address, user ID)

        Returns:
            True if request is allowed, False if rate limited
        """
        if self.redis:
            return await self._check_redis_rate_limit(key)
        else:
            return await self._check_memory_rate_limit(key)

    async def _check_redis_rate_limit(self, key: str) -> bool:
        """Redis-based rate limiting (production)."""
        from datetime import datetime

        now = datetime.utcnow().timestamp()
        minute_ago = now - 60

        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        rate_key = f"rate:{key}"

        # Remove requests older than 1 minute
        pipe.zremrangebyscore(rate_key, 0, minute_ago)
        # Add current request
        pipe.zadd(rate_key, {str(now): now})
        # Count requests in last minute
        pipe.zcard(rate_key)
        # Set expiry to auto-cleanup
        pipe.expire(rate_key, 60)

        results = await pipe.execute()
        count = results[2]  # zcard result

        return count <= self.requests_per_minute

    async def _check_memory_rate_limit(self, key: str) -> bool:
        """
        In-memory rate limiting (development fallback).

        WARNING: Not thread-safe, has memory leak, and doesn't work across
        multiple backend instances. Use Redis in production.
        """
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        if key in self.requests:
            self.requests[key] = [
                req_time for req_time in self.requests[key] if req_time > minute_ago
            ]

        # Check rate limit
        if key not in self.requests:
            self.requests[key] = []

        if len(self.requests[key]) >= self.requests_per_minute:
            return False

        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance (Redis client will be injected if available)
auth_rate_limiter = RateLimiter(requests_per_minute=10)


async def check_auth_rate_limit(request: Request) -> None:
    """
    Check rate limit for authentication endpoints.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # Use IP address as rate limit key
    client_ip = request.client.host if request.client else "unknown"

    is_allowed = await auth_rate_limiter.check_rate_limit(client_ip)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
        )