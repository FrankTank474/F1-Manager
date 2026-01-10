from datetime import datetime, timezone
from typing import Optional, Tuple

from ..config import settings
from ..datastore.interface import DatastoreInterface
from ..models.user import User, UserCreate
from ..models.auth import LoginResponse, RefreshResponse
from ..security.password import hash_password, verify_password
from ..security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_token_expiry,
)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, datastore: DatastoreInterface):
        self.datastore = datastore

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        # Hash the password
        password_hash = hash_password(user_data.password)

        # Create the user in datastore
        user = await self.datastore.create_user(
            email=user_data.email,
            username=user_data.username,
            password_hash=password_hash,
        )

        return user

    async def authenticate(
        self, email: str, password: str
    ) -> Optional[LoginResponse]:
        """Authenticate user and return tokens."""
        # Get user by email
        user = await self.datastore.get_user_by_email(email)
        if not user:
            return None

        # Check if user is active
        if not user.is_active:
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            return None

        # Record login
        await self.datastore.record_login(user.id)

        # Create tokens
        access_token, access_jti = create_access_token(user.id)
        refresh_token, refresh_jti = create_refresh_token(user.id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_access_token(
        self, refresh_token: str
    ) -> Optional[RefreshResponse]:
        """Refresh access token using refresh token."""
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload:
            return None

        # Check token type
        if payload.get("type") != "refresh":
            return None

        # Check if token is blacklisted
        jti = payload.get("jti")
        if jti and await self.datastore.is_token_blacklisted(jti):
            return None

        # Get user
        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self.datastore.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        # Create new access token
        access_token, _ = create_access_token(user_id)

        return RefreshResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, access_token: str) -> bool:
        """Logout user by blacklisting their token."""
        payload = decode_token(access_token)
        if not payload:
            return False

        jti = payload.get("jti")
        if not jti:
            return False

        # Get token expiry
        expiry = get_token_expiry(access_token)
        if not expiry:
            expiry = datetime.now(timezone.utc)

        # Blacklist the token
        await self.datastore.blacklist_token(jti, expiry)

        return True

    async def validate_token(self, token: str) -> Optional[str]:
        """Validate access token and return user_id if valid."""
        payload = decode_token(token)
        if not payload:
            return None

        # Check token type
        if payload.get("type") != "access":
            return None

        # Check if blacklisted
        jti = payload.get("jti")
        if jti and await self.datastore.is_token_blacklisted(jti):
            return None

        return payload.get("sub")
