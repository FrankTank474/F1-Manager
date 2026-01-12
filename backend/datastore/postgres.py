import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

import asyncpg

from .interface import DatastoreInterface
from ..models.user import User, UserUpdate, UserInDB
from ..models.game import Game, GameInvite, GamePlayer, GameStatus, InviteStatus

logger = logging.getLogger(__name__)


class PostgresDatastore(DatastoreInterface):
    """PostgreSQL datastore for production."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Create connection pool and ensure tables exist."""
        logger.info("Connecting to PostgreSQL database...")
        try:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
            )
            logger.info("PostgreSQL connection pool created (min=2, max=10)")
            await self._create_tables()
            logger.info("Database tables created/verified successfully")
        except asyncpg.PostgresError as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

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

                CREATE TABLE IF NOT EXISTS games (
                    id UUID PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    creator_id UUID NOT NULL REFERENCES users(id),
                    creator_username VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    players JSONB NOT NULL DEFAULT '[]',
                    max_players INTEGER NOT NULL DEFAULT 2,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    started_at TIMESTAMPTZ,
                    completed_at TIMESTAMPTZ
                );

                CREATE INDEX IF NOT EXISTS idx_games_creator ON games(creator_id);
                CREATE INDEX IF NOT EXISTS idx_games_status ON games(status);

                CREATE TABLE IF NOT EXISTS game_invites (
                    id UUID PRIMARY KEY,
                    game_id UUID NOT NULL REFERENCES games(id) ON DELETE CASCADE,
                    inviter_id UUID NOT NULL REFERENCES users(id),
                    invitee_id UUID NOT NULL REFERENCES users(id),
                    invitee_username VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    responded_at TIMESTAMPTZ
                );

                CREATE INDEX IF NOT EXISTS idx_invites_game ON game_invites(game_id);
                CREATE INDEX IF NOT EXISTS idx_invites_invitee ON game_invites(invitee_id);
                CREATE INDEX IF NOT EXISTS idx_invites_status ON game_invites(status);

                CREATE TABLE IF NOT EXISTS game_states (
                    game_id UUID PRIMARY KEY REFERENCES games(id) ON DELETE CASCADE,
                    state_data JSONB NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
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

    # Game operations
    async def create_game(self, game: Game) -> Game:
        """Create a new game."""
        players_json = json.dumps([p.model_dump() for p in game.players], default=str)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO games (id, name, creator_id, creator_username, status, players, max_players, created_at, updated_at, started_at, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                uuid.UUID(game.id),
                game.name,
                uuid.UUID(game.creator_id),
                game.creator_username,
                game.status.value,
                players_json,
                game.max_players,
                game.created_at,
                game.updated_at,
                game.started_at,
                game.completed_at,
            )
        return game

    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Get game by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM games WHERE id = $1",
                uuid.UUID(game_id),
            )
            if not row:
                return None
            return self._row_to_game(row)

    async def get_games_for_user(self, user_id: str) -> List[Game]:
        """Get all games where user is a player or creator."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM games
                WHERE creator_id = $1
                   OR players::jsonb @> $2::jsonb
                ORDER BY updated_at DESC
                """,
                uuid.UUID(user_id),
                json.dumps([{"user_id": user_id}]),
            )
            return [self._row_to_game(row) for row in rows]

    async def update_game(self, game: Game) -> Optional[Game]:
        """Update a game."""
        players_json = json.dumps([p.model_dump() for p in game.players], default=str)
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE games SET name = $1, status = $2, players = $3, updated_at = $4, started_at = $5, completed_at = $6
                WHERE id = $7
                """,
                game.name,
                game.status.value,
                players_json,
                game.updated_at,
                game.started_at,
                game.completed_at,
                uuid.UUID(game.id),
            )
            if result == "UPDATE 0":
                return None
            return game

    async def delete_game(self, game_id: str) -> bool:
        """Delete a game."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM games WHERE id = $1",
                uuid.UUID(game_id),
            )
            return result == "DELETE 1"

    # Game invite operations
    async def create_invite(self, invite: GameInvite) -> GameInvite:
        """Create a game invite."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO game_invites (id, game_id, inviter_id, invitee_id, invitee_username, status, created_at, responded_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                uuid.UUID(invite.id),
                uuid.UUID(invite.game_id),
                uuid.UUID(invite.inviter_id),
                uuid.UUID(invite.invitee_id),
                invite.invitee_username,
                invite.status.value,
                invite.created_at,
                invite.responded_at,
            )
        return invite

    async def get_invite_by_id(self, invite_id: str) -> Optional[GameInvite]:
        """Get invite by ID."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM game_invites WHERE id = $1",
                uuid.UUID(invite_id),
            )
            if not row:
                return None
            return self._row_to_invite(row)

    async def get_pending_invites_for_game(self, game_id: str) -> List[GameInvite]:
        """Get all pending invites for a game."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM game_invites WHERE game_id = $1 AND status = $2",
                uuid.UUID(game_id),
                InviteStatus.PENDING.value,
            )
            return [self._row_to_invite(row) for row in rows]

    async def get_pending_invites_for_user(self, user_id: str) -> List[GameInvite]:
        """Get all pending invites received by a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM game_invites WHERE invitee_id = $1 AND status = $2",
                uuid.UUID(user_id),
                InviteStatus.PENDING.value,
            )
            return [self._row_to_invite(row) for row in rows]

    async def update_invite(self, invite: GameInvite) -> Optional[GameInvite]:
        """Update an invite."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE game_invites SET status = $1, responded_at = $2
                WHERE id = $3
                """,
                invite.status.value,
                invite.responded_at,
                uuid.UUID(invite.id),
            )
            if result == "UPDATE 0":
                return None
            return invite

    async def search_users_by_username(self, query: str, exclude_user_id: str, limit: int = 10) -> List[User]:
        """Search users by username prefix."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, email, username, created_at, updated_at, last_login, is_active
                FROM users
                WHERE LOWER(username) LIKE LOWER($1) AND id != $2
                LIMIT $3
                """,
                f"{query}%",
                uuid.UUID(exclude_user_id),
                limit,
            )
            return [self._row_to_user(row) for row in rows]

    def _row_to_game(self, row: asyncpg.Record) -> Game:
        """Convert database row to Game model."""
        players_data = row["players"] if isinstance(row["players"], list) else json.loads(row["players"])
        players = []
        for p in players_data:
            players.append(GamePlayer(
                user_id=p["user_id"],
                username=p["username"],
                team_name=p.get("team_name"),
                joined_at=datetime.fromisoformat(p["joined_at"].replace("Z", "+00:00")) if isinstance(p["joined_at"], str) else p["joined_at"],
                is_creator=p.get("is_creator", False),
            ))
        return Game(
            id=str(row["id"]),
            name=row["name"],
            creator_id=str(row["creator_id"]),
            creator_username=row["creator_username"],
            status=GameStatus(row["status"]),
            players=players,
            max_players=row["max_players"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
        )

    def _row_to_invite(self, row: asyncpg.Record) -> GameInvite:
        """Convert database row to GameInvite model."""
        return GameInvite(
            id=str(row["id"]),
            game_id=str(row["game_id"]),
            inviter_id=str(row["inviter_id"]),
            invitee_id=str(row["invitee_id"]),
            invitee_username=row["invitee_username"],
            status=InviteStatus(row["status"]),
            created_at=row["created_at"],
            responded_at=row["responded_at"],
        )

    # Game state persistence
    async def save_game_state(self, game_id: str, state_data: dict) -> None:
        """Save game state data as JSON."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO game_states (game_id, state_data, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (game_id) DO UPDATE SET
                    state_data = EXCLUDED.state_data,
                    updated_at = EXCLUDED.updated_at
                """,
                uuid.UUID(game_id),
                json.dumps(state_data, default=str),
                datetime.now(timezone.utc),
            )

    async def load_game_state(self, game_id: str) -> Optional[dict]:
        """Load game state data. Returns None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state_data FROM game_states WHERE game_id = $1",
                uuid.UUID(game_id),
            )
            if not row:
                return None
            state_data = row["state_data"]
            if isinstance(state_data, str):
                return json.loads(state_data)
            return state_data

    async def delete_game_state(self, game_id: str) -> bool:
        """Delete game state data."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM game_states WHERE game_id = $1",
                uuid.UUID(game_id),
            )
            return result == "DELETE 1"
