from typing import Optional

from ..datastore.interface import DatastoreInterface
from ..models.user import User, UserUpdate, PasswordChange
from ..security.password import hash_password, verify_password


class UserService:
    """Service for user management operations."""

    def __init__(self, datastore: DatastoreInterface):
        self.datastore = datastore

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user = await self.datastore.get_user_by_id(user_id)
        if not user:
            return None
        # Convert UserInDB to User (strip password_hash)
        return User(
            id=user.id,
            email=user.email,
            username=user.username,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            is_active=user.is_active,
        )

    async def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """Update user profile."""
        return await self.datastore.update_user(user_id, update)

    async def change_password(
        self, user_id: str, password_change: PasswordChange
    ) -> bool:
        """Change user's password."""
        # Get user with password hash
        user = await self.datastore.get_user_by_id(user_id)
        if not user:
            return False

        # Verify current password
        if not verify_password(password_change.current_password, user.password_hash):
            raise ValueError("Current password is incorrect")

        # Hash new password
        new_hash = hash_password(password_change.new_password)

        # Update password
        return await self.datastore.update_password(user_id, new_hash)

    async def delete_user(self, user_id: str) -> bool:
        """Delete user account."""
        return await self.datastore.delete_user(user_id)
