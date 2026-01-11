"""API endpoints for gameplay - Full multiplayer support."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ...models.game_state import (
    GameStateResponse, GamePhase, TireCompound,
    TireSelectionRequest, SignDriverRequest, PitStopRequest,
    SelectSponsorRequest, UpgradeCarRequest, StartDevelopmentRequest,
    ReleaseDriverRequest, ReadyRequest
)
from ...models.auth import MessageResponse
from ...services.game_state_service import game_state_manager, MultiplayerGameState
from ...dependencies import get_current_user_id, get_game_service

router = APIRouter(prefix="/gameplay", tags=["gameplay"])


def get_game_state(game_id: str, user_id: str) -> MultiplayerGameState:
    """Get game state and verify access."""
    game_state = game_state_manager.get_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game session not found")

    # Check if user is a player in the game
    if not game_state.is_player(user_id):
        raise HTTPException(status_code=403, detail="Not authorized for this game")

    return game_state


@router.post("/{game_id}/start", response_model=GameStateResponse)
async def start_game_session(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
    game_service = Depends(get_game_service),
):
    """Start or resume a game session."""
    # Verify game exists and user has access
    game = await game_service.get_game(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check user is a player
    is_player = any(p.user_id == user_id for p in game.players)
    if not is_player:
        raise HTTPException(status_code=403, detail="Not a player in this game")

    # Get player info
    player = next((p for p in game.players if p.user_id == user_id), None)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Reactivate game if stopped (or start if pending)
    try:
        await game_service.start_game(game_id, user_id)
    except ValueError as e:
        # Ignore errors like "already active" - we just want to make sure it's playable
        pass

    # Check if game state already exists
    game_state = game_state_manager.get_game(game_id)
    if not game_state:
        # Create new multiplayer game state
        game_state = game_state_manager.create_game(game_id, user_id, player.username)
    else:
        # Add this player if not already in the game
        if not game_state.is_player(user_id):
            game_state.add_player(user_id, player.username)

    return game_state.get_state_response(user_id)


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_current_state(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get current game state."""
    game_state = get_game_state(game_id, user_id)
    return game_state.get_state_response(user_id)


# ==================== SPONSOR SELECTION ====================

@router.post("/{game_id}/select-sponsor", response_model=GameStateResponse)
async def select_sponsor(
    game_id: str,
    request: SelectSponsorRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Select a sponsor for the player's team."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SPONSOR_SELECTION:
        raise HTTPException(status_code=400, detail="Not in sponsor selection phase")

    success = game_state.select_sponsor(user_id, request.sponsor_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to select sponsor")

    return game_state.get_state_response(user_id)


# ==================== DRIVER MANAGEMENT ====================

@router.post("/{game_id}/sign-driver", response_model=GameStateResponse)
async def sign_driver(
    game_id: str,
    request: SignDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Sign a driver to the player's team."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TEAM_SETUP:
        raise HTTPException(status_code=400, detail="Cannot sign drivers in current phase")

    success = game_state.sign_driver(
        user_id,
        request.driver_id,
        request.salary,
        request.years,
        request.is_number_one
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to sign driver - not your turn or driver unavailable")

    return game_state.get_state_response(user_id)


@router.post("/{game_id}/release-driver", response_model=GameStateResponse)
async def release_driver(
    game_id: str,
    request: ReleaseDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Release a driver from the player's team."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only release drivers in main menu")

    success = game_state.release_driver(user_id, request.driver_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to release driver")

    return game_state.get_state_response(user_id)


# ==================== CAR UPGRADES ====================

@router.post("/{game_id}/upgrade-car", response_model=GameStateResponse)
async def upgrade_car(
    game_id: str,
    request: UpgradeCarRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Upgrade a car stat."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only upgrade car in main menu")

    success = game_state.upgrade_car(user_id, request.stat_name, request.points)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to upgrade car - insufficient budget or invalid stat")

    return game_state.get_state_response(user_id)


# ==================== DEVELOPMENT TREE ====================

@router.post("/{game_id}/start-development", response_model=GameStateResponse)
async def start_development(
    game_id: str,
    request: StartDevelopmentRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Start a development node."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only start development in main menu")

    success = game_state.start_development(user_id, request.node_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start development - invalid node, locked, or insufficient budget")

    return game_state.get_state_response(user_id)


# ==================== READY / WAITING ====================

@router.post("/{game_id}/ready", response_model=GameStateResponse)
async def mark_ready(
    game_id: str,
    request: ReadyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Mark player as ready to proceed."""
    game_state = get_game_state(game_id, user_id)

    game_state.set_player_ready(user_id, request.ready)
    return game_state.get_state_response(user_id)


# ==================== RACE WEEKEND ====================

@router.post("/{game_id}/start-race-weekend", response_model=GameStateResponse)
async def start_race_weekend(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start a race weekend (qualifying)."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Cannot start race weekend in current phase")

    success = game_state.start_race_weekend(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start race weekend")

    return game_state.get_state_response(user_id)


@router.post("/{game_id}/advance-to-tire-selection", response_model=GameStateResponse)
async def advance_to_tire_selection(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance from qualifying to tire selection."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.QUALIFYING:
        raise HTTPException(status_code=400, detail="Not in qualifying phase")

    success = game_state.advance_to_tire_selection(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance to tire selection")

    return game_state.get_state_response(user_id)


@router.post("/{game_id}/select-tire", response_model=GameStateResponse)
async def select_tire(
    game_id: str,
    request: TireSelectionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Select tire compound for a driver."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TIRE_SELECTION:
        raise HTTPException(status_code=400, detail="Not in tire selection phase")

    success = game_state.select_tire(user_id, request.driver_id, request.compound)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to select tire - not your driver or not your turn")

    return game_state.get_state_response(user_id)


# ==================== RACE SIMULATION ====================

@router.post("/{game_id}/simulate-lap", response_model=GameStateResponse)
async def simulate_lap(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Simulate one lap of the race."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.simulate_race_lap()
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/pit-stop", response_model=GameStateResponse)
async def make_pit_stop(
    game_id: str,
    request: PitStopRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Make a pit stop for a driver."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    success = game_state.pit_player_driver(user_id, request.driver_id, request.compound.value)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pit driver - not your driver")

    return game_state.get_state_response(user_id)


@router.post("/{game_id}/confirm-pit-decisions", response_model=GameStateResponse)
async def confirm_pit_decisions(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Confirm pit decisions (after pitting or choosing to stay out) for multiplayer sync."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.confirm_pit_decisions(user_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/simulate-race", response_model=GameStateResponse)
async def simulate_full_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Simulate the entire race at once."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.simulate_full_race()
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/next-race", response_model=GameStateResponse)
async def advance_to_next_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance to the next race."""
    game_state = get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_RESULTS:
        raise HTTPException(status_code=400, detail="Race not finished")

    success = game_state.advance_to_next_race(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance to next race")

    return game_state.get_state_response(user_id)


# ==================== INBOX ====================

@router.post("/{game_id}/mark-message-read", response_model=GameStateResponse)
async def mark_message_read(
    game_id: str,
    message_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark an inbox message as read."""
    game_state = get_game_state(game_id, user_id)

    game_state.mark_message_read(user_id, message_id)
    return game_state.get_state_response(user_id)
