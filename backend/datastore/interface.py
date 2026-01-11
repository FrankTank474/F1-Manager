from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List

from ..models.user import User, UserCreate, UserUpdate, UserInDB
from ..models.game import Game, GameInvite, GameStatus, InviteStatus


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

    # Game operations
    @abstractmethod
    async def create_game(self, game: Game) -> Game:
        """Create a new game."""
        pass

    @abstractmethod
    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Get game by ID."""
        pass

    @abstractmethod
    async def get_games_for_user(self, user_id: str) -> List[Game]:
        """Get all games where user is a player or creator."""
        pass

    @abstractmethod
    async def update_game(self, game: Game) -> Optional[Game]:
        """Update a game."""
        pass

    @abstractmethod
    async def delete_game(self, game_id: str) -> bool:
        """Delete a game."""
        pass

    # Game invite operations
    @abstractmethod
    async def create_invite(self, invite: GameInvite) -> GameInvite:
        """Create a game invite."""
        pass

    @abstractmethod
    async def get_invite_by_id(self, invite_id: str) -> Optional[GameInvite]:
        """Get invite by ID."""
        pass

    @abstractmethod
    async def get_pending_invites_for_game(self, game_id: str) -> List[GameInvite]:
        """Get all pending invites for a game."""
        pass

    @abstractmethod
    async def get_pending_invites_for_user(self, user_id: str) -> List[GameInvite]:
        """Get all pending invites received by a user."""
        pass

    @abstractmethod
    async def update_invite(self, invite: GameInvite) -> Optional[GameInvite]:
        """Update an invite."""
        pass

    @abstractmethod
    async def search_users_by_username(self, query: str, exclude_user_id: str, limit: int = 10) -> List[User]:
        """Search users by username prefix for invite suggestions."""
        pass
