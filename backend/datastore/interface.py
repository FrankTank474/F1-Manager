from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from ..models.user import User, UserCreate, UserUpdate, UserInDB


class DatastoreInterface(ABC):
    """Abstract interface for data storage operations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the datastore connection/setup."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the datastore connection."""
        pass

    # User operations
    @abstractmethod
    async def create_user(self, email: str, username: str, password_hash: str) -> User:
        """Create a new user. Raises ValueError if email/username exists."""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID (includes password hash)."""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email address (includes password hash)."""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username (includes password hash)."""
        pass

    @abstractmethod
    async def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """Update user data."""
        pass

    @abstractmethod
    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user's password hash."""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        pass

    @abstractmethod
    async def record_login(self, user_id: str) -> None:
        """Record a user login event (update last_login)."""
        pass

    # Token blacklist (for logout)
    @abstractmethod
    async def blacklist_token(self, token_jti: str, expires_at: datetime) -> None:
        """Add a JWT token ID to the blacklist."""
        pass

    @abstractmethod
    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if a token is blacklisted."""
        pass

    @abstractmethod
    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from blacklist. Returns count removed."""
        pass
