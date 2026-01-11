import json
import asyncio
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .interface import DatastoreInterface
from ..models.user import User, UserUpdate, UserInDB
from ..models.game import Game, GameInvite, GamePlayer, GameStatus, InviteStatus


class LocalJSONDatastore(DatastoreInterface):
    """Local JSON file-based datastore for development."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.users_file = data_dir / "users.json"
        self.tokens_file = data_dir / "blacklisted_tokens.json"
        self.games_file = data_dir / "games.json"
        self.invites_file = data_dir / "invites.json"
        self._users: Dict[str, Dict[str, Any]] = {}
        self._tokens: Dict[str, str] = {}  # jti -> expires_at ISO string
        self._games: Dict[str, Dict[str, Any]] = {}
        self._invites: Dict[str, Dict[str, Any]] = {}
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
        if self.games_file.exists():
            with open(self.games_file, "r") as f:
                self._games = json.load(f)
        if self.invites_file.exists():
            with open(self.invites_file, "r") as f:
                self._invites = json.load(f)

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

    async def _save_games(self) -> None:
        """Save games to JSON file."""
        async with self._lock:
            with open(self.games_file, "w") as f:
                json.dump(self._games, f, indent=2, default=str)

    async def _save_invites(self) -> None:
        """Save invites to JSON file."""
        async with self._lock:
            with open(self.invites_file, "w") as f:
                json.dump(self._invites, f, indent=2, default=str)

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

    def _serialize_player(self, player: GamePlayer) -> dict:
        """Serialize a GamePlayer to a JSON-compatible dict."""
        return {
            "user_id": player.user_id,
            "username": player.username,
            "team_name": player.team_name,
            "joined_at": player.joined_at.isoformat(),
            "is_creator": player.is_creator,
        }

    # Game operations
    async def create_game(self, game: Game) -> Game:
        """Create a new game."""
        game_data = {
            "id": game.id,
            "name": game.name,
            "creator_id": game.creator_id,
            "creator_username": game.creator_username,
            "status": game.status.value,
            "players": [self._serialize_player(p) for p in game.players],
            "max_players": game.max_players,
            "created_at": game.created_at.isoformat(),
            "updated_at": game.updated_at.isoformat(),
            "started_at": game.started_at.isoformat() if game.started_at else None,
            "completed_at": game.completed_at.isoformat() if game.completed_at else None,
        }
        self._games[game.id] = game_data
        await self._save_games()
        return game

    async def get_game_by_id(self, game_id: str) -> Optional[Game]:
        """Get game by ID."""
        game_data = self._games.get(game_id)
        if not game_data:
            return None
        return self._to_game(game_data)

    async def get_games_for_user(self, user_id: str) -> List[Game]:
        """Get all games where user is a player or creator."""
        games = []
        for game_data in self._games.values():
            # Check if user is creator
            if game_data["creator_id"] == user_id:
                games.append(self._to_game(game_data))
                continue
            # Check if user is a player
            for player in game_data["players"]:
                if player["user_id"] == user_id:
                    games.append(self._to_game(game_data))
                    break
        return games

    async def update_game(self, game: Game) -> Optional[Game]:
        """Update a game."""
        if game.id not in self._games:
            return None
        game_data = {
            "id": game.id,
            "name": game.name,
            "creator_id": game.creator_id,
            "creator_username": game.creator_username,
            "status": game.status.value,
            "players": [self._serialize_player(p) for p in game.players],
            "max_players": game.max_players,
            "created_at": game.created_at.isoformat(),
            "updated_at": game.updated_at.isoformat(),
            "started_at": game.started_at.isoformat() if game.started_at else None,
            "completed_at": game.completed_at.isoformat() if game.completed_at else None,
        }
        self._games[game.id] = game_data
        await self._save_games()
        return game

    async def delete_game(self, game_id: str) -> bool:
        """Delete a game."""
        if game_id not in self._games:
            return False
        del self._games[game_id]
        # Also delete related invites
        invites_to_delete = [
            inv_id for inv_id, inv in self._invites.items()
            if inv["game_id"] == game_id
        ]
        for inv_id in invites_to_delete:
            del self._invites[inv_id]
        await self._save_games()
        await self._save_invites()
        return True

    # Game invite operations
    async def create_invite(self, invite: GameInvite) -> GameInvite:
        """Create a game invite."""
        invite_data = {
            "id": invite.id,
            "game_id": invite.game_id,
            "inviter_id": invite.inviter_id,
            "invitee_id": invite.invitee_id,
            "invitee_username": invite.invitee_username,
            "status": invite.status.value,
            "created_at": invite.created_at.isoformat(),
            "responded_at": invite.responded_at.isoformat() if invite.responded_at else None,
        }
        self._invites[invite.id] = invite_data
        await self._save_invites()
        return invite

    async def get_invite_by_id(self, invite_id: str) -> Optional[GameInvite]:
        """Get invite by ID."""
        invite_data = self._invites.get(invite_id)
        if not invite_data:
            return None
        return self._to_invite(invite_data)

    async def get_pending_invites_for_game(self, game_id: str) -> List[GameInvite]:
        """Get all pending invites for a game."""
        invites = []
        for invite_data in self._invites.values():
            if invite_data["game_id"] == game_id and invite_data["status"] == InviteStatus.PENDING.value:
                invites.append(self._to_invite(invite_data))
        return invites

    async def get_pending_invites_for_user(self, user_id: str) -> List[GameInvite]:
        """Get all pending invites received by a user."""
        invites = []
        for invite_data in self._invites.values():
            if invite_data["invitee_id"] == user_id and invite_data["status"] == InviteStatus.PENDING.value:
                invites.append(self._to_invite(invite_data))
        return invites

    async def update_invite(self, invite: GameInvite) -> Optional[GameInvite]:
        """Update an invite."""
        if invite.id not in self._invites:
            return None
        invite_data = {
            "id": invite.id,
            "game_id": invite.game_id,
            "inviter_id": invite.inviter_id,
            "invitee_id": invite.invitee_id,
            "invitee_username": invite.invitee_username,
            "status": invite.status.value,
            "created_at": invite.created_at.isoformat(),
            "responded_at": invite.responded_at.isoformat() if invite.responded_at else None,
        }
        self._invites[invite.id] = invite_data
        await self._save_invites()
        return invite

    async def search_users_by_username(self, query: str, exclude_user_id: str, limit: int = 10) -> List[User]:
        """Search users by username prefix."""
        results = []
        query_lower = query.lower()
        for user_data in self._users.values():
            if user_data["id"] == exclude_user_id:
                continue
            if user_data["username"].lower().startswith(query_lower):
                results.append(self._to_user(user_data))
                if len(results) >= limit:
                    break
        return results

    def _to_game(self, data: Dict[str, Any]) -> Game:
        """Convert dict to Game model."""
        players = []
        for p in data.get("players", []):
            players.append(GamePlayer(
                user_id=p["user_id"],
                username=p["username"],
                team_name=p.get("team_name"),
                joined_at=datetime.fromisoformat(p["joined_at"].replace("Z", "+00:00")),
                is_creator=p.get("is_creator", False),
            ))
        return Game(
            id=data["id"],
            name=data["name"],
            creator_id=data["creator_id"],
            creator_username=data["creator_username"],
            status=GameStatus(data["status"]),
            players=players,
            max_players=data["max_players"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            started_at=(
                datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
                if data.get("started_at")
                else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
                if data.get("completed_at")
                else None
            ),
        )

    def _to_invite(self, data: Dict[str, Any]) -> GameInvite:
        """Convert dict to GameInvite model."""
        return GameInvite(
            id=data["id"],
            game_id=data["game_id"],
            inviter_id=data["inviter_id"],
            invitee_id=data["invitee_id"],
            invitee_username=data["invitee_username"],
            status=InviteStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            responded_at=(
                datetime.fromisoformat(data["responded_at"].replace("Z", "+00:00"))
                if data.get("responded_at")
                else None
            ),
        )
