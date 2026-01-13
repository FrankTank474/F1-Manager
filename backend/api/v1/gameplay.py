"""API endpoints for gameplay - Full multiplayer support."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ...models.game_state import (
    GameStateResponse, GamePhase, TireCompound,
    TireSelectionRequest, SignDriverRequest, PitStopRequest,
    SelectSponsorRequest, UpgradeCarRequest, StartDevelopmentRequest,
    ReleaseDriverRequest, ReadyRequest, SetTeamNameRequest
)
from ...models.auth import MessageResponse
from ...services.game_state_service import game_state_manager, MultiplayerGameState
from ...dependencies import get_current_user_id, get_game_service

router = APIRouter(prefix="/gameplay", tags=["gameplay"])


async def get_game_state(game_id: str, user_id: str) -> MultiplayerGameState:
    """Get game state and verify access."""
    # Try to load from memory or datastore
    game_state = await game_state_manager.load_game(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game session not found")

    # Check if user is a player in the game
    if not game_state.is_player(user_id):
        raise HTTPException(status_code=403, detail="Not authorized for this game")

    return game_state


async def save_game_state(game_id: str) -> None:
    """Save game state after modifications."""
    await game_state_manager.save_game(game_id)


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

    # Check if game state already exists (try memory then datastore)
    game_state = await game_state_manager.load_game(game_id)
    if not game_state:
        # Create new multiplayer game state
        game_state = game_state_manager.create_game(game_id, user_id, player.username)
    else:
        # Add this player if not already in the game
        if not game_state.is_player(user_id):
            game_state.add_player(user_id, player.username)

    # Save game state to datastore
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.get("/{game_id}/state", response_model=GameStateResponse)
async def get_current_state(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get current game state."""
    game_state = await get_game_state(game_id, user_id)
    return game_state.get_state_response(user_id)


# ==================== TEAM NAME SELECTION ====================

@router.post("/{game_id}/set-team-name", response_model=GameStateResponse)
async def set_team_name(
    game_id: str,
    request: SetTeamNameRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Set the team name for the player."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TEAM_NAME_SELECTION:
        raise HTTPException(status_code=400, detail="Not in team name selection phase")

    success = game_state.set_team_name(user_id, request.team_name)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to set team name. Name must be 3-30 characters.")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== SPONSOR SELECTION ====================

@router.post("/{game_id}/select-sponsor", response_model=GameStateResponse)
async def select_sponsor(
    game_id: str,
    request: SelectSponsorRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Select a sponsor for the player's team."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SPONSOR_SELECTION:
        raise HTTPException(status_code=400, detail="Not in sponsor selection phase")

    success = game_state.select_sponsor(user_id, request.sponsor_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to select sponsor")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== DRIVER MANAGEMENT ====================

@router.post("/{game_id}/sign-driver", response_model=GameStateResponse)
async def sign_driver(
    game_id: str,
    request: SignDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Sign a driver to the player's team."""
    game_state = await get_game_state(game_id, user_id)

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

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/release-driver", response_model=GameStateResponse)
async def release_driver(
    game_id: str,
    request: ReleaseDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Release a driver from the player's team."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only release drivers in main menu")

    success = game_state.release_driver(user_id, request.driver_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to release driver")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== CAR UPGRADES ====================

@router.post("/{game_id}/upgrade-car", response_model=GameStateResponse)
async def upgrade_car(
    game_id: str,
    request: UpgradeCarRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Upgrade a car stat."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only upgrade car in main menu")

    success = game_state.upgrade_car(user_id, request.stat_name, request.points)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to upgrade car - insufficient budget or invalid stat")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== DEVELOPMENT TREE ====================

@router.post("/{game_id}/start-development", response_model=GameStateResponse)
async def start_development(
    game_id: str,
    request: StartDevelopmentRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Start a development node."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Can only start development in main menu")

    success = game_state.start_development(user_id, request.node_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start development - invalid node, locked, or insufficient budget")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== READY / WAITING ====================

@router.post("/{game_id}/ready", response_model=GameStateResponse)
async def mark_ready(
    game_id: str,
    request: ReadyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Mark player as ready to proceed."""
    game_state = await get_game_state(game_id, user_id)

    game_state.set_player_ready(user_id, request.ready)
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== RACE WEEKEND ====================

@router.post("/{game_id}/start-race-weekend", response_model=GameStateResponse)
async def start_race_weekend(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start a race weekend (qualifying)."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.MAIN_MENU:
        raise HTTPException(status_code=400, detail="Cannot start race weekend in current phase")

    success = game_state.start_race_weekend(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start race weekend")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/advance-qualifying", response_model=GameStateResponse)
async def advance_qualifying(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance to the next qualifying session (Q1->Q2->Q3->Tire Selection)."""
    game_state = await get_game_state(game_id, user_id)

    valid_phases = [
        GamePhase.QUALIFYING_Q1, GamePhase.QUALIFYING_Q2, GamePhase.QUALIFYING_Q3,
        GamePhase.SPRINT_SHOOTOUT_Q1, GamePhase.SPRINT_SHOOTOUT_Q2, GamePhase.SPRINT_SHOOTOUT_Q3,
        GamePhase.QUALIFYING  # Legacy support
    ]

    if game_state.phase not in valid_phases:
        raise HTTPException(status_code=400, detail="Not in a qualifying phase")

    success = game_state.advance_qualifying(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance qualifying")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/advance-to-tire-selection", response_model=GameStateResponse)
async def advance_to_tire_selection(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance from qualifying to tire selection (legacy endpoint)."""
    game_state = await get_game_state(game_id, user_id)

    # Support both old QUALIFYING phase and new Q3 phase
    if game_state.phase not in [GamePhase.QUALIFYING, GamePhase.QUALIFYING_Q3]:
        raise HTTPException(status_code=400, detail="Not in qualifying phase")

    if hasattr(game_state, 'advance_qualifying'):
        success = game_state.advance_qualifying(user_id)
    else:
        success = game_state.advance_to_tire_selection(user_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance to tire selection")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== SPRINT RACE ====================

@router.post("/{game_id}/start-sprint-race", response_model=GameStateResponse)
async def start_sprint_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Start the sprint race from the sprint grid."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SPRINT_GRID:
        raise HTTPException(status_code=400, detail="Not on sprint grid")

    success = game_state.start_sprint_race(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start sprint race")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/simulate-sprint-lap", response_model=GameStateResponse)
async def simulate_sprint_lap(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Simulate one lap of the sprint race."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SPRINT_RACE:
        raise HTTPException(status_code=400, detail="Sprint race not in progress")

    game_state.simulate_sprint_lap()
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/advance-from-sprint", response_model=GameStateResponse)
async def advance_from_sprint(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance from sprint results to main race qualifying."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SPRINT_RESULTS:
        raise HTTPException(status_code=400, detail="Not in sprint results phase")

    success = game_state.advance_from_sprint_results(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance from sprint results")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/select-tire", response_model=GameStateResponse)
async def select_tire(
    game_id: str,
    request: TireSelectionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Select tire compound for a driver."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TIRE_SELECTION:
        raise HTTPException(status_code=400, detail="Not in tire selection phase")

    success = game_state.select_tire(user_id, request.driver_id, request.compound)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to select tire - not your driver or not your turn")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/ready-to-race", response_model=GameStateResponse)
async def ready_to_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark player as ready to start the race (after selecting tires)."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TIRE_SELECTION:
        raise HTTPException(status_code=400, detail="Not in tire selection phase")

    success = game_state.ready_to_race(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Must select tires for all drivers first")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== RACE SIMULATION ====================

@router.post("/{game_id}/simulate-lap", response_model=GameStateResponse)
async def simulate_lap(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Simulate one lap of the race."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.simulate_race_lap()
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/pit-stop", response_model=GameStateResponse)
async def make_pit_stop(
    game_id: str,
    request: PitStopRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Make a pit stop for a driver."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    result = game_state.pit_player_driver(user_id, request.driver_id, request.compound.value)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to pit driver"))

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/confirm-pit-decisions", response_model=GameStateResponse)
async def confirm_pit_decisions(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Confirm pit decisions (after pitting or choosing to stay out) for multiplayer sync."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.confirm_pit_decisions(user_id)
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/simulate-race", response_model=GameStateResponse)
async def simulate_full_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Simulate the entire race at once."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Race not in progress")

    game_state.simulate_full_race()
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/next-race", response_model=GameStateResponse)
async def advance_to_next_race(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Advance to the next race."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.RACE_RESULTS:
        raise HTTPException(status_code=400, detail="Race not finished")

    success = game_state.advance_to_next_race(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to advance to next race")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/proceed-from-season-end", response_model=GameStateResponse)
async def proceed_from_season_end(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Proceed from season end standings to transfer window."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.SEASON_END:
        raise HTTPException(status_code=400, detail="Not in season end phase")

    success = game_state.proceed_from_season_end(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to proceed")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/fast-forward")
async def fast_forward_races(
    game_id: str,
    num_races: int = 1,
    user_id: str = Depends(get_current_user_id),
):
    """Fast forward through multiple races (3, 5, 10, or -1 for rest of season)."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase not in [GamePhase.MAIN_MENU, GamePhase.RACE_RESULTS]:
        raise HTTPException(status_code=400, detail="Can only fast forward from main menu or race results")

    result = game_state.fast_forward_races(user_id, num_races)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Fast forward failed"))

    await save_game_state(game_id)
    return {
        "state": game_state.get_state_response(user_id),
        "fast_forward_results": result
    }


@router.post("/{game_id}/fast-forward-ready")
async def toggle_fast_forward_ready(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Toggle ready status for multiplayer fast forward. Step 1."""
    game_state = await get_game_state(game_id, user_id)

    result = game_state.toggle_fast_forward_ready(user_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to toggle ready"))

    await save_game_state(game_id)

    return {
        "state": game_state.get_state_response(user_id),
        "is_ready": result.get("is_ready")
    }


@router.post("/{game_id}/fast-forward-select")
async def select_fast_forward_races(
    game_id: str,
    num_races: int = 1,
    user_id: str = Depends(get_current_user_id),
):
    """Select number of races for multiplayer fast forward. Step 2 - both must be ready."""
    game_state = await get_game_state(game_id, user_id)

    result = game_state.select_fast_forward_races(user_id, num_races)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Selection failed"))

    await save_game_state(game_id)

    # If fast forward was executed, include the results
    if result.get("executed"):
        return {
            "state": game_state.get_state_response(user_id),
            "fast_forward_results": result,
            "executed": True
        }

    # Otherwise return state with waiting/mismatch status
    return {
        "state": game_state.get_state_response(user_id),
        "waiting": result.get("waiting", False),
        "mismatch": result.get("mismatch", False),
        "your_selection": result.get("your_selection"),
        "other_selection": result.get("other_selection"),
        "message": result.get("message")
    }


@router.post("/{game_id}/cancel-fast-forward")
async def cancel_fast_forward(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Cancel fast forward - clear ready and selection status."""
    game_state = await get_game_state(game_id, user_id)

    game_state.cancel_fast_forward(user_id)
    await save_game_state(game_id)

    return {
        "state": game_state.get_state_response(user_id),
        "cancelled": True
    }


# ==================== INBOX ====================

@router.post("/{game_id}/mark-message-read", response_model=GameStateResponse)
async def mark_message_read(
    game_id: str,
    message_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Mark an inbox message as read."""
    game_state = await get_game_state(game_id, user_id)

    game_state.mark_message_read(user_id, message_id)
    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


# ==================== TRANSFER WINDOW ====================

@router.post("/{game_id}/transfer-sign-driver", response_model=GameStateResponse)
async def transfer_sign_driver(
    game_id: str,
    request: SignDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Sign a driver during the transfer window."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TRANSFER_WINDOW:
        raise HTTPException(status_code=400, detail="Not in transfer window")

    success = game_state.sign_driver_transfer(
        user_id,
        request.driver_id,
        request.salary,
        request.years
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to sign driver - not interested, too expensive, or team full")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/transfer-release-driver", response_model=GameStateResponse)
async def transfer_release_driver(
    game_id: str,
    request: ReleaseDriverRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Release a driver during the transfer window."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TRANSFER_WINDOW:
        raise HTTPException(status_code=400, detail="Not in transfer window")

    success = game_state.release_driver_transfer(user_id, request.driver_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to release driver - must keep at least one driver")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)


@router.post("/{game_id}/skip-transfer-window", response_model=GameStateResponse)
async def skip_transfer_window(
    game_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Skip the transfer window and start the next season."""
    game_state = await get_game_state(game_id, user_id)

    if game_state.phase != GamePhase.TRANSFER_WINDOW:
        raise HTTPException(status_code=400, detail="Not in transfer window")

    success = game_state.skip_transfer_window(user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to skip transfer window")

    await save_game_state(game_id)
    return game_state.get_state_response(user_id)
