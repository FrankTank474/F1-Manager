from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class GameStatus(str, Enum):
    PENDING = "pending"      # Created, waiting to start
    ACTIVE = "active"        # Game in progress
    STOPPED = "stopped"      # Game paused, can be resumed
    COMPLETED = "completed"  # Game finished
    ABANDONED = "abandoned"  # Game abandoned


class InviteStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class GameInvite(BaseModel):
    """Invitation to join a game."""
    id: str
    game_id: str
    inviter_id: str
    invitee_id: str
    invitee_username: str
    status: InviteStatus = InviteStatus.PENDING
    created_at: datetime
    responded_at: Optional[datetime] = None


class GamePlayer(BaseModel):
    """A player in a game."""
    user_id: str
    username: str
    team_name: Optional[str] = None
    joined_at: datetime
    is_creator: bool = False


class Game(BaseModel):
    """A game instance."""
    id: str
    name: str
    creator_id: str
    creator_username: str
    status: GameStatus = GameStatus.PENDING
    players: List[GamePlayer] = []
    max_players: int = 2
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class GameCreate(BaseModel):
    """Request to create a new game."""
    name: str = Field(..., min_length=1, max_length=100)


class GameInviteCreate(BaseModel):
    """Request to invite a player."""
    username: str = Field(..., min_length=1)


class GameSummary(BaseModel):
    """Summary of a game for listing."""
    id: str
    name: str
    creator_username: str
    status: GameStatus
    player_count: int
    max_players: int
    created_at: datetime
    is_creator: bool = False


class PendingInvite(BaseModel):
    """A pending invite for display."""
    id: str
    game_id: str
    game_name: str
    inviter_username: str
    created_at: datetime
