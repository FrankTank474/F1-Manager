import uuid
from datetime import datetime, timezone
from typing import Optional

import asyncpg

from .interface import DatastoreInterface
from ..models.user import User, UserUpdate, UserInDB


class PostgresDatastore(DatastoreInterface):
    """PostgreSQL datastore for production."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Create connection pool and ensure tables exist."""
        self._pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10,
        )
        await self._create_tables()

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()

    async def _create_tables(self) -> None:
        """Create tables if they don't exist."""
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    last_login TIMESTAMPTZ,
                    is_active BOOLEAN DEFAULT TRUE
                );

                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

                CREATE TABLE IF NOT EXISTS token_blacklist (
                    jti VARCHAR(255) PRIMARY KEY,
                    expires_at TIMESTAMPTZ NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tokens_expires ON token_blacklist(expires_at);
            """)

    async def create_user(self, email: str, username: str, password_hash: str) -> User:
        """Create a new user."""
        async with self._pool.acquire() as conn:
            try:
                row = await conn.fetchrow(
                    """
                    INSERT INTO users (id, email, username, password_hash)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id, email, username, created_at, updated_at, last_login, is_active
                    """,
                    uuid.uuid4(),
                    email,
                    username,
                    password_hash,
                )
                return User(
                    id=str(row["id"]),
                    email=row["email"],
                    username=row["username"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    last_login=row["last_login"],
                    is_active=row["is_active"],
                )
            except asyncpg.UniqueViolationError as e:
                if "email" in str(e):
                    raise ValueError("Email already registered")
                raise ValueError("Username already taken")

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, password_hash, created_at, updated_at, last_login, is_active
                FROM users WHERE id = $1
                """,
                uuid.UUID(user_id),
            )
            if not row:
                return None
            return self._row_to_user_in_db(row)

    async def get_user_by_email(self, email: str) -> Optional[UserInDB]:
        """Get user by email."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, password_hash, created_at, updated_at, last_login, is_active
                FROM users WHERE LOWER(email) = LOWER($1)
                """,
                email,
            )
            if not row:
                return None
            return self._row_to_user_in_db(row)

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, password_hash, created_at, updated_at, last_login, is_active
                FROM users WHERE LOWER(username) = LOWER($1)
                """,
                username,
            )
            if not row:
                return None
            return self._row_to_user_in_db(row)

    async def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """Update user data."""
        async with self._pool.acquire() as conn:
            # Build update query dynamically
            updates = []
            values = []
            param_num = 1

            if update.email is not None:
                updates.append(f"email = ${param_num}")
                values.append(update.email)
                param_num += 1

            if update.username is not None:
                updates.append(f"username = ${param_num}")
                values.append(update.username)
                param_num += 1

            if not updates:
                # Nothing to update, fetch and return current user
                row = await conn.fetchrow(
                    """
                    SELECT id, email, username, created_at, updated_at, last_login, is_active
                    FROM users WHERE id = $1
                    """,
                    uuid.UUID(user_id),
                )
                if not row:
                    return None
                return self._row_to_user(row)

            updates.append(f"updated_at = ${param_num}")
            values.append(datetime.now(timezone.utc))
            param_num += 1

            values.append(uuid.UUID(user_id))

            try:
                row = await conn.fetchrow(
                    f"""
                    UPDATE users SET {', '.join(updates)}
                    WHERE id = ${param_num}
                    RETURNING id, email, username, created_at, updated_at, last_login, is_active
                    """,
                    *values,
                )
                if not row:
                    return None
                return self._row_to_user(row)
            except asyncpg.UniqueViolationError as e:
                if "email" in str(e):
                    raise ValueError("Email already registered")
                raise ValueError("Username already taken")

    async def update_password(self, user_id: str, password_hash: str) -> bool:
        """Update user's password."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE users SET password_hash = $1, updated_at = $2
                WHERE id = $3
                """,
                password_hash,
                datetime.now(timezone.utc),
                uuid.UUID(user_id),
            )
            return result == "UPDATE 1"

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM users WHERE id = $1",
                uuid.UUID(user_id),
            )
            return result == "DELETE 1"

    async def record_login(self, user_id: str) -> None:
        """Record login timestamp."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = $1 WHERE id = $2",
                datetime.now(timezone.utc),
                uuid.UUID(user_id),
            )

    async def blacklist_token(self, token_jti: str, expires_at: datetime) -> None:
        """Add token to blacklist."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO token_blacklist (jti, expires_at)
                VALUES ($1, $2)
                ON CONFLICT (jti) DO NOTHING
                """,
                token_jti,
                expires_at,
            )

    async def is_token_blacklisted(self, token_jti: str) -> bool:
        """Check if token is blacklisted."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM token_blacklist WHERE jti = $1",
                token_jti,
            )
            return row is not None

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from blacklist."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM token_blacklist WHERE expires_at < $1",
                datetime.now(timezone.utc),
            )
            # Result is like "DELETE 5"
            try:
                return int(result.split()[1])
            except (IndexError, ValueError):
                return 0

    def _row_to_user(self, row: asyncpg.Record) -> User:
        """Convert database row to User model."""
        return User(
            id=str(row["id"]),
            email=row["email"],
            username=row["username"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login=row["last_login"],
            is_active=row["is_active"],
        )

    def _row_to_user_in_db(self, row: asyncpg.Record) -> UserInDB:
        """Convert database row to UserInDB model."""
        return UserInDB(
            id=str(row["id"]),
            email=row["email"],
            username=row["username"],
            password_hash=row["password_hash"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_login=row["last_login"],
            is_active=row["is_active"],
        )
