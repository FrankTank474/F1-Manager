import uuid
from datetime import datetime, timezone
from typing import Optional, List

from ..datastore.interface import DatastoreInterface
from ..models.game import (
    Game, GameCreate, GamePlayer, GameStatus, GameSummary,
    GameInvite, GameInviteCreate, InviteStatus, PendingInvite
)
from ..models.user import User


class GameService:
    """Service for game management operations."""

    def __init__(self, datastore: DatastoreInterface):
        self.datastore = datastore

    async def create_game(self, name: str, creator_id: str, creator_username: str) -> Game:
        """Create a new game."""
        now = datetime.now(timezone.utc)
        game = Game(
            id=str(uuid.uuid4()),
            name=name,
            creator_id=creator_id,
            creator_username=creator_username,
            status=GameStatus.PENDING,
            players=[
                GamePlayer(
                    user_id=creator_id,
                    username=creator_username,
                    joined_at=now,
                    is_creator=True,
                )
            ],
            max_players=2,
            created_at=now,
            updated_at=now,
        )
        return await self.datastore.create_game(game)

    async def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID."""
        return await self.datastore.get_game_by_id(game_id)

    async def get_user_games(self, user_id: str) -> List[GameSummary]:
        """Get all games for a user as summaries."""
        games = await self.datastore.get_games_for_user(user_id)
        summaries = []
        for game in games:
            summaries.append(GameSummary(
                id=game.id,
                name=game.name,
                creator_username=game.creator_username,
                status=game.status,
                player_count=len(game.players),
                max_players=game.max_players,
                created_at=game.created_at,
                is_creator=game.creator_id == user_id,
            ))
        return summaries

    async def delete_game(self, game_id: str, user_id: str) -> bool:
        """Delete a game (only creator can delete)."""
        game = await self.datastore.get_game_by_id(game_id)
        if not game:
            return False
        if game.creator_id != user_id:
            raise ValueError("Only the creator can delete this game")
        # Can delete pending, stopped, completed, or abandoned games
        # Only active games cannot be deleted (stop first)
        if game.status == GameStatus.ACTIVE:
            raise ValueError("Cannot delete an active game. Stop it first.")
        return await self.datastore.delete_game(game_id)

    async def start_game(self, game_id: str, user_id: str) -> Game:
        """Start or resume a game."""
        game = await self.datastore.get_game_by_id(game_id)
        if not game:
            raise ValueError("Game not found")

        # Check user is a player
        is_player = any(p.user_id == user_id for p in game.players)
        if not is_player:
            raise ValueError("You are not a player in this game")

        # Handle different statuses
        if game.status == GameStatus.ACTIVE:
            # Already active, just return
            return game
        elif game.status == GameStatus.STOPPED:
            # Resume stopped game
            game.status = GameStatus.ACTIVE
            game.updated_at = datetime.now(timezone.utc)
            return await self.datastore.update_game(game)
        elif game.status == GameStatus.PENDING:
            # Start new game (only creator can start pending games)
            if game.creator_id != user_id:
                raise ValueError("Only the creator can start this game")
            if len(game.players) < 1:
                raise ValueError("Need at least 1 player to start")
            game.status = GameStatus.ACTIVE
            game.started_at = datetime.now(timezone.utc)
            game.updated_at = datetime.now(timezone.utc)
            return await self.datastore.update_game(game)
        else:
            raise ValueError(f"Cannot start game in {game.status} status")

    async def stop_game(self, game_id: str, user_id: str) -> Game:
        """Stop/pause a game (can be resumed later)."""
        game = await self.datastore.get_game_by_id(game_id)
        if not game:
            raise ValueError("Game not found")

        # Check user is a player
        is_player = any(p.user_id == user_id for p in game.players)
        if not is_player:
            raise ValueError("You are not a player in this game")

        if game.status != GameStatus.ACTIVE:
            raise ValueError("Game is not active")

        game.status = GameStatus.STOPPED
        game.updated_at = datetime.now(timezone.utc)
        return await self.datastore.update_game(game)

    # Invite operations
    async def invite_player(
        self, game_id: str, inviter_id: str, invitee_username: str
    ) -> GameInvite:
        """Invite a player to a game."""
        # Get game
        game = await self.datastore.get_game_by_id(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.creator_id != inviter_id:
            raise ValueError("Only the creator can invite players")
        if game.status != GameStatus.PENDING:
            raise ValueError("Cannot invite players to a started game")
        if len(game.players) >= game.max_players:
            raise ValueError("Game is full")

        # Get invitee
        invitee = await self.datastore.get_user_by_username(invitee_username)
        if not invitee:
            raise ValueError("User not found")
        if invitee.id == inviter_id:
            raise ValueError("Cannot invite yourself")

        # Check if already a player
        for player in game.players:
            if player.user_id == invitee.id:
                raise ValueError("User is already a player in this game")

        # Check for existing pending invite
        pending_invites = await self.datastore.get_pending_invites_for_game(game_id)
        for invite in pending_invites:
            if invite.invitee_id == invitee.id:
                raise ValueError("User already has a pending invite")

        # Create invite
        now = datetime.now(timezone.utc)
        invite = GameInvite(
            id=str(uuid.uuid4()),
            game_id=game_id,
            inviter_id=inviter_id,
            invitee_id=invitee.id,
            invitee_username=invitee.username,
            status=InviteStatus.PENDING,
            created_at=now,
        )

        return await self.datastore.create_invite(invite)

    async def withdraw_invite(self, invite_id: str, user_id: str) -> bool:
        """Withdraw an invite (only inviter can withdraw)."""
        invite = await self.datastore.get_invite_by_id(invite_id)
        if not invite:
            raise ValueError("Invite not found")
        if invite.inviter_id != user_id:
            raise ValueError("Only the inviter can withdraw this invite")
        if invite.status != InviteStatus.PENDING:
            raise ValueError("Invite is not pending")

        invite.status = InviteStatus.WITHDRAWN
        invite.responded_at = datetime.now(timezone.utc)
        await self.datastore.update_invite(invite)
        return True

    async def get_game_invites(self, game_id: str, user_id: str) -> List[GameInvite]:
        """Get all pending invites for a game (only creator can see)."""
        game = await self.datastore.get_game_by_id(game_id)
        if not game:
            raise ValueError("Game not found")
        if game.creator_id != user_id:
            raise ValueError("Only the creator can view invites")
        return await self.datastore.get_pending_invites_for_game(game_id)

    async def get_user_pending_invites(self, user_id: str) -> List[PendingInvite]:
        """Get all pending invites for a user."""
        invites = await self.datastore.get_pending_invites_for_user(user_id)
        pending = []
        for invite in invites:
            game = await self.datastore.get_game_by_id(invite.game_id)
            if game:
                pending.append(PendingInvite(
                    id=invite.id,
                    game_id=invite.game_id,
                    game_name=game.name,
                    inviter_username=game.creator_username,
                    created_at=invite.created_at,
                ))
        return pending

    async def respond_to_invite(
        self, invite_id: str, user_id: str, accept: bool
    ) -> Optional[Game]:
        """Accept or decline an invite."""
        invite = await self.datastore.get_invite_by_id(invite_id)
        if not invite:
            raise ValueError("Invite not found")
        if invite.invitee_id != user_id:
            raise ValueError("This invite is not for you")
        if invite.status != InviteStatus.PENDING:
            raise ValueError("Invite is not pending")

        now = datetime.now(timezone.utc)
        invite.responded_at = now

        if accept:
            # Get game and add player
            game = await self.datastore.get_game_by_id(invite.game_id)
            if not game:
                raise ValueError("Game no longer exists")
            if game.status != GameStatus.PENDING:
                raise ValueError("Game has already started")
            if len(game.players) >= game.max_players:
                raise ValueError("Game is full")

            # Get user info
            user = await self.datastore.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            # Add player
            game.players.append(GamePlayer(
                user_id=user_id,
                username=user.username,
                joined_at=now,
                is_creator=False,
            ))
            game.updated_at = now

            invite.status = InviteStatus.ACCEPTED
            await self.datastore.update_invite(invite)
            return await self.datastore.update_game(game)
        else:
            invite.status = InviteStatus.DECLINED
            await self.datastore.update_invite(invite)
            return None

    async def search_users(self, query: str, user_id: str) -> List[User]:
        """Search users by username for inviting."""
        if len(query) < 2:
            return []
        return await self.datastore.search_users_by_username(query, user_id, limit=10)
