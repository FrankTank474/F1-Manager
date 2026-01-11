from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from ...models.game import (
    Game, GameCreate, GameSummary, GameInvite, GameInviteCreate, PendingInvite
)
from ...models.auth import MessageResponse
from ...models.user import User
from ...services.game_service import GameService
from ...services.game_state_service import game_state_manager
from ...dependencies import get_game_service, get_current_user_id, get_user_service

router = APIRouter(prefix="/games", tags=["games"])


# Static routes MUST come before dynamic /{game_id} routes to avoid conflicts

@router.get("", response_model=List[GameSummary])
async def list_games(
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Get all games for the current user."""
    return await game_service.get_user_games(user_id)


@router.post("", response_model=Game, status_code=status.HTTP_201_CREATED)
async def create_game(
    game_data: GameCreate,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
    user_service = Depends(get_user_service),
):
    """Create a new game."""
    user = await user_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await game_service.create_game(
        name=game_data.name,
        creator_id=user_id,
        creator_username=user.username,
    )


# User search for inviting (static path - must be before /{game_id})
@router.get("/users/search", response_model=List[User])
async def search_users(
    q: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Search users by username for inviting."""
    return await game_service.search_users(q, user_id)


# User's received invites (static path - must be before /{game_id})
@router.get("/invites/pending", response_model=List[PendingInvite])
async def get_my_pending_invites(
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Get all pending invites for the current user."""
    return await game_service.get_user_pending_invites(user_id)


@router.delete("/invites/{invite_id}", response_model=MessageResponse)
async def withdraw_invite(
    invite_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Withdraw an invite (inviter only)."""
    try:
        await game_service.withdraw_invite(invite_id, user_id)
        return MessageResponse(message="Invite withdrawn successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invites/{invite_id}/accept", response_model=Game)
async def accept_invite(
    invite_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Accept an invite."""
    try:
        game = await game_service.respond_to_invite(invite_id, user_id, accept=True)
        if not game:
            raise HTTPException(status_code=500, detail="Failed to join game")
        return game
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invites/{invite_id}/decline", response_model=MessageResponse)
async def decline_invite(
    invite_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Decline an invite."""
    try:
        await game_service.respond_to_invite(invite_id, user_id, accept=False)
        return MessageResponse(message="Invite declined")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Dynamic routes with {game_id} parameter - MUST come after static routes

@router.get("/{game_id}", response_model=Game)
async def get_game(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Get a specific game."""
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    # Check user is a player
    is_player = any(p.user_id == user_id for p in game.players)
    if not is_player and game.creator_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this game")
    return game


@router.delete("/{game_id}", response_model=MessageResponse)
async def delete_game(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Delete a game (creator only)."""
    try:
        deleted = await game_service.delete_game(game_id, user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Game not found")
        return MessageResponse(message="Game deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/start", response_model=Game)
async def start_game(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Start or resume a game."""
    try:
        return await game_service.start_game(game_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/stop", response_model=Game)
async def stop_game(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Stop a game (sets to inactive, can be resumed later)."""
    try:
        # Mark game state as stopped so other player gets notified
        game_state = await game_state_manager.load_game(game_id)
        if game_state:
            game_state.stop_game(user_id)
            await game_state_manager.save_game(game_id)

        return await game_service.stop_game(game_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{game_id}/invites", response_model=List[GameInvite])
async def get_game_invites(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Get all pending invites for a game (creator only)."""
    try:
        return await game_service.get_game_invites(game_id, user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/invites", response_model=GameInvite, status_code=status.HTTP_201_CREATED)
async def invite_player(
    game_id: str,
    invite_data: GameInviteCreate,
    user_id: str = Depends(get_current_user_id),
    game_service: GameService = Depends(get_game_service),
):
    """Invite a player to a game (creator only)."""
    try:
        return await game_service.invite_player(
            game_id=game_id,
            inviter_id=user_id,
            invitee_username=invite_data.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
