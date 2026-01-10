import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .interface import DatastoreInterface
from ..models.user import User, UserUpdate, UserInDB


class LocalJSONDatastore(DatastoreInterface):
    """Local JSON file-based datastore for development."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.users_file = data_dir / "users.json"
        self.tokens_file = data_dir / "blacklisted_tokens.json"
        self._users: Dict[str, Dict[str, Any]] = {}
        self._tokens: Dict[str, str] = {}  # jti -> expires_at ISO string
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the datastore, creating files if needed."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        await self._load_data()

    async def close(self) -> None:
        """Save data and close."""
        await self._save_users()
        await self._save_tokens()

    async def _load_data(self) -> None:
        """Load data from JSON files."""
        if self.users_file.exists():
            with open(self.users_file, "r") as f:
                self._users = json.load(f)
        if self.tokens_file.exists():
            with open(self.tokens_file, "r") as f:
                self._tokens = json.load(f)

    async def _save_users(self) -> None:
        """Save users to JSON file."""
        async with self._lock:
            with open(self.users_file, "w") as f:
                json.dump(self._users, f, indent=2, default=str)

    async def _save_tokens(self) -> None:
        """Save token blacklist to JSON file."""
        async with self._lock:
            with open(self.tokens_file, "w") as f:
                json.dump(self._tokens, f, indent=2)

    async def create_user(self, email: str, username: str, password_hash: str) -> User:
        """Create a new user."""
        # Check for existing email/username
        for u in self._users.values():
            if u["email"].lower() == email.lower():
                raise ValueError("Email already registered")
            if u["username"].lower() == username.lower():
                raise ValueError("Username already taken")

        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        user_data = {
            "id": user_id,
            "email": email,
            "username": username,
            "password_hash": password_hash,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "is_active": True,
        }

        self._users[user_id] = user_data
        await self._save_users()

        return User(
            id=user_id,
            email=email,
            username=username,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            last_login=None,
            is_active=True,
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        user_data = self._users.get(user_id)
        if not user_data:
            return None
        return self._to_user_in_db(user_data)

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        for user_data in self._users.values():
            if user_data["email"].lower() == email.lower():
                return self._to_user_in_db(user_data)
        return None

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username."""
        for user_data in self._users.values():
            if user_data["username"].lower() == username.lower():
                return self._to_user_in_db(user_data)
        return None

    async def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """Update user data."""
        if user_id not in self._users:
            return None

        user_data = self._users[user_id]

        if update.email is not None:
            # Check email not taken by another user
            for uid, u in self._users.items():
                if uid != user_id and u["email"].lower() == update.email.lower():
                    raise ValueError("Email already registered")
            user_data["email"] = update.email

        if update.username is not None:
            # Check username not taken by another user
            for uid, u in self._users.items():
                if uid != user_id and u["username"].lower() == update.username.lower():
                    raise ValueError("Username already taken")
            user_data["username"] = update.username

        user_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._save_users()

        return self._to_user(user_data)

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user's password."""
        if user_id not in self._users:
            return False

        self._users[user_id]["password_hash"] = password_hash
        self._users[user_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._save_users()
        return True

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        if user_id not in self._users:
            return False

        del self._users[user_id]
        await self._save_users()
        return True

    async def record_login(self, user_id: str) -> None:
        """Record login timestamp."""
        if user_id in self._users:
            self._users[user_id]["last_login"] = datetime.now(timezone.utc).isoformat()
            await self._save_users()

    async def blacklist_token(self, token_jti: str, expires_at: datetime) -> None:
        """Add token to blacklist."""
        self._tokens[token_jti] = expires_at.isoformat()
        await self._save_tokens()

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if token is blacklisted."""
        return token_jti in self._tokens

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from blacklist."""
        now = datetime.now(timezone.utc)
        expired = []

        for jti, expires_str in self._tokens.items():
            expires_at = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
            if expires_at < now:
                expired.append(jti)

        for jti in expired:
            del self._tokens[jti]

        if expired:
            await self._save_tokens()

        return len(expired)

    def _to_user(self, data: Dict[str, Any]) -> User:
        """Convert dict to User model."""
        return User(
            id=data["id"],
            email=data["email"],
            username=data["username"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            last_login=(
                datetime.fromisoformat(data["last_login"].replace("Z", "+00:00"))
                if data["last_login"]
                else None
            ),
            is_active=data["is_active"],
        )

    def _to_user_in_db(self, data: Dict[str, Any]) -> UserInDB:
        """Convert dict to UserInDB model."""
        return UserInDB(
            id=data["id"],
            email=data["email"],
            username=data["username"],
            password_hash=data["password_hash"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            last_login=(
                datetime.fromisoformat(data["last_login"].replace("Z", "+00:00"))
                if data["last_login"]
                else None
            ),
            is_active=data["is_active"],
        )
