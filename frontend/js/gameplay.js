// Gameplay module for F1 Manager web version - Full Multiplayer Support
import { api, ApiError } from './api.js';
import { escapeHtml, formatDate, showAlert, setButtonLoading } from './utils.js';
import { modalAlert, modalConfirm } from './modal.js';

// Game phases
const GamePhase = {
    WAITING_FOR_PLAYERS: 'waiting_for_players',
    TEAM_NAME_SELECTION: 'team_name_selection',
    SPONSOR_SELECTION: 'sponsor_selection',
    TEAM_SETUP: 'team_setup',
    MAIN_MENU: 'main_menu',
    RACE_WEEKEND: 'race_weekend',
    // Qualifying stages
    QUALIFYING: 'qualifying',
    QUALIFYING_Q1: 'qualifying_q1',
    QUALIFYING_Q2: 'qualifying_q2',
    QUALIFYING_Q3: 'qualifying_q3',
    // Sprint weekend phases
    SPRINT_SHOOTOUT_Q1: 'sprint_shootout_q1',
    SPRINT_SHOOTOUT_Q2: 'sprint_shootout_q2',
    SPRINT_SHOOTOUT_Q3: 'sprint_shootout_q3',
    SPRINT_GRID: 'sprint_grid',
    SPRINT_RACE: 'sprint_race',
    SPRINT_RESULTS: 'sprint_results',
    // Race phases
    TIRE_SELECTION: 'tire_selection',
    RACE_IN_PROGRESS: 'race_in_progress',
    RACE_RESULTS: 'race_results',
    SEASON_END: 'season_end',
    TRANSFER_WINDOW: 'transfer_window'
};

let currentGameState = null;
let raceSimulationInterval = null;
let currentContainer = null;
let refreshInterval = null;

/**
 * Render multiplayer status bar
 */
function renderMultiplayerStatus(state) {
    if (!state.is_multiplayer) return '';

    const players = state.players || [];
    const currentPlayerId = state.turn_info?.current_player_id;
    const isYourTurn = state.is_your_turn;

    return `
        <div class="multiplayer-status-bar">
            <div class="players-status">
                ${players.map(p => `
                    <div class="player-badge ${p.player_id === state.your_player_id ? 'you' : 'opponent'} ${p.player_id === currentPlayerId ? 'active-turn' : ''}">
                        <span class="player-name">${escapeHtml(p.username)}</span>
                        ${p.is_ready ? '<span class="ready-badge">Ready</span>' : ''}
                    </div>
                `).join('')}
            </div>
            ${state.turn_info ? `
                <div class="turn-indicator ${isYourTurn ? 'your-turn' : 'waiting'}">
                    ${isYourTurn ? 'Your Turn' : `Waiting for ${escapeHtml(state.turn_info.current_player_username)}`}
                </div>
            ` : ''}
        </div>
    `;
}

/**
 * Render game control buttons
 */
function renderGameControls(state) {
    return `
        <div class="game-controls-bar">
            ${renderMultiplayerStatus(state)}
            <button class="btn btn-danger btn-sm" id="stop-game-btn" title="Stop game and return to lobby">
                Stop Game
            </button>
        </div>
    `;
}

/**
 * Attach game control event listeners
 */
function attachGameControlListeners(container, state) {
    document.getElementById('stop-game-btn')?.addEventListener('click', async () => {
        const confirmed = await modalConfirm('Stop this game? You can resume it later by clicking Play.', 'Stop Game');
        if (confirmed) {
            stopRefreshInterval();
            try {
                await api.post(`/games/${state.game_id}/stop`);
                window.location.hash = '#/games';
            } catch (error) {
                console.error('Failed to stop game:', error);
                window.location.hash = '#/games';
            }
        }
    });
}

/**
 * Start auto-refresh for multiplayer waiting states
 */
function startRefreshInterval(gameId, container) {
    stopRefreshInterval();
    refreshInterval = setInterval(async () => {
        try {
            const state = await api.get(`/gameplay/${gameId}/state`);

            // Check if game was stopped by another player
            if (state.game_stopped) {
                stopRefreshInterval();
                await modalAlert(`Game stopped by ${state.stopped_by || 'another player'}. Returning to lobby.`, 'Game Stopped');
                window.location.hash = '#/games';
                return;
            }

            if (state.phase !== currentGameState?.phase ||
                JSON.stringify(state.players) !== JSON.stringify(currentGameState?.players) ||
                state.turn_info?.current_player_id !== currentGameState?.turn_info?.current_player_id) {
                renderGameScreen(container, state);
            }
        } catch (error) {
            console.error('Refresh failed:', error);
        }
    }, 3000);
}

function stopRefreshInterval() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

/**
 * Start or resume a game session
 */
export async function startGameSession(gameId, container) {
    currentContainer = container;
    stopRefreshInterval();
    try {
        const state = await api.post(`/gameplay/${gameId}/start`);
        currentGameState = state;
        renderGameScreen(container, state);
    } catch (error) {
        container.innerHTML = `
            <div class="container" style="padding-top: var(--space-xl);">
                <div class="alert alert-error">Failed to start game: ${error.message}</div>
                <a href="#/games" class="btn btn-secondary mt-lg">Back to Games</a>
            </div>
        `;
    }
}

/**
 * Render the appropriate game screen based on phase
 */
function renderGameScreen(container, state) {
    currentGameState = state;
    currentContainer = container;
    stopRefreshInterval();

    // Check if game was stopped
    if (state.game_stopped) {
        modalAlert(`Game stopped by ${state.stopped_by || 'another player'}. Returning to lobby.`, 'Game Stopped')
            .then(() => { window.location.hash = '#/games'; });
        return;
    }

    // Render screen based on phase
    switch (state.phase) {
        case GamePhase.WAITING_FOR_PLAYERS:
            renderWaitingForPlayers(container, state);
            startRefreshInterval(state.game_id, container);
            break;
        case GamePhase.TEAM_NAME_SELECTION:
            renderTeamNameSelection(container, state);
            if (state.players?.find(p => p.player_id === state.your_player_id)?.has_set_team_name) {
                startRefreshInterval(state.game_id, container);
            }
            break;
        case GamePhase.SPONSOR_SELECTION:
            renderSponsorSelection(container, state);
            if (!state.players?.find(p => p.player_id === state.your_player_id)?.has_selected_sponsor) {
                // Haven't selected yet
            } else {
                startRefreshInterval(state.game_id, container);
            }
            break;
        case GamePhase.TEAM_SETUP:
            renderDriverSelection(container, state);
            if (!state.is_your_turn && state.is_multiplayer) {
                startRefreshInterval(state.game_id, container);
            }
            break;
        case GamePhase.MAIN_MENU:
            renderMainMenu(container, state);
            break;
        case GamePhase.QUALIFYING:
        case GamePhase.QUALIFYING_Q1:
            renderQualifyingQ1(container, state);
            break;
        case GamePhase.QUALIFYING_Q2:
            renderQualifyingQ2(container, state);
            break;
        case GamePhase.QUALIFYING_Q3:
            renderQualifyingQ3(container, state);
            break;
        case GamePhase.SPRINT_SHOOTOUT_Q1:
            renderSprintShootoutQ1(container, state);
            break;
        case GamePhase.SPRINT_SHOOTOUT_Q2:
            renderSprintShootoutQ2(container, state);
            break;
        case GamePhase.SPRINT_SHOOTOUT_Q3:
            renderSprintShootoutQ3(container, state);
            break;
        case GamePhase.SPRINT_GRID:
            renderSprintGrid(container, state);
            break;
        case GamePhase.SPRINT_RACE:
            renderSprintRace(container, state);
            break;
        case GamePhase.SPRINT_RESULTS:
            renderSprintResults(container, state);
            break;
        case GamePhase.TIRE_SELECTION:
            renderTireSelection(container, state);
            break;
        case GamePhase.RACE_IN_PROGRESS:
            renderRaceInProgress(container, state);
            break;
        case GamePhase.RACE_RESULTS:
            renderRaceResults(container, state);
            break;
        case GamePhase.SEASON_END:
            renderSeasonEnd(container, state);
            break;
        case GamePhase.TRANSFER_WINDOW:
            renderTransferWindow(container, state);
            break;
        default:
            renderMainMenu(container, state);
    }

    // Add game controls bar after content is rendered
    const gameContainer = container.querySelector('.game-container');
    if (gameContainer) {
        gameContainer.insertAdjacentHTML('afterbegin', renderGameControls(state));
        attachGameControlListeners(container, state);
    }
}

/**
 * Waiting for Players Screen (Multiplayer)
 */
function renderWaitingForPlayers(container, state) {
    container.innerHTML = `
        <div class="game-container">
            <div class="game-header text-center">
                <h1>Waiting for Players</h1>
                <p class="text-secondary">Share the game link with another player to start</p>
            </div>

            <div class="game-content text-center">
                <div class="card">
                    <div class="waiting-animation">
                        <div class="spinner"></div>
                    </div>
                    <h3>Players: ${state.player_count}/2</h3>
                    <div class="players-list mt-lg">
                        ${state.players?.map(p => `
                            <div class="player-card ${p.player_id === state.your_player_id ? 'you' : ''}">
                                <span class="player-name">${escapeHtml(p.username)}</span>
                                <span class="player-team">${escapeHtml(p.team_name)}</span>
                            </div>
                        `).join('') || '<p>No players yet</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * Team Name Selection Screen
 */
function renderTeamNameSelection(container, state) {
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const hasSetName = myPlayer?.has_set_team_name;

    if (hasSetName) {
        container.innerHTML = `
            <div class="game-container">
                <div class="game-header text-center">
                    <h1>Team Name Set!</h1>
                    <p class="text-secondary">Waiting for other player to name their team...</p>
                </div>
                <div class="game-content text-center">
                    <div class="card">
                        <div class="waiting-animation">
                            <div class="spinner"></div>
                        </div>
                        <p class="mt-lg">Your team: <strong>${escapeHtml(myPlayer.team_name)}</strong></p>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header text-center">
                <h1>Create Your Team</h1>
                <p class="text-secondary">Welcome to F1! Choose a name for your new racing team.</p>
            </div>

            <div class="game-content">
                <div class="card team-name-card">
                    <div class="team-name-intro">
                        <h3>Your F1 Journey Begins</h3>
                        <p>You're starting as a <strong>backmarker team</strong> - a new constructor entering Formula 1.</p>
                        <p>Your car won't be competitive against the big teams yet, and top drivers won't be interested in joining you.</p>
                        <p>But with smart management, good results, and car development, you can build your team's prestige and attract better talent!</p>
                    </div>

                    <div class="team-name-form mt-xl">
                        <label for="team-name-input">Team Name</label>
                        <input type="text" id="team-name-input" class="form-input" placeholder="Enter your team name (3-30 characters)" maxlength="30" />
                        <p class="input-hint">Examples: "Velocity Racing", "Phoenix F1", "Apex Motorsport"</p>

                        <button class="btn btn-primary btn-lg btn-block mt-lg" id="set-team-name-btn">
                            Create Team
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Set team name handler
    document.getElementById('set-team-name-btn')?.addEventListener('click', async () => {
        const input = document.getElementById('team-name-input');
        const teamName = input?.value?.trim();

        if (!teamName || teamName.length < 3 || teamName.length > 30) {
            showAlert(container.querySelector('.game-content'), 'Team name must be 3-30 characters', 'error');
            return;
        }

        const btn = document.getElementById('set-team-name-btn');
        setButtonLoading(btn, true);

        try {
            const newState = await api.post(`/gameplay/${state.game_id}/set-team-name`, {
                team_name: teamName
            });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    // Enter key handler
    document.getElementById('team-name-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            document.getElementById('set-team-name-btn')?.click();
        }
    });
}

/**
 * Sponsor Selection Screen
 */
function renderSponsorSelection(container, state) {
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const hasSelected = myPlayer?.has_selected_sponsor;

    if (hasSelected) {
        container.innerHTML = `
            <div class="game-container">
                <div class="game-header text-center">
                    <h1>Sponsor Selected!</h1>
                    <p class="text-secondary">Waiting for other player to select their sponsor...</p>
                </div>
                <div class="game-content text-center">
                    <div class="card">
                        <div class="waiting-animation">
                            <div class="spinner"></div>
                        </div>
                        <h3>Your sponsor: ${escapeHtml(state.player_team?.sponsor?.name || 'Selected')}</h3>
                    </div>
                </div>
            </div>
        `;
        return;
    }

    const sponsors = state.available_sponsors || [];

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Select Your Sponsor</h1>
                <p class="text-secondary">Choose a sponsor to fund your team. Higher tiers have tougher objectives but bigger rewards.</p>
            </div>

            <div class="game-content">
                <div class="sponsors-grid">
                    ${sponsors.map(sponsor => `
                        <div class="card sponsor-card sponsor-${sponsor.tier}" data-sponsor-id="${sponsor.id}">
                            <div class="sponsor-tier">${sponsor.tier.toUpperCase()}</div>
                            <h3>${escapeHtml(sponsor.name)}</h3>
                            <div class="sponsor-details">
                                <div class="sponsor-stat">
                                    <span class="label">Per Race</span>
                                    <span class="value">$${sponsor.payment_per_race.toFixed(1)}M</span>
                                </div>
                                <div class="sponsor-stat">
                                    <span class="label">Season Bonus</span>
                                    <span class="value">$${sponsor.season_bonus.toFixed(0)}M</span>
                                </div>
                            </div>
                            <div class="sponsor-objective">
                                <strong>Objective:</strong>
                                <p>${escapeHtml(sponsor.objective?.description || 'Meet performance targets')}</p>
                            </div>
                            <button class="btn btn-primary btn-block select-sponsor-btn" data-sponsor-id="${sponsor.id}">
                                Select ${escapeHtml(sponsor.name)}
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    // Event listeners
    container.querySelectorAll('.select-sponsor-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const sponsorId = btn.dataset.sponsorId;
            setButtonLoading(btn, true);
            try {
                const newState = await api.post(`/gameplay/${state.game_id}/select-sponsor`, {
                    sponsor_id: sponsorId
                });
                renderGameScreen(container, newState);
            } catch (error) {
                showAlert(container.querySelector('.game-content'), error.message, 'error');
                setButtonLoading(btn, false);
            }
        });
    });
}

/**
 * Driver Selection Screen (Team Setup) with Turn-Based Support
 */
function renderDriverSelection(container, state) {
    const teamDriverCount = state.player_team?.drivers?.length || 0;
    const driversNeeded = 2 - teamDriverCount;
    const isYourTurn = state.is_your_turn;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Team Setup</h1>
                <p class="text-secondary">Sign ${driversNeeded} driver${driversNeeded !== 1 ? 's' : ''} to complete your team</p>
            </div>

            <div class="game-content">
                ${!isYourTurn && state.is_multiplayer ? `
                    <div class="alert alert-info mb-lg">
                        Waiting for ${escapeHtml(state.turn_info?.current_player_username || 'other player')} to make their pick...
                    </div>
                ` : ''}

                <div class="card mb-lg">
                    <div class="flex" style="justify-content: space-between; align-items: center;">
                        <h3>${escapeHtml(state.player_team?.name || 'Your Team')}</h3>
                        <span class="stat-pill" style="font-size: var(--font-lg);">Budget: <strong>$${state.player_team?.budget?.toFixed(1) || 0}M</strong></span>
                    </div>
                    ${state.player_team?.drivers?.length > 0 ? `
                        <div class="mt-md">
                            <h4>Signed Drivers:</h4>
                            ${state.player_team.drivers.map(d => `
                                <div class="driver-card-mini">
                                    <span class="driver-name">${escapeHtml(d.name)}</span>
                                    <span class="driver-rating">OVR: ${calculateOverall(d.stats)}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>

                ${state.opponent_team ? `
                    <div class="card mb-lg opponent-card">
                        <h4>Opponent: ${escapeHtml(state.opponent_team.name)}</h4>
                        <p>Drivers: ${state.opponent_team.drivers?.map(d => escapeHtml(d.name)).join(', ') || 'None signed'}</p>
                    </div>
                ` : ''}

                <h3>Available Drivers (${state.market_drivers?.length || 0})</h3>
                <p class="text-secondary mb-md">Drivers will only join teams that match their prestige expectations. Build your reputation to attract better talent!</p>
                <div class="card mt-md">
                    <div style="overflow-x: auto;">
                        <table class="driver-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Age</th>
                                    <th>Nat</th>
                                    <th>OVR</th>
                                    <th>POT</th>
                                    <th>Interest</th>
                                    <th>PAC</th>
                                    <th>OVT</th>
                                    <th>DEF</th>
                                    <th>CON</th>
                                    <th>TIR</th>
                                    <th>WET</th>
                                    <th>Value</th>
                                    <th>Salary</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                ${state.market_drivers?.map((driver, idx) => {
                                    const budget = state.player_team?.budget || 0;
                                    const minCost = state.min_driver_cost || 0;
                                    const driversNeeded = state.drivers_needed || 2;
                                    const cantAfford = driver.market_value > budget;
                                    const wouldLeaveShort = driversNeeded > 1 && (budget - driver.market_value) < minCost;
                                    const isUnaffordable = cantAfford || wouldLeaveShort;
                                    const notInterested = driver.interested === false;
                                    const cannotSign = !isYourTurn || isUnaffordable || notInterested;

                                    return `<tr class="${isUnaffordable ? 'unaffordable' : ''} ${notInterested ? 'not-interested' : ''}">
                                        <td><strong>${escapeHtml(driver.name)}</strong></td>
                                        <td>${driver.age}</td>
                                        <td>${escapeHtml(driver.nationality.substring(0, 3).toUpperCase())}</td>
                                        <td><span class="stat-badge">${calculateOverall(driver.stats)}</span></td>
                                        <td><span class="stat-badge potential">${driver.potential}</span></td>
                                        <td>
                                            ${driver.interested !== false ?
                                                `<span class="interest-badge interested" title="Willing to join your team">Interested</span>` :
                                                `<span class="interest-badge not-interested" title="${escapeHtml(driver.interest_reason || 'Not interested')}">${escapeHtml(driver.interest_reason || 'Not interested')}</span>`
                                            }
                                        </td>
                                        <td>${driver.stats.pace}</td>
                                        <td>${driver.stats.overtaking}</td>
                                        <td>${driver.stats.defending}</td>
                                        <td>${driver.stats.consistency}</td>
                                        <td>${driver.stats.tire_management}</td>
                                        <td>${driver.stats.wet_skill}</td>
                                        <td class="price-tag">$${driver.market_value?.toFixed(1)}M</td>
                                        <td>$${driver.salary?.toFixed(1)}M</td>
                                        <td>
                                            <button class="btn ${cannotSign ? 'btn-secondary' : 'btn-primary'} btn-sm sign-driver-btn"
                                                    data-driver-id="${driver.id}"
                                                    data-driver-name="${escapeHtml(driver.name)}"
                                                    data-salary="${driver.salary}"
                                                    data-value="${driver.market_value}"
                                                    ${cannotSign ? 'disabled' : ''}
                                                    title="${!isYourTurn ? 'Not your turn' : notInterested ? 'Driver not interested in joining' : cantAfford ? 'Cannot afford' : wouldLeaveShort ? 'Not enough left for 2nd driver' : 'Sign driver'}">
                                                ${!isYourTurn ? 'Wait' : notInterested ? 'No' : cantAfford ? 'Too $$$' : wouldLeaveShort ? 'Need 2' : 'Sign'}
                                            </button>
                                        </td>
                                    </tr>`;
                                }).join('') || '<tr><td colspan="15">No drivers available</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Add event listeners for signing drivers
    container.querySelectorAll('.sign-driver-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const driverId = btn.dataset.driverId;
            const driverName = btn.dataset.driverName;
            const salary = parseFloat(btn.dataset.salary);

            const confirmed = await modalConfirm(`Sign ${driverName} for $${salary.toFixed(1)}M/year?`, 'Sign Driver');
            if (confirmed) {
                setButtonLoading(btn, true);
                try {
                    const newState = await api.post(`/gameplay/${state.game_id}/sign-driver`, {
                        driver_id: driverId,
                        salary: salary,
                        years: 2,
                        is_number_one: (state.player_team?.drivers?.length || 0) === 0
                    });
                    renderGameScreen(container, newState);
                } catch (error) {
                    showAlert(container.querySelector('.game-content'), error.message, 'error');
                    setButtonLoading(btn, false);
                }
            }
        });
    });
}

/**
 * Main Menu Screen - Team Hub
 */
function renderMainMenu(container, state) {
    const track = state.current_track;
    const team = state.player_team;
    const car = team?.car;
    const drivers = team?.drivers || [];
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    // Calculate car overall
    const carOverall = car ? Math.round(
        (car.downforce || 0) * 0.18 +
        (car.aero_efficiency || 0) * 0.18 +
        (car.chassis || 0) * 0.22 +
        (car.power_unit || 0) * 0.18 +
        (car.reliability || 0) * 0.12 +
        (car.tire_cooling || 0) * 0.12
    ) : 0;

    container.innerHTML = `
        <div class="game-container hub-container">
            <!-- Team Header -->
            <div class="hub-header">
                <div class="hub-team-info">
                    <h1 class="hub-team-name">${escapeHtml(team?.name || 'Your Team')}</h1>
                    <div class="hub-season-info">
                        <span class="season-badge">Season ${state.current_season}</span>
                        <span class="race-progress">Race ${state.current_race} / ${state.total_races}</span>
                    </div>
                </div>
                <div class="hub-stats">
                    <div class="hub-stat">
                        <span class="hub-stat-value">$${team?.budget?.toFixed(1) || 0}M</span>
                        <span class="hub-stat-label">Budget</span>
                    </div>
                    <div class="hub-stat">
                        <span class="hub-stat-value">${team?.season_points || 0}</span>
                        <span class="hub-stat-label">Points</span>
                    </div>
                    <div class="hub-stat">
                        <span class="hub-stat-value">${team?.race_wins || 0}</span>
                        <span class="hub-stat-label">Wins</span>
                    </div>
                </div>
            </div>

            <div class="hub-content">
                <!-- Main Hub Grid -->
                <div class="hub-grid">
                    <!-- Left Column: Drivers & Car -->
                    <div class="hub-left">
                        <!-- Drivers Section -->
                        <div class="hub-section">
                            <h3 class="hub-section-title">Drivers</h3>
                            <div class="hub-drivers">
                                ${drivers.map((driver, idx) => `
                                    <div class="hub-driver-card">
                                        <div class="hub-driver-number">${idx + 1}</div>
                                        <div class="hub-driver-info">
                                            <span class="hub-driver-name">${escapeHtml(driver.name)}</span>
                                            <span class="hub-driver-stats">
                                                OVR ${calculateOverall(driver.stats)} |
                                                ${driver.season_points || 0} pts
                                            </span>
                                        </div>
                                        <div class="hub-driver-morale" title="Morale: ${driver.morale || 75}%">
                                            <div class="mini-morale-bar">
                                                <div class="mini-morale-fill" style="width: ${driver.morale || 75}%; background: ${getMoraleColor(driver.morale || 75)}"></div>
                                            </div>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>

                        <!-- Car Section -->
                        <div class="hub-section">
                            <div class="hub-section-header">
                                <h3 class="hub-section-title">Car Performance</h3>
                                <span class="car-overall-badge">OVR ${carOverall}</span>
                            </div>
                            <div class="hub-car-stats">
                                <div class="hub-car-stat">
                                    <span class="car-stat-name">Downforce</span>
                                    <div class="car-stat-bar"><div class="car-stat-fill" style="width: ${car?.downforce || 0}%"></div></div>
                                    <span class="car-stat-val">${car?.downforce || 0}</span>
                                </div>
                                <div class="hub-car-stat">
                                    <span class="car-stat-name">Aero</span>
                                    <div class="car-stat-bar"><div class="car-stat-fill" style="width: ${car?.aero_efficiency || 0}%"></div></div>
                                    <span class="car-stat-val">${car?.aero_efficiency || 0}</span>
                                </div>
                                <div class="hub-car-stat">
                                    <span class="car-stat-name">Chassis</span>
                                    <div class="car-stat-bar"><div class="car-stat-fill" style="width: ${car?.chassis || 0}%"></div></div>
                                    <span class="car-stat-val">${car?.chassis || 0}</span>
                                </div>
                                <div class="hub-car-stat">
                                    <span class="car-stat-name">Power</span>
                                    <div class="car-stat-bar"><div class="car-stat-fill" style="width: ${car?.power_unit || 0}%"></div></div>
                                    <span class="car-stat-val">${car?.power_unit || 0}</span>
                                </div>
                                <div class="hub-car-stat">
                                    <span class="car-stat-name">Reliability</span>
                                    <div class="car-stat-bar"><div class="car-stat-fill" style="width: ${car?.reliability || 0}%"></div></div>
                                    <span class="car-stat-val">${car?.reliability || 0}</span>
                                </div>
                            </div>
                            <button class="btn btn-secondary btn-block mt-md" id="upgrades-btn">
                                Upgrade Car
                            </button>
                        </div>
                    </div>

                    <!-- Right Column: Race & Navigation -->
                    <div class="hub-right">
                        <!-- Next Race Card -->
                        ${track ? `
                            <div class="hub-race-card">
                                <div class="race-card-header">
                                    <span class="race-round">Round ${state.current_race}</span>
                                    <span class="race-flag">${getCountryFlag(track.country)}</span>
                                </div>
                                <h2 class="race-track-name">${escapeHtml(track.name)}</h2>
                                <p class="race-location">${escapeHtml(track.city)}, ${escapeHtml(track.country)}</p>

                                <div class="race-details">
                                    <div class="race-detail">
                                        <span class="detail-value">${track.laps}</span>
                                        <span class="detail-label">Laps</span>
                                    </div>
                                    <div class="race-detail">
                                        <span class="detail-value">${formatTrackType(track.track_type)}</span>
                                        <span class="detail-label">Type</span>
                                    </div>
                                    <div class="race-detail">
                                        <span class="detail-value">${getTireWearLevel(track.tire_degradation)}</span>
                                        <span class="detail-label">Tire Wear</span>
                                    </div>
                                </div>

                                ${isMultiplayer ? `
                                    <div class="ready-status">
                                        <div class="ready-player ${imReady ? 'is-ready' : ''}">
                                            <span class="ready-name">You</span>
                                            <span class="ready-indicator">${imReady ? 'READY' : 'NOT READY'}</span>
                                        </div>
                                        <div class="ready-player ${opponentReady ? 'is-ready' : ''}">
                                            <span class="ready-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                                            <span class="ready-indicator">${opponentReady ? 'READY' : 'NOT READY'}</span>
                                        </div>
                                    </div>
                                    ${!imReady ? `
                                        <button class="btn btn-success btn-lg btn-block" id="ready-btn">
                                            Ready for Race Weekend
                                        </button>
                                    ` : bothReady ? `
                                        <button class="btn btn-primary btn-lg btn-block" id="start-race-btn">
                                            Start Race Weekend
                                        </button>
                                    ` : `
                                        <div class="waiting-opponent">
                                            <div class="spinner-small"></div>
                                            <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')}...</span>
                                        </div>
                                    `}
                                ` : `
                                    <button class="btn btn-primary btn-lg btn-block" id="start-race-btn">
                                        Start Race Weekend
                                    </button>
                                `}
                            </div>
                        ` : ''}

                        <!-- Quick Nav -->
                        <div class="hub-nav">
                            <button class="hub-nav-btn" id="standings-btn">
                                <span class="nav-icon">🏆</span>
                                <span class="nav-label">Standings</span>
                            </button>
                            <button class="hub-nav-btn" id="calendar-btn">
                                <span class="nav-icon">📅</span>
                                <span class="nav-label">Calendar</span>
                            </button>
                            <button class="hub-nav-btn" id="team-btn">
                                <span class="nav-icon">👥</span>
                                <span class="nav-label">Team Info</span>
                            </button>
                            <button class="hub-nav-btn" id="rivals-btn">
                                <span class="nav-icon">🏎️</span>
                                <span class="nav-label">Other Teams</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Event listeners
    document.getElementById('ready-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready`, { ready: true });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.hub-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('start-race-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('start-race-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/start-race-weekend`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.hub-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('team-btn')?.addEventListener('click', () => renderTeamScreen(container, state));
    document.getElementById('upgrades-btn')?.addEventListener('click', () => renderUpgradesScreen(container, state));
    document.getElementById('standings-btn')?.addEventListener('click', () => renderStandingsScreen(container, state));
    document.getElementById('calendar-btn')?.addEventListener('click', () => renderCalendarScreen(container, state));
    document.getElementById('rivals-btn')?.addEventListener('click', () => renderOtherTeamsScreen(container, state));

    // Auto-refresh in multiplayer when ready (to detect when other player advances phase)
    if (isMultiplayer && imReady) {
        startRefreshInterval(state.game_id, container);
    }
}

function getCountryFlag(country) {
    const flags = {
        'Bahrain': '🇧🇭', 'Saudi Arabia': '🇸🇦', 'Australia': '🇦🇺', 'Japan': '🇯🇵',
        'China': '🇨🇳', 'USA': '🇺🇸', 'Italy': '🇮🇹', 'Monaco': '🇲🇨', 'Canada': '🇨🇦',
        'Spain': '🇪🇸', 'Austria': '🇦🇹', 'UK': '🇬🇧', 'Hungary': '🇭🇺', 'Belgium': '🇧🇪',
        'Netherlands': '🇳🇱', 'Singapore': '🇸🇬', 'Mexico': '🇲🇽', 'Brazil': '🇧🇷',
        'Qatar': '🇶🇦', 'UAE': '🇦🇪', 'Azerbaijan': '🇦🇿'
    };
    return flags[country] || '🏁';
}

/**
 * Car Upgrades Screen
 */
function renderUpgradesScreen(container, state) {
    const upgrades = state.upgrade_options || [];
    const budget = state.player_team?.budget || 0;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Car Upgrades</h1>
                <span class="stat-pill">Budget: $${budget.toFixed(1)}M</span>
            </div>

            <div class="game-content">
                <p class="text-secondary mb-lg">Upgrade individual car stats. Cost increases with stat value.</p>

                <div class="upgrades-grid">
                    ${upgrades.map(upgrade => `
                        <div class="card upgrade-card ${!upgrade.can_afford ? 'unaffordable' : ''}">
                            <h4>${escapeHtml(upgrade.display_name)}</h4>
                            <div class="upgrade-stat">
                                <div class="stat-bar-container">
                                    <div class="stat-bar" style="width: ${upgrade.current_value}%"></div>
                                </div>
                                <span class="stat-value">${upgrade.current_value} -> ${upgrade.new_value}</span>
                            </div>
                            <div class="upgrade-cost">
                                Cost: $${upgrade.upgrade_cost.toFixed(1)}M
                            </div>
                            <button class="btn ${upgrade.can_afford ? 'btn-primary' : 'btn-secondary'} btn-block upgrade-btn"
                                    data-stat="${upgrade.stat_name}"
                                    ${!upgrade.can_afford ? 'disabled' : ''}>
                                ${upgrade.can_afford ? 'Upgrade' : 'Not Enough Budget'}
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => renderMainMenu(container, state));

    container.querySelectorAll('.upgrade-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const statName = btn.dataset.stat;
            setButtonLoading(btn, true);
            try {
                const newState = await api.post(`/gameplay/${state.game_id}/upgrade-car`, {
                    stat_name: statName,
                    points: 1
                });
                renderUpgradesScreen(container, newState);
            } catch (error) {
                showAlert(container.querySelector('.game-content'), error.message, 'error');
                setButtonLoading(btn, false);
            }
        });
    });
}

/**
 * Development Tree Screen
 */
function renderDevelopmentScreen(container, state) {
    const tree = state.development_tree;
    const budget = state.player_team?.budget || 0;

    if (!tree) {
        container.innerHTML = `
            <div class="game-container">
                <div class="game-header">
                    <button class="btn btn-secondary" id="back-btn">Back</button>
                    <h1>Development Tree</h1>
                </div>
                <div class="game-content">
                    <p>Development tree not available.</p>
                </div>
            </div>
        `;
        document.getElementById('back-btn')?.addEventListener('click', () => renderMainMenu(container, state));
        return;
    }

    const categories = ['aerodynamics', 'power_unit', 'chassis', 'tire_management'];
    const categoryNames = {
        aerodynamics: 'Aerodynamics',
        power_unit: 'Power Unit',
        chassis: 'Chassis',
        tire_management: 'Tire Management'
    };

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Development Tree</h1>
                <span class="stat-pill">Budget: $${budget.toFixed(1)}M</span>
            </div>

            <div class="game-content">
                <p class="text-secondary mb-md">Active developments: ${tree.active_developments?.length || 0}/2</p>

                <div class="dev-tabs">
                    ${categories.map((cat, i) => `
                        <button class="tab-btn ${i === 0 ? 'active' : ''}" data-category="${cat}">
                            ${categoryNames[cat]}
                        </button>
                    `).join('')}
                </div>

                ${categories.map((cat, i) => `
                    <div class="dev-category" id="cat-${cat}" style="display: ${i === 0 ? 'block' : 'none'}">
                        <div class="dev-nodes-grid">
                            ${tree.nodes?.filter(n => n.category === cat).map(node => {
                                const isCompleted = tree.completed_developments?.includes(node.id);
                                const isActive = tree.active_developments?.includes(node.id);
                                const isLocked = node.is_locked;
                                const prereqsMet = node.prerequisites.every(p => tree.completed_developments?.includes(p));
                                const canStart = !isCompleted && !isActive && !isLocked && prereqsMet &&
                                                tree.active_developments?.length < 2 && budget >= node.cost;

                                let statusClass = '';
                                let statusText = '';
                                if (isCompleted) { statusClass = 'completed'; statusText = 'Completed'; }
                                else if (isActive) { statusClass = 'in-progress'; statusText = `${node.races_remaining} races left`; }
                                else if (isLocked) { statusClass = 'locked'; statusText = 'Locked'; }
                                else if (!prereqsMet) { statusClass = 'locked'; statusText = 'Prerequisites needed'; }

                                return `
                                    <div class="card dev-node ${statusClass}">
                                        <div class="dev-node-branch">${node.branch}</div>
                                        <h4>${escapeHtml(node.name)}</h4>
                                        <p class="dev-description">${escapeHtml(node.description)}</p>
                                        <div class="dev-effects">
                                            ${Object.entries(node.effects || {}).map(([stat, val]) => `
                                                <span class="effect ${val > 0 ? 'positive' : 'negative'}">
                                                    ${stat.replace('_', ' ')}: ${val > 0 ? '+' : ''}${val}
                                                </span>
                                            `).join('')}
                                        </div>
                                        <div class="dev-meta">
                                            <span>Cost: $${node.cost}M</span>
                                            <span>Time: ${node.development_time} races</span>
                                        </div>
                                        ${statusText ? `<div class="dev-status">${statusText}</div>` : ''}
                                        ${canStart ? `
                                            <button class="btn btn-primary btn-sm btn-block start-dev-btn" data-node-id="${node.id}">
                                                Start Research
                                            </button>
                                        ` : ''}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => renderMainMenu(container, state));

    // Tab switching
    container.querySelectorAll('.tab-btn[data-category]').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.tab-btn[data-category]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const cat = btn.dataset.category;
            categories.forEach(c => {
                document.getElementById(`cat-${c}`).style.display = c === cat ? 'block' : 'none';
            });
        });
    });

    // Start development
    container.querySelectorAll('.start-dev-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const nodeId = btn.dataset.nodeId;
            setButtonLoading(btn, true);
            try {
                const newState = await api.post(`/gameplay/${state.game_id}/start-development`, {
                    node_id: nodeId
                });
                renderDevelopmentScreen(container, newState);
            } catch (error) {
                showAlert(container.querySelector('.game-content'), error.message, 'error');
                setButtonLoading(btn, false);
            }
        });
    });
}

/**
 * Inbox Screen
 */
function renderInboxScreen(container, state) {
    const messages = state.inbox || [];

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Inbox</h1>
            </div>

            <div class="game-content">
                ${messages.length === 0 ? '<p class="text-muted">No messages</p>' : ''}
                <div class="inbox-list">
                    ${messages.map(msg => `
                        <div class="card inbox-message ${msg.is_read ? 'read' : 'unread'} priority-${msg.priority}">
                            <div class="message-header">
                                <span class="message-type">${msg.type.replace('_', ' ')}</span>
                                <span class="message-time">${formatMessageTime(msg.timestamp)}</span>
                            </div>
                            <h4 class="message-subject">${escapeHtml(msg.subject)}</h4>
                            <p class="message-body">${escapeHtml(msg.body)}</p>
                            <div class="message-footer">
                                <span class="message-sender">From: ${escapeHtml(msg.sender)}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => renderMainMenu(container, state));
}

function formatMessageTime(timestamp) {
    try {
        const date = new Date(timestamp);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch {
        return timestamp;
    }
}

/**
 * Q1 Qualifying Screen - All drivers, slowest eliminated
 */
function renderQualifyingQ1(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;
    const isSprintWeekend = state.current_track?.is_sprint_weekend;

    // Q1 results - all drivers, slowest are eliminated
    const q1Results = state.qualifying_results || [];
    const totalDrivers = q1Results.length;
    const eliminatedCount = q1Results.filter(r => r.eliminated_in === 'Q1').length;
    const advancingTo = totalDrivers - eliminatedCount;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Q1 Results</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}${isSprintWeekend ? ' - Sprint Weekend' : ''}</p>
                <div class="quali-stage-indicator">
                    <span class="quali-stage active">Q1</span>
                    <span class="quali-stage">Q2</span>
                    <span class="quali-stage">Q3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Top ${advancingTo} advance to Q2 | ${eliminatedCount} drivers eliminated</span>
                </div>

                <div class="card">
                    <table class="results-table quali-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Q1 Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q1Results.map((result, idx) => {
                                const isEliminated = result.eliminated_in === 'Q1';
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${isEliminated ? 'eliminated-row' : ''}">
                                        <td class="pos-cell">${result.position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q1_time || result.lap_time}</td>
                                        <td>${isEliminated ? '<span class="status-eliminated">OUT</span>' : '<span class="status-through">Q2</span>'}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to Q2', 'advance-qualifying')}
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Q2 Qualifying Screen - Q1 survivors, slowest eliminated
 */
function renderQualifyingQ2(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;
    const isSprintWeekend = state.current_track?.is_sprint_weekend;

    // Q2 results - drivers who survived Q1
    const q2Results = (state.qualifying_results || []).filter(r => !r.eliminated_in || r.eliminated_in !== 'Q1');
    const eliminatedCount = q2Results.filter(r => r.eliminated_in === 'Q2').length;
    const advancingTo = q2Results.length - eliminatedCount;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Q2 Results</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}${isSprintWeekend ? ' - Sprint Weekend' : ''}</p>
                <div class="quali-stage-indicator">
                    <span class="quali-stage completed">Q1</span>
                    <span class="quali-stage active">Q2</span>
                    <span class="quali-stage">Q3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Top ${advancingTo} advance to Q3 | ${eliminatedCount} drivers eliminated</span>
                    <span class="quali-info tire-info">Top ${advancingTo} must start race on Q2 tires!</span>
                </div>

                <div class="card">
                    <table class="results-table quali-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Q2 Time</th>
                                <th>Tire</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q2Results.map((result, idx) => {
                                const q2Position = idx + 1;
                                const isEliminated = result.eliminated_in === 'Q2';
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${isEliminated ? 'eliminated-row' : ''}">
                                        <td class="pos-cell">${q2Position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q2_time || result.lap_time}</td>
                                        <td>${result.q2_tire ? `<span class="tire-badge tire-${result.q2_tire}">${result.q2_tire.charAt(0).toUpperCase()}</span>` : '-'}</td>
                                        <td>${isEliminated ? '<span class="status-eliminated">OUT</span>' : '<span class="status-through">Q3</span>'}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="6">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to Q3', 'advance-qualifying')}
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Q3 Qualifying Screen - Top 10 fight for pole
 */
function renderQualifyingQ3(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;
    const isSprintWeekend = state.current_track?.is_sprint_weekend;

    // Q3 results - top 10 only
    const q3Results = (state.qualifying_results || []).filter(r => !r.eliminated_in);

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Q3 Results - Final Grid</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}${isSprintWeekend ? ' - Sprint Weekend' : ''}</p>
                <div class="quali-stage-indicator">
                    <span class="quali-stage completed">Q1</span>
                    <span class="quali-stage completed">Q2</span>
                    <span class="quali-stage active">Q3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Top 10 Shootout for Pole Position!</span>
                </div>

                <div class="card">
                    <h3 class="mb-md">Pole Position Shootout</h3>
                    <table class="results-table quali-table q3-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Q3 Time</th>
                                <th>Gap</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q3Results.slice(0, 10).map((result, idx) => {
                                const poleTime = q3Results[0]?.q3_time || q3Results[0]?.lap_time;
                                const gap = idx === 0 ? '-' : calculateTimeGap(poleTime, result.q3_time || result.lap_time);
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${idx === 0 ? 'pole-position' : ''}">
                                        <td class="pos-cell">${idx === 0 ? '<span class="pole-badge">P</span>' : idx + 1}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q3_time || result.lap_time}</td>
                                        <td class="gap-cell">${gap}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                <!-- Full Grid Preview -->
                <div class="card mt-lg">
                    <h3 class="mb-md">Full Starting Grid</h3>
                    <table class="results-table quali-table">
                        <thead>
                            <tr>
                                <th>Grid</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Best Time</th>
                                <th>Session</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${state.qualifying_results?.map(result => {
                                const session = result.eliminated_in || 'Q3';
                                const bestTime = result.q3_time || result.q2_time || result.q1_time || result.lap_time;
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''}">
                                        <td class="pos-cell">${result.position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${bestTime}</td>
                                        <td><span class="session-badge session-${session.toLowerCase()}">${session}</span></td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${isSprintWeekend ?
                    renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to Sprint Shootout', 'advance-qualifying') :
                    renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to Tire Selection', 'advance-qualifying')
                }
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Helper to render multiplayer sync UI
 */
function renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, continueText, endpoint) {
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);

    if (isMultiplayer) {
        return `
            <div class="sync-status mt-xl">
                <div class="sync-player ${imReady ? 'is-ready' : ''}">
                    <span class="sync-name">You</span>
                    <span class="sync-indicator">${imReady ? 'Ready' : 'Reviewing'}</span>
                </div>
                <div class="sync-player ${opponentReady ? 'is-ready' : ''}">
                    <span class="sync-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                    <span class="sync-indicator">${opponentReady ? 'Ready' : 'Reviewing'}</span>
                </div>
            </div>
            ${!imReady ? `
                <button class="btn btn-success btn-lg btn-block mt-lg" id="ready-btn">
                    Ready to Continue
                </button>
            ` : bothReady ? `
                <button class="btn btn-primary btn-lg btn-block mt-lg" id="continue-btn" data-endpoint="${endpoint}">
                    ${continueText}
                </button>
            ` : `
                <div class="waiting-sync mt-lg">
                    <div class="spinner-small"></div>
                    <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')}...</span>
                </div>
            `}
        `;
    } else {
        return `
            <button class="btn btn-primary btn-lg btn-block mt-xl" id="continue-btn" data-endpoint="${endpoint}">
                ${continueText}
            </button>
        `;
    }
}

/**
 * Attach event listeners for qualifying screens
 */
function attachQualifyingListeners(container, state, isMultiplayer, imReady) {
    document.getElementById('ready-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready`, { ready: true });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('continue-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('continue-btn');
        const endpoint = btn.dataset.endpoint || 'advance-qualifying';
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/${endpoint}`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    if (isMultiplayer && imReady) {
        startRefreshInterval(state.game_id, container);
    }
}

/**
 * Calculate time gap between two lap times (format: "1:23.456")
 */
function calculateTimeGap(poleTime, lapTime) {
    if (!poleTime || !lapTime) return '-';

    const parseTime = (t) => {
        const match = t.match(/(\d+):(\d+)\.(\d+)/);
        if (!match) return 0;
        return parseInt(match[1]) * 60 + parseInt(match[2]) + parseInt(match[3]) / 1000;
    };

    const gap = parseTime(lapTime) - parseTime(poleTime);
    if (gap <= 0) return '-';
    return `+${gap.toFixed(3)}`;
}

// ==================== SPRINT WEEKEND SCREENS ====================

/**
 * Sprint Shootout Q1 - Qualifying for Sprint Race
 */
function renderSprintShootoutQ1(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    const q1Results = state.qualifying_results || [];

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Sprint Shootout - SQ1</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="sprint-badge">SPRINT WEEKEND</div>
                <div class="quali-stage-indicator">
                    <span class="quali-stage active">SQ1</span>
                    <span class="quali-stage">SQ2</span>
                    <span class="quali-stage">SQ3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Sprint Shootout: Bottom 5 eliminated (P16-P20)</span>
                </div>

                <div class="card">
                    <table class="results-table quali-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>SQ1 Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q1Results.map((result, idx) => {
                                const isEliminated = result.position >= 16 || result.eliminated_in === 'Q1';
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${isEliminated ? 'eliminated-row' : ''}">
                                        <td class="pos-cell">${result.position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q1_time || result.lap_time}</td>
                                        <td>${isEliminated ? '<span class="status-eliminated">OUT</span>' : '<span class="status-through">SQ2</span>'}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to SQ2', 'advance-qualifying')}
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Sprint Shootout Q2
 */
function renderSprintShootoutQ2(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    const q2Results = (state.qualifying_results || []).filter(r => !r.eliminated_in || r.eliminated_in !== 'Q1');

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Sprint Shootout - SQ2</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="sprint-badge">SPRINT WEEKEND</div>
                <div class="quali-stage-indicator">
                    <span class="quali-stage completed">SQ1</span>
                    <span class="quali-stage active">SQ2</span>
                    <span class="quali-stage">SQ3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Top 10 advance to SQ3 | Bottom 5 eliminated (P11-P15)</span>
                </div>

                <div class="card">
                    <table class="results-table quali-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>SQ2 Time</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q2Results.map((result, idx) => {
                                const q2Position = idx + 1;
                                const isEliminated = q2Position >= 11 || result.eliminated_in === 'Q2';
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${isEliminated ? 'eliminated-row' : ''}">
                                        <td class="pos-cell">${q2Position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q2_time || result.lap_time}</td>
                                        <td>${isEliminated ? '<span class="status-eliminated">OUT</span>' : '<span class="status-through">SQ3</span>'}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to SQ3', 'advance-qualifying')}
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Sprint Shootout Q3 - Final Sprint Grid
 */
function renderSprintShootoutQ3(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    const q3Results = (state.qualifying_results || []).filter(r => !r.eliminated_in);

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Sprint Shootout - SQ3</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="sprint-badge">SPRINT WEEKEND</div>
                <div class="quali-stage-indicator">
                    <span class="quali-stage completed">SQ1</span>
                    <span class="quali-stage completed">SQ2</span>
                    <span class="quali-stage active">SQ3</span>
                </div>
            </div>

            <div class="game-content">
                <div class="quali-info-bar mb-md">
                    <span class="quali-info">Top 10 Fight for Sprint Pole!</span>
                </div>

                <div class="card">
                    <h3 class="mb-md">Sprint Pole Shootout</h3>
                    <table class="results-table quali-table q3-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>SQ3 Time</th>
                                <th>Gap</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${q3Results.slice(0, 10).map((result, idx) => {
                                const poleTime = q3Results[0]?.q3_time || q3Results[0]?.lap_time;
                                const gap = idx === 0 ? '-' : calculateTimeGap(poleTime, result.q3_time || result.lap_time);
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${idx === 0 ? 'pole-position' : ''}">
                                        <td class="pos-cell">${idx === 0 ? '<span class="pole-badge">P</span>' : idx + 1}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td class="time-cell">${result.q3_time || result.lap_time}</td>
                                        <td class="gap-cell">${gap}</td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${renderMultiplayerSyncUI(state, isMultiplayer, imReady, opponentReady, bothReady, 'Continue to Sprint Grid', 'advance-qualifying')}
            </div>
        </div>
    `;

    attachQualifyingListeners(container, state, isMultiplayer, imReady);
}

/**
 * Sprint Grid Screen - Shows full sprint starting grid
 */
function renderSprintGrid(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;
    const sprintLaps = state.current_track?.sprint_laps || 19;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Sprint Starting Grid</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="sprint-badge">SPRINT RACE - ${sprintLaps} LAPS</div>
            </div>

            <div class="game-content">
                <div class="sprint-info card mb-lg">
                    <h3>Sprint Race Format</h3>
                    <div class="sprint-points-info">
                        <span class="sprint-point">P1: 8pts</span>
                        <span class="sprint-point">P2: 7pts</span>
                        <span class="sprint-point">P3: 6pts</span>
                        <span class="sprint-point">P4: 5pts</span>
                        <span class="sprint-point">P5: 4pts</span>
                        <span class="sprint-point">P6: 3pts</span>
                        <span class="sprint-point">P7: 2pts</span>
                        <span class="sprint-point">P8: 1pt</span>
                    </div>
                    <p class="text-secondary mt-sm">No pit stops required - tyres provided</p>
                </div>

                <div class="card">
                    <h3 class="mb-md">Full Sprint Grid</h3>
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Grid</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Shootout Session</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${state.qualifying_results?.map(result => {
                                const session = result.eliminated_in ? `SQ${result.eliminated_in.charAt(1)}` : 'SQ3';
                                return `
                                    <tr class="${result.player_id === state.your_player_id ? 'player-row your-driver' : ''}">
                                        <td class="pos-cell">${result.position}</td>
                                        <td>${escapeHtml(result.driver_name)}</td>
                                        <td>${escapeHtml(result.team_name)}</td>
                                        <td><span class="session-badge session-${session.toLowerCase()}">${session}</span></td>
                                    </tr>
                                `;
                            }).join('') || '<tr><td colspan="4">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${isMultiplayer ? `
                    <div class="sync-status mt-xl">
                        <div class="sync-player ${imReady ? 'is-ready' : ''}">
                            <span class="sync-name">You</span>
                            <span class="sync-indicator">${imReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                        <div class="sync-player ${opponentReady ? 'is-ready' : ''}">
                            <span class="sync-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                            <span class="sync-indicator">${opponentReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                    </div>
                    ${!imReady ? `
                        <button class="btn btn-success btn-lg btn-block mt-lg" id="ready-btn">
                            Ready for Sprint Race
                        </button>
                    ` : bothReady ? `
                        <button class="btn btn-primary btn-lg btn-block mt-lg" id="start-sprint-btn">
                            Start Sprint Race
                        </button>
                    ` : `
                        <div class="waiting-sync mt-lg">
                            <div class="spinner-small"></div>
                            <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')}...</span>
                        </div>
                    `}
                ` : `
                    <button class="btn btn-primary btn-lg btn-block mt-xl" id="start-sprint-btn">
                        Start Sprint Race
                    </button>
                `}
            </div>
        </div>
    `;

    document.getElementById('ready-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready`, { ready: true });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('start-sprint-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('start-sprint-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/start-sprint-race`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    if (isMultiplayer && imReady) {
        startRefreshInterval(state.game_id, container);
    }
}

// Track sprint race simulation state
let sprintAutoSimulating = false;

/**
 * Sprint Race In Progress Screen
 */
function renderSprintRace(container, state) {
    const raceState = state.race_state;
    const sprintLaps = state.current_track?.sprint_laps || 19;

    // Weather indicator
    const weatherIcon = raceState?.weather === 'light_rain' ? '🌧️' :
                       raceState?.weather === 'heavy_rain' ? '⛈️' : '☀️';
    const weatherText = raceState?.weather?.replace('_', ' ').toUpperCase() || 'DRY';

    container.innerHTML = `
        <div class="game-container race-screen">
            <div class="game-header">
                <div class="race-header-info">
                    <div>
                        <h1>Sprint Race</h1>
                        <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown')}</p>
                        <span class="weather-indicator ${raceState?.weather !== 'dry' ? 'rain-warning' : ''}">${weatherIcon} ${weatherText}</span>
                        ${raceState?.safety_car ? '<span class="safety-car-badge">SAFETY CAR</span>' : ''}
                    </div>
                    <div class="lap-counter">
                        <span class="lap-current">Lap ${raceState?.current_lap || 0}</span>
                        <span class="lap-total">/ ${raceState?.total_laps || sprintLaps}</span>
                    </div>
                </div>
            </div>

            <div class="game-content">
                <div class="race-simulating card mb-lg">
                    <div class="simulating-status">
                        <div class="spinner-small"></div>
                        <span>Sprint Race in progress...</span>
                    </div>
                </div>

                <div class="race-positions card">
                    <table class="race-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Gap</th>
                                <th>Tire</th>
                                <th>Wear</th>
                            </tr>
                        </thead>
                        <tbody id="race-positions">
                            ${renderSprintRacePositions(raceState?.positions || [], state.your_player_id)}
                        </tbody>
                    </table>
                </div>

                <div class="race-events card mt-lg">
                    <h3>Recent Events</h3>
                    <div id="race-events" class="events-list">
                        ${raceState?.events?.slice(-8).map(e => `
                            <div class="event-item event-${e.event_type}">
                                <span class="event-lap">Lap ${e.lap}</span>
                                <span class="event-text">${escapeHtml(e.description)}</span>
                            </div>
                        `).reverse().join('') || '<p class="text-muted">No events yet</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Auto-simulate sprint race (no pit decisions)
    if (!raceState?.is_finished) {
        autoSimulateSprintRace(container, state.game_id);
    }
}

/**
 * Render sprint race positions (no pit stops column)
 */
function renderSprintRacePositions(positions, yourPlayerId) {
    return positions.map(p => `
        <tr class="${p.player_id === yourPlayerId ? 'player-row your-driver' : ''} ${p.status === 'dnf' ? 'dnf-row' : ''}">
            <td class="pos-cell">${p.status === 'dnf' ? 'DNF' : p.position}</td>
            <td>${escapeHtml(p.driver_name)}</td>
            <td class="team-cell">${escapeHtml(p.team_name || '')}</td>
            <td>${p.gap}</td>
            <td><span class="tire-badge tire-${p.tire}">${p.tire.charAt(0).toUpperCase()}</span></td>
            <td>
                <div class="wear-bar">
                    <div class="wear-fill" style="width: ${p.tire_wear}%; background: ${getWearColor(p.tire_wear)}"></div>
                </div>
            </td>
        </tr>
    `).join('');
}

/**
 * Auto-simulate sprint race without pit decisions
 */
async function autoSimulateSprintRace(container, gameId) {
    if (sprintAutoSimulating) return;
    sprintAutoSimulating = true;

    try {
        let state = await api.post(`/gameplay/${gameId}/simulate-sprint-lap`);

        while (state.phase === GamePhase.SPRINT_RACE) {
            const raceState = state.race_state;

            if (raceState?.is_finished || raceState?.current_lap >= raceState?.total_laps) {
                break;
            }

            // Small delay for visual effect
            await new Promise(resolve => setTimeout(resolve, 100));

            // Simulate next lap
            state = await api.post(`/gameplay/${gameId}/simulate-sprint-lap`);
        }

        sprintAutoSimulating = false;
        renderGameScreen(container, state);
    } catch (error) {
        sprintAutoSimulating = false;
        showAlert(container.querySelector('.game-content'), error.message, 'error');
    }
}

/**
 * Sprint Race Results Screen
 */
function renderSprintResults(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    // Sprint points: 8,7,6,5,4,3,2,1 for P1-P8
    const getSprintPoints = (pos) => {
        const sprintPoints = [8, 7, 6, 5, 4, 3, 2, 1];
        return pos <= 8 ? sprintPoints[pos - 1] : 0;
    };

    // Calculate points earned this sprint for each player
    const myDrivers = state.race_state?.positions?.filter(p => p.player_id === state.your_player_id) || [];
    const myPoints = myDrivers.reduce((sum, p) => sum + (p.status !== 'dnf' ? getSprintPoints(p.position) : 0), 0);

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Sprint Race Results</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="sprint-badge">SPRINT COMPLETE</div>
            </div>

            <div class="game-content">
                <div class="race-summary card mb-lg">
                    <h3>Your Sprint Results</h3>
                    <div class="your-results">
                        ${myDrivers.map(p => `
                            <div class="result-driver ${p.status === 'dnf' ? 'dnf' : p.position <= 3 ? 'podium' : ''}">
                                <span class="result-pos">${p.status === 'dnf' ? 'DNF' : `P${p.position}`}</span>
                                <span class="result-name">${escapeHtml(p.driver_name)}</span>
                                <span class="result-points">+${p.status === 'dnf' ? '0' : getSprintPoints(p.position)} pts</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="total-points">Sprint Points: +${myPoints}</div>
                </div>

                <div class="card">
                    <h3>Sprint Classification</h3>
                    <div class="sprint-points-legend mb-md">
                        <span class="text-secondary">Points: P1=8, P2=7, P3=6, P4=5, P5=4, P6=3, P7=2, P8=1</span>
                    </div>
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Points</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${state.race_state?.positions?.map(p => `
                                <tr class="${p.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${p.status === 'dnf' ? 'dnf-row' : ''}">
                                    <td class="pos-cell">${p.status === 'dnf' ? 'DNF' : p.position}</td>
                                    <td>${escapeHtml(p.driver_name)}</td>
                                    <td>${escapeHtml(p.team_name)}</td>
                                    <td>${p.status === 'dnf' ? '0' : getSprintPoints(p.position)}</td>
                                </tr>
                            `).join('') || '<tr><td colspan="4">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${isMultiplayer ? `
                    <div class="sync-status mt-xl">
                        <div class="sync-player ${imReady ? 'is-ready' : ''}">
                            <span class="sync-name">You</span>
                            <span class="sync-indicator">${imReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                        <div class="sync-player ${opponentReady ? 'is-ready' : ''}">
                            <span class="sync-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                            <span class="sync-indicator">${opponentReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                    </div>
                    ${!imReady ? `
                        <button class="btn btn-success btn-lg btn-block mt-lg" id="ready-btn">
                            Ready for Main Race
                        </button>
                    ` : bothReady ? `
                        <button class="btn btn-primary btn-lg btn-block mt-lg" id="continue-btn">
                            Continue to Tire Selection
                        </button>
                    ` : `
                        <div class="waiting-sync mt-lg">
                            <div class="spinner-small"></div>
                            <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')}...</span>
                        </div>
                    `}
                ` : `
                    <button class="btn btn-primary btn-lg btn-block mt-xl" id="continue-btn">
                        Continue to Tire Selection
                    </button>
                `}
            </div>
        </div>
    `;

    document.getElementById('ready-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready`, { ready: true });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('continue-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('continue-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/advance-from-sprint`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    if (isMultiplayer && imReady) {
        startRefreshInterval(state.game_id, container);
    }
}

/**
 * Tire Selection Screen - With sync for multiplayer
 */
function renderTireSelection(container, state) {
    const drivers = state.player_team?.drivers || [];
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const tiresSelected = myPlayer?.has_selected_tires;
    const opponentTiresSelected = otherPlayer?.has_selected_tires;
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    // Weather info
    const weather = state.weather_forecast || 'dry';
    const weatherIcon = weather === 'light_rain' ? '🌧️' : weather === 'heavy_rain' ? '⛈️' : '☀️';
    const weatherText = weather.replace('_', ' ').toUpperCase();
    const isWet = weather !== 'dry';

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Select Starting Tires</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
                <div class="weather-forecast ${isWet ? 'rain-warning' : ''}">
                    <span class="weather-icon">${weatherIcon}</span>
                    <span class="weather-text">${weatherText}</span>
                </div>
            </div>

            <div class="game-content">
                ${!tiresSelected ? `
                    <div class="tire-selection-grid">
                        ${drivers.map((driver, idx) => `
                            <div class="card tire-selection-card" data-driver-id="${driver.id}">
                                <h3>${escapeHtml(driver.name)}</h3>
                                <p class="text-secondary">Grid Position: ${getDriverQualifyingPosition(state, driver.name)}</p>

                                <div class="tire-options mt-lg">
                                    <button class="tire-btn tire-soft selected" data-compound="soft">
                                        <span class="tire-icon">S</span>
                                        <span class="tire-name">Soft</span>
                                        <span class="tire-desc">Fast but wears quickly</span>
                                    </button>
                                    <button class="tire-btn tire-medium" data-compound="medium">
                                        <span class="tire-icon">M</span>
                                        <span class="tire-name">Medium</span>
                                        <span class="tire-desc">Balanced performance</span>
                                    </button>
                                    <button class="tire-btn tire-hard" data-compound="hard">
                                        <span class="tire-icon">H</span>
                                        <span class="tire-name">Hard</span>
                                        <span class="tire-desc">Durable but slower</span>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <button class="btn btn-success btn-lg btn-block mt-xl" id="confirm-tires-btn">
                        Confirm Tire Selection
                    </button>
                ` : `
                    <div class="tires-confirmed card text-center">
                        <h3>Tires Selected!</h3>
                        <p class="text-secondary">Your starting tire choices have been locked in.</p>
                        ${isMultiplayer && !imReady ? `
                            <button class="btn btn-success btn-lg mt-lg" id="ready-to-race-btn">
                                Ready to Race!
                            </button>
                        ` : ''}
                    </div>
                `}

                ${isMultiplayer ? `
                    <div class="sync-status mt-xl">
                        <div class="sync-player ${tiresSelected ? 'is-ready' : ''}">
                            <span class="sync-name">You</span>
                            <span class="sync-indicator">${imReady ? 'Ready!' : tiresSelected ? 'Tires Set' : 'Selecting'}</span>
                        </div>
                        <div class="sync-player ${opponentTiresSelected ? 'is-ready' : ''}">
                            <span class="sync-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                            <span class="sync-indicator">${opponentReady ? 'Ready!' : opponentTiresSelected ? 'Tires Set' : 'Selecting'}</span>
                        </div>
                    </div>
                    ${tiresSelected && imReady && !bothReady ? `
                        <div class="waiting-sync mt-lg">
                            <div class="spinner-small"></div>
                            <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')} to ready up...</span>
                        </div>
                    ` : ''}
                ` : ''}
            </div>
        </div>
    `;

    // Tire selection handlers
    container.querySelectorAll('.tire-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.tire-selection-card');
            card.querySelectorAll('.tire-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });

    // Confirm tires handler
    document.getElementById('confirm-tires-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('confirm-tires-btn');
        setButtonLoading(btn, true);

        try {
            // Submit tire selections for each driver
            for (const driver of drivers) {
                const card = container.querySelector(`[data-driver-id="${driver.id}"]`);
                const selectedTire = card?.querySelector('.tire-btn.selected');
                const compound = selectedTire?.dataset.compound || 'medium';

                await api.post(`/gameplay/${state.game_id}/select-tire`, {
                    driver_id: driver.id,
                    compound: compound
                });
            }

            // Get updated state
            const newState = await api.get(`/gameplay/${state.game_id}/state`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    // Ready to race handler (multiplayer only)
    document.getElementById('ready-to-race-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-to-race-btn');
        setButtonLoading(btn, true);

        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready-to-race`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    // Auto-refresh when waiting for opponent (to detect when other player is ready or race starts)
    if (isMultiplayer && tiresSelected) {
        startRefreshInterval(state.game_id, container);
    }
}

// Track race simulation state
let raceAutoSimulating = false;

/**
 * Race In Progress Screen - Server-controlled with multiplayer sync
 */
function renderRaceInProgress(container, state) {
    const raceState = state.race_state;
    const playerDrivers = state.player_team?.drivers || [];
    const isMultiplayer = state.is_multiplayer;
    const pitStatus = raceState?.pit_decision_status;

    // Get player positions for display
    const playerPositions = raceState?.positions?.filter(p => p.player_id === state.your_player_id && p.status !== 'dnf') || [];

    // Multiplayer pit sync status
    const pausedForPits = pitStatus?.paused_for_pits || false;
    const iNeedToDecide = pitStatus?.i_need_to_decide || false;
    const iHaveConfirmed = pitStatus?.i_have_confirmed || true;
    const waitingForPlayers = pitStatus?.waiting_for_players || [];
    const myDriversNeedingPit = pitStatus?.my_drivers_needing_pit || [];

    // Weather indicator
    const weatherIcon = raceState?.weather === 'light_rain' ? '🌧️' :
                       raceState?.weather === 'heavy_rain' ? '⛈️' : '☀️';
    const weatherText = raceState?.weather?.replace('_', ' ').toUpperCase() || 'DRY';

    // Single player pit decision check (client-side)
    const singlePlayerNeedsPit = !isMultiplayer && checkNeedsPitDecision(playerPositions, raceState);

    // Determine what UI to show
    let pitUI = '';

    if (isMultiplayer && pausedForPits) {
        // MULTIPLAYER: Server-controlled pit sync
        if (iNeedToDecide) {
            // I need to make pit decisions
            pitUI = `
                <div class="pit-alert card mb-lg">
                    <div class="alert-header">
                        <span class="alert-icon">⚠️</span>
                        <h3>Pit Decision Required</h3>
                        <p>Choose to pit or stay out for your drivers</p>
                    </div>
                    <div class="pit-driver-controls">
                        ${playerPositions.filter(p => myDriversNeedingPit.includes(playerDrivers.find(d => d.name === p.driver_name)?.id)).map(p => {
                            const driver = playerDrivers.find(d => d.name === p.driver_name);
                            const gripLevel = getGripLevel(p.tire_wear);
                            return `
                                <div class="pit-driver-card needs-pit" data-driver-id="${driver?.id}">
                                    <div class="pit-driver-info">
                                        <strong>${escapeHtml(p.driver_name)}</strong>
                                        <span class="pit-status">P${p.position} | ${p.tire.toUpperCase()} | Wear: ${p.tire_wear}% (${gripLevel})</span>
                                    </div>
                                    <div class="pit-buttons">
                                        ${raceState?.weather === 'dry' ? `
                                            <button class="btn btn-sm pit-btn tire-soft" data-driver="${driver?.id}" data-compound="soft">Soft</button>
                                            <button class="btn btn-sm pit-btn tire-medium" data-driver="${driver?.id}" data-compound="medium">Medium</button>
                                            <button class="btn btn-sm pit-btn tire-hard" data-driver="${driver?.id}" data-compound="hard">Hard</button>
                                        ` : `
                                            <button class="btn btn-sm pit-btn tire-intermediate" data-driver="${driver?.id}" data-compound="intermediate">Inters</button>
                                            <button class="btn btn-sm pit-btn tire-wet" data-driver="${driver?.id}" data-compound="wet">Wets</button>
                                        `}
                                        <button class="btn btn-sm btn-secondary skip-pit-btn" data-driver="${driver?.id}">Stay Out</button>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                    <button class="btn btn-primary btn-block mt-lg" id="confirm-decisions-btn">
                        Confirm Decisions
                    </button>
                </div>
            `;
        } else if (waitingForPlayers.length > 0) {
            // Waiting for opponent to make their decisions
            pitUI = `
                <div class="pit-alert card mb-lg waiting-opponent-pit">
                    <div class="alert-header">
                        <div class="spinner-small"></div>
                        <h3>Waiting for Opponent</h3>
                        <p>Waiting for ${escapeHtml(waitingForPlayers.join(', '))} to make pit decisions...</p>
                    </div>
                </div>
            `;
        } else if (!iHaveConfirmed) {
            // I haven't confirmed yet but have no drivers needing pit
            pitUI = `
                <div class="pit-alert card mb-lg">
                    <div class="alert-header">
                        <span class="alert-icon">⏳</span>
                        <h3>Pit Stop Window</h3>
                        <p>Your opponent needs to make a pit decision. You can wait or continue when ready.</p>
                    </div>
                    <button class="btn btn-primary btn-block mt-lg" id="confirm-decisions-btn">
                        Continue
                    </button>
                </div>
            `;
        }
    } else if (!isMultiplayer && singlePlayerNeedsPit) {
        // SINGLE PLAYER: Client-side pit decision
        pitUI = `
            <div class="pit-alert card mb-lg">
                <div class="alert-header">
                    <span class="alert-icon">⚠️</span>
                    <h3>Pit Stop Recommended</h3>
                    <p>One or more drivers have high tire wear or wrong tires for conditions</p>
                </div>
                <div class="pit-driver-controls">
                    ${playerPositions.filter(p => p.tire_wear >= 70 || (raceState?.weather !== 'dry' && !['intermediate', 'wet'].includes(p.tire))).map(p => {
                        const driver = playerDrivers.find(d => d.name === p.driver_name);
                        const gripLevel = getGripLevel(p.tire_wear);
                        return `
                            <div class="pit-driver-card needs-pit" data-driver-id="${driver?.id}">
                                <div class="pit-driver-info">
                                    <strong>${escapeHtml(p.driver_name)}</strong>
                                    <span class="pit-status">P${p.position} | ${p.tire.toUpperCase()} | Wear: ${p.tire_wear}% (${gripLevel})</span>
                                </div>
                                <div class="pit-buttons">
                                    ${raceState?.weather === 'dry' ? `
                                        <button class="btn btn-sm pit-btn tire-soft" data-driver="${driver?.id}" data-compound="soft">Soft</button>
                                        <button class="btn btn-sm pit-btn tire-medium" data-driver="${driver?.id}" data-compound="medium">Medium</button>
                                        <button class="btn btn-sm pit-btn tire-hard" data-driver="${driver?.id}" data-compound="hard">Hard</button>
                                    ` : `
                                        <button class="btn btn-sm pit-btn tire-intermediate" data-driver="${driver?.id}" data-compound="intermediate">Inters</button>
                                        <button class="btn btn-sm pit-btn tire-wet" data-driver="${driver?.id}" data-compound="wet">Wets</button>
                                    `}
                                    <button class="btn btn-sm btn-secondary skip-pit-btn" data-driver="${driver?.id}">Stay Out</button>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
                <button class="btn btn-primary btn-block mt-lg" id="continue-race-btn">
                    Continue Race
                </button>
            </div>
        `;
    } else if (!pausedForPits && !singlePlayerNeedsPit) {
        // Race is running (no pit decisions needed)
        pitUI = `
            <div class="race-simulating card mb-lg">
                <div class="simulating-status">
                    <div class="spinner-small"></div>
                    <span>Race in progress - Lap ${raceState?.current_lap || 0}/${raceState?.total_laps || 0}</span>
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="game-container race-screen">
            <div class="game-header">
                <div class="race-header-info">
                    <div>
                        <h1>${escapeHtml(state.current_track?.name || 'Race')}</h1>
                        <span class="weather-indicator ${raceState?.weather !== 'dry' ? 'rain-warning' : ''}">${weatherIcon} ${weatherText}</span>
                        ${raceState?.safety_car ? '<span class="safety-car-badge">SAFETY CAR</span>' : ''}
                    </div>
                    <div class="lap-counter">
                        <span class="lap-current">Lap ${raceState?.current_lap || 0}</span>
                        <span class="lap-total">/ ${raceState?.total_laps || 0}</span>
                    </div>
                </div>
            </div>

            <div class="game-content">
                ${pitUI}

                <div class="race-positions card">
                    <table class="race-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Gap</th>
                                <th>Tire</th>
                                <th>Wear</th>
                                <th>Pits</th>
                            </tr>
                        </thead>
                        <tbody id="race-positions">
                            ${renderRacePositions(raceState?.positions || [], state.your_player_id)}
                        </tbody>
                    </table>
                </div>

                <div class="race-events card mt-lg">
                    <h3>Recent Events</h3>
                    <div id="race-events" class="events-list">
                        ${raceState?.events?.slice(-8).map(e => `
                            <div class="event-item event-${e.event_type}">
                                <span class="event-lap">Lap ${e.lap}</span>
                                <span class="event-text">${escapeHtml(e.description)}</span>
                            </div>
                        `).reverse().join('') || '<p class="text-muted">No events yet</p>'}
                    </div>
                </div>
            </div>
        </div>
    `;

    // Pit stop button handlers
    container.querySelectorAll('.pit-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const driverId = btn.dataset.driver;
            const compound = btn.dataset.compound;
            setButtonLoading(btn, true);
            try {
                await api.post(`/gameplay/${state.game_id}/pit-stop`, {
                    driver_id: driverId,
                    compound: compound
                });
                // Mark this driver's card as pitted
                const card = btn.closest('.pit-driver-card');
                if (card) {
                    card.classList.add('pitted');
                    card.innerHTML = `<div class="pitted-message">Pitting for ${compound.toUpperCase()} tires</div>`;
                }
            } catch (error) {
                showAlert(container.querySelector('.game-content'), error.message, 'error');
                setButtonLoading(btn, false);
            }
        });
    });

    // Skip pit handlers
    container.querySelectorAll('.skip-pit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const card = btn.closest('.pit-driver-card');
            if (card) {
                card.classList.add('pitted');
                card.innerHTML = `<div class="pitted-message">Staying out</div>`;
            }
        });
    });

    // Confirm decisions button (multiplayer sync)
    document.getElementById('confirm-decisions-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('confirm-decisions-btn');
        setButtonLoading(btn, true);
        try {
            // Confirm our pit decisions
            await api.post(`/gameplay/${state.game_id}/confirm-pit-decisions`);
            // Refresh state
            const newState = await api.get(`/gameplay/${state.game_id}/state`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    // Single player continue race button
    document.getElementById('continue-race-btn')?.addEventListener('click', () => {
        autoSimulateRace(container, state.game_id);
    });

    // Auto-simulate race when not paused for pits (or when all players have confirmed)
    const allConfirmed = pitStatus?.all_confirmed || false;
    const shouldAutoSimulate = !raceState?.is_finished &&
        (isMultiplayer ? (!pausedForPits || allConfirmed) : !singlePlayerNeedsPit);
    if (shouldAutoSimulate) {
        autoSimulateRace(container, state.game_id);
    }

    // Start refresh interval when waiting for opponent's pit decisions (multiplayer)
    if (isMultiplayer && pausedForPits && !iNeedToDecide && waitingForPlayers.length > 0) {
        startRefreshInterval(state.game_id, container);
    }
}

/**
 * Check if any player driver needs a pit decision
 */
function checkNeedsPitDecision(playerPositions, raceState) {
    if (!playerPositions || playerPositions.length === 0) return false;

    for (const p of playerPositions) {
        // High tire wear
        if (p.tire_wear >= 70) return true;

        // Wrong tires for weather
        const isWet = raceState?.weather !== 'dry';
        const hasWetTires = ['intermediate', 'wet'].includes(p.tire);
        if (isWet && !hasWetTires) return true;
        if (!isWet && hasWetTires && p.pit_stops > 0) return true; // Only flag if they've pitted before
    }

    return false;
}

function getGripLevel(wear) {
    if (wear <= 20) return 'OPTIMAL';
    if (wear <= 40) return 'GOOD';
    if (wear <= 60) return 'WORN';
    if (wear <= 80) return 'CRITICAL';
    return 'DEAD';
}

/**
 * Auto-simulate race until pit decision needed or race ends
 * Server controls pit decision pauses for multiplayer sync
 * Client controls pit decisions for single player
 */
async function autoSimulateRace(container, gameId) {
    if (raceAutoSimulating) return;
    raceAutoSimulating = true;

    try {
        let state = await api.post(`/gameplay/${gameId}/simulate-lap`);

        // Keep simulating until we need to pause
        while (state.phase === GamePhase.RACE_IN_PROGRESS) {
            const raceState = state.race_state;
            const pitStatus = raceState?.pit_decision_status;
            const isMultiplayer = state.is_multiplayer;

            // Check if race finished
            if (raceState?.is_finished || raceState?.current_lap >= raceState?.total_laps) {
                break;
            }

            // MULTIPLAYER: Server tells us when to pause
            if (isMultiplayer && pitStatus?.paused_for_pits) {
                break;
            }

            // SINGLE PLAYER: Client-side pit check
            if (!isMultiplayer) {
                const playerPositions = raceState?.positions?.filter(p =>
                    p.player_id === state.your_player_id && p.status !== 'dnf'
                ) || [];
                if (checkNeedsPitDecision(playerPositions, raceState)) {
                    break;
                }
            }

            // Small delay for visual effect
            await new Promise(resolve => setTimeout(resolve, 100));

            // Simulate next lap
            state = await api.post(`/gameplay/${gameId}/simulate-lap`);
        }

        raceAutoSimulating = false;
        renderGameScreen(container, state);
    } catch (error) {
        raceAutoSimulating = false;
        showAlert(container.querySelector('.game-content'), error.message, 'error');
    }
}

async function simulateFullRace(container, gameId) {
    const btn = document.getElementById('sim-race-btn');
    setButtonLoading(btn, true);

    try {
        const newState = await api.post(`/gameplay/${gameId}/simulate-race`);
        renderGameScreen(container, newState);
    } catch (error) {
        showAlert(container.querySelector('.game-content'), error.message, 'error');
        setButtonLoading(btn, false);
    }
}

function renderRacePositions(positions, yourPlayerId) {
    return positions.map(p => `
        <tr class="${p.player_id === yourPlayerId ? 'player-row your-driver' : ''} ${p.status === 'dnf' ? 'dnf-row' : ''}">
            <td class="pos-cell">${p.status === 'dnf' ? 'DNF' : p.position}</td>
            <td>${escapeHtml(p.driver_name)}</td>
            <td class="team-cell">${escapeHtml(p.team_name || '')}</td>
            <td>${p.gap}</td>
            <td><span class="tire-badge tire-${p.tire}">${p.tire.charAt(0).toUpperCase()}</span></td>
            <td>
                <div class="wear-bar">
                    <div class="wear-fill" style="width: ${p.tire_wear}%; background: ${getWearColor(p.tire_wear)}"></div>
                </div>
            </td>
            <td>${p.pit_stops}</td>
        </tr>
    `).join('');
}

function getWearColor(wear) {
    if (wear < 40) return 'var(--success)';
    if (wear < 70) return 'var(--warning)';
    return 'var(--error)';
}

/**
 * Race Results Screen - With sync for multiplayer
 */
function renderRaceResults(container, state) {
    const isMultiplayer = state.is_multiplayer;
    const myPlayer = state.players?.find(p => p.player_id === state.your_player_id);
    const otherPlayer = state.players?.find(p => p.player_id !== state.your_player_id);
    const imReady = myPlayer?.is_ready;
    const opponentReady = otherPlayer?.is_ready;
    const bothReady = isMultiplayer ? (imReady && opponentReady) : true;

    // Calculate points earned this race for each player
    const myDrivers = state.race_state?.positions?.filter(p => p.player_id === state.your_player_id) || [];
    const myPoints = myDrivers.reduce((sum, p) => sum + (p.status !== 'dnf' ? getPointsForPosition(p.position) : 0), 0);

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Race Results</h1>
                <p class="text-secondary">${escapeHtml(state.current_track?.name || 'Unknown Track')}</p>
            </div>

            <div class="game-content">
                <div class="race-summary card mb-lg">
                    <h3>Your Results</h3>
                    <div class="your-results">
                        ${myDrivers.map(p => `
                            <div class="result-driver ${p.status === 'dnf' ? 'dnf' : p.position <= 3 ? 'podium' : ''}">
                                <span class="result-pos">${p.status === 'dnf' ? 'DNF' : `P${p.position}`}</span>
                                <span class="result-name">${escapeHtml(p.driver_name)}</span>
                                <span class="result-points">+${p.status === 'dnf' ? '0' : getPointsForPosition(p.position)} pts</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="total-points">Total: +${myPoints} points</div>
                </div>

                <div class="card">
                    <h3>Full Classification</h3>
                    <table class="results-table">
                        <thead>
                            <tr>
                                <th>Pos</th>
                                <th>Driver</th>
                                <th>Team</th>
                                <th>Gap</th>
                                <th>Points</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${state.race_state?.positions?.map(p => `
                                <tr class="${p.player_id === state.your_player_id ? 'player-row your-driver' : ''} ${p.status === 'dnf' ? 'dnf-row' : ''}">
                                    <td class="pos-cell">${p.status === 'dnf' ? 'DNF' : p.position}</td>
                                    <td>${escapeHtml(p.driver_name)}</td>
                                    <td>${escapeHtml(p.team_name)}</td>
                                    <td class="gap-cell">${p.position === 1 ? 'Leader' : p.status === 'dnf' ? '-' : p.gap}</td>
                                    <td>${p.status === 'dnf' ? '0' : getPointsForPosition(p.position)}</td>
                                </tr>
                            `).join('') || '<tr><td colspan="5">No results</td></tr>'}
                        </tbody>
                    </table>
                </div>

                ${state.news_headlines && state.news_headlines.length > 0 ? `
                    <div class="card news-headlines-card mt-lg">
                        <h3>Race Headlines</h3>
                        <div class="news-headlines">
                            ${state.news_headlines.slice(0, 5).map(nh => `
                                <div class="news-item ${nh.is_about_player ? 'about-player' : ''} category-${nh.category}">
                                    <div class="news-category">${formatNewsCategory(nh.category)}</div>
                                    <div class="news-headline">${escapeHtml(nh.headline)}</div>
                                    <div class="news-body">${escapeHtml(nh.body)}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                ${isMultiplayer ? `
                    <div class="sync-status mt-xl">
                        <div class="sync-player ${imReady ? 'is-ready' : ''}">
                            <span class="sync-name">You</span>
                            <span class="sync-indicator">${imReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                        <div class="sync-player ${opponentReady ? 'is-ready' : ''}">
                            <span class="sync-name">${escapeHtml(otherPlayer?.username || 'Opponent')}</span>
                            <span class="sync-indicator">${opponentReady ? 'Ready' : 'Reviewing'}</span>
                        </div>
                    </div>
                    ${!imReady ? `
                        <button class="btn btn-success btn-lg btn-block mt-lg" id="ready-btn">
                            Ready to Continue
                        </button>
                    ` : bothReady ? `
                        <button class="btn btn-primary btn-lg btn-block mt-lg" id="continue-btn">
                            Continue to Next Race
                        </button>
                    ` : `
                        <div class="waiting-sync mt-lg">
                            <div class="spinner-small"></div>
                            <span>Waiting for ${escapeHtml(otherPlayer?.username || 'opponent')}...</span>
                        </div>
                    `}
                ` : `
                    <button class="btn btn-primary btn-lg btn-block mt-xl" id="continue-btn">
                        Continue
                    </button>
                `}
            </div>
        </div>
    `;

    document.getElementById('ready-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('ready-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/ready`, { ready: true });
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    document.getElementById('continue-btn')?.addEventListener('click', async () => {
        const btn = document.getElementById('continue-btn');
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/next-race`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });

    // Auto-refresh when ready (to detect when other player advances phase)
    if (isMultiplayer && imReady) {
        startRefreshInterval(state.game_id, container);
    }
}

/**
 * Team Screen with Morale
 */
function renderTeamScreen(container, state) {
    const team = state.player_team;
    const car = team?.car;
    const sponsor = team?.sponsor;

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>My Team</h1>
            </div>

            <div class="game-content">
                <div class="team-info-grid">
                    <div class="card">
                        <h3>Team Info</h3>
                        <p><strong>${escapeHtml(team?.name || 'Unknown')}</strong></p>
                        <p>Budget: $${team?.budget?.toFixed(1) || 0}M</p>
                        <p>Season Points: ${team?.season_points || 0}</p>
                        <p>Race Wins: ${team?.race_wins || 0}</p>
                    </div>

                    ${sponsor ? `
                        <div class="card">
                            <h3>Sponsor: ${escapeHtml(sponsor.name)}</h3>
                            <p class="sponsor-tier tier-${sponsor.tier}">${sponsor.tier.toUpperCase()}</p>
                            <p>Per Race: $${sponsor.payment_per_race?.toFixed(1) || 0}M</p>
                            <p>Objectives Met: ${sponsor.objectives_met || 0}/${sponsor.races_completed || 0}</p>
                        </div>
                    ` : ''}

                    <div class="card">
                        <h3>Car Stats</h3>
                        <div class="car-stats">
                            ${renderCarStat('Downforce', car?.downforce)}
                            ${renderCarStat('Aero Efficiency', car?.aero_efficiency)}
                            ${renderCarStat('Chassis', car?.chassis)}
                            ${renderCarStat('Power Unit', car?.power_unit)}
                            ${renderCarStat('Reliability', car?.reliability)}
                            ${renderCarStat('Tire Cooling', car?.tire_cooling)}
                        </div>
                        <p class="mt-md"><strong>Overall: ${calculateCarOverall(car)}</strong></p>
                    </div>
                </div>

                <h3 class="mt-xl">Drivers</h3>
                <div class="drivers-grid mt-md">
                    ${team?.drivers?.map(driver => `
                        <div class="card driver-detail-card">
                            <div class="driver-header-row">
                                <h4>${escapeHtml(driver.name)}</h4>
                                ${driver.form?.level && driver.form.level !== 'normal' ? `
                                    <span class="driver-form-badge form-${driver.form.level}">${formatFormLevel(driver.form.level)}</span>
                                ` : ''}
                            </div>
                            <p class="text-secondary">${driver.age} years old - ${escapeHtml(driver.nationality)}</p>

                            ${driver.traits?.length > 0 ? `
                                <div class="driver-traits">
                                    ${driver.traits.map(trait => `<span class="trait-badge trait-${trait}">${formatTraitName(trait)}</span>`).join('')}
                                </div>
                            ` : ''}

                            ${driver.injury?.injury_type && driver.injury.injury_type !== 'none' ? `
                                <div class="injury-detail mt-sm">
                                    <span class="injury-badge injury-${driver.injury.injury_type}">${driver.injury.description}</span>
                                    <p class="races-remaining">Out for ${driver.injury.races_remaining} more race(s)</p>
                                </div>
                            ` : ''}

                            <div class="driver-morale mt-md">
                                <span>Morale: </span>
                                <div class="morale-bar">
                                    <div class="morale-fill" style="width: ${driver.morale || 75}%; background: ${getMoraleColor(driver.morale)}"></div>
                                </div>
                                <span>${driver.morale || 75}%</span>
                            </div>

                            <div class="driver-stats-detail mt-md">
                                ${renderDriverStat('Pace', driver.stats.pace)}
                                ${renderDriverStat('Overtaking', driver.stats.overtaking)}
                                ${renderDriverStat('Defending', driver.stats.defending)}
                                ${renderDriverStat('Consistency', driver.stats.consistency)}
                                ${renderDriverStat('Tire Mgmt', driver.stats.tire_management)}
                                ${renderDriverStat('Wet Skill', driver.stats.wet_skill)}
                            </div>

                            <div class="driver-season-stats mt-md">
                                <span class="mini-stat">Points: ${driver.season_points || 0}</span>
                                <span class="mini-stat">Wins: ${driver.race_wins || 0}</span>
                                <span class="mini-stat">Podiums: ${driver.podiums || 0}</span>
                            </div>

                            ${driver.relationships?.length > 0 ? `
                                <div class="driver-relationships">
                                    <h5>Relationships</h5>
                                    <div class="relationship-list">
                                        ${driver.relationships.slice(0, 3).map(rel => `
                                            <div class="relationship-item">
                                                <span class="relationship-type type-${rel.relationship_type}">${formatRelationshipType(rel.relationship_type)}</span>
                                                <span class="relationship-name">${escapeHtml(rel.other_driver_name)}</span>
                                                ${rel.reason ? `<span class="relationship-reason">${escapeHtml(rel.reason)}</span>` : ''}
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}

                            ${driver.contract ? `
                                <div class="driver-contract mt-md">
                                    <small>Contract: ${driver.contract.years_remaining} year(s) @ $${driver.contract.salary?.toFixed(1) || driver.salary?.toFixed(1)}M</small>
                                </div>
                            ` : ''}
                        </div>
                    `).join('') || '<p>No drivers</p>'}
                </div>
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => {
        renderMainMenu(container, state);
    });
}

function getMoraleColor(morale) {
    if (morale >= 80) return 'var(--success)';
    if (morale >= 50) return 'var(--warning)';
    return 'var(--error)';
}

/**
 * Standings Screen
 */
function renderStandingsScreen(container, state) {
    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Championship Standings</h1>
            </div>

            <div class="game-content">
                <div class="standings-tabs">
                    <button class="tab-btn active" data-tab="drivers">Drivers</button>
                    <button class="tab-btn" data-tab="constructors">Constructors</button>
                </div>

                <div class="tab-content" id="drivers-tab">
                    <div class="card">
                        <table class="standings-table">
                            <thead>
                                <tr>
                                    <th>Pos</th>
                                    <th>Driver</th>
                                    <th>Team</th>
                                    <th>Wins</th>
                                    <th>Points</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${state.driver_standings?.map(s => `
                                    <tr class="${s.player_id === state.your_player_id ? 'player-row your-driver' : ''}">
                                        <td class="pos-cell">${s.position}</td>
                                        <td>${escapeHtml(s.driver_name)}</td>
                                        <td>${escapeHtml(s.team_name)}</td>
                                        <td>${s.wins}</td>
                                        <td><strong>${s.points}</strong></td>
                                    </tr>
                                `).join('') || '<tr><td colspan="5">No standings</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="tab-content" id="constructors-tab" style="display: none;">
                    <div class="card">
                        <table class="standings-table">
                            <thead>
                                <tr>
                                    <th>Pos</th>
                                    <th>Team</th>
                                    <th>Wins</th>
                                    <th>Points</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${state.constructor_standings?.map(s => `
                                    <tr class="${s.player_id === state.your_player_id ? 'player-row your-driver' : ''}">
                                        <td class="pos-cell">${s.position}</td>
                                        <td>${escapeHtml(s.team_name)}</td>
                                        <td>${s.wins}</td>
                                        <td><strong>${s.points}</strong></td>
                                    </tr>
                                `).join('') || '<tr><td colspan="4">No standings</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Tab switching
    container.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const tab = btn.dataset.tab;
            document.getElementById('drivers-tab').style.display = tab === 'drivers' ? 'block' : 'none';
            document.getElementById('constructors-tab').style.display = tab === 'constructors' ? 'block' : 'none';
        });
    });

    document.getElementById('back-btn')?.addEventListener('click', () => {
        renderMainMenu(container, state);
    });
}

/**
 * Calendar Screen
 */
function renderCalendarScreen(container, state) {
    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Season Calendar</h1>
            </div>

            <div class="game-content">
                <div class="calendar-grid">
                    ${state.calendar?.map(race => `
                        <div class="card calendar-card ${race.is_current ? 'current-race' : ''} ${race.is_completed ? 'completed-race' : ''}">
                            <div class="race-number">R${race.race_number}</div>
                            <h4>${escapeHtml(race.track.name)}</h4>
                            <p class="text-secondary">${escapeHtml(race.track.country)}</p>
                            ${race.is_completed ? '<span class="race-status completed">Completed</span>' : ''}
                            ${race.is_current ? '<span class="race-status current">Next Race</span>' : ''}
                        </div>
                    `).join('') || '<p>No calendar data</p>'}
                </div>
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => {
        renderMainMenu(container, state);
    });
}

/**
 * Season End Screen
 */
function renderSeasonEnd(container, state) {
    const driverChamp = state.driver_standings?.[0];
    const constructorChamp = state.constructor_standings?.[0];
    const playerPosition = state.constructor_standings?.find(s => s.player_id === state.your_player_id)?.position || 'N/A';

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Season ${state.current_season} Complete!</h1>
            </div>

            <div class="game-content text-center">
                <div class="card champion-card mb-xl">
                    <h2>Champions</h2>
                    <div class="champions-grid mt-lg">
                        <div>
                            <h4>Drivers' Champion</h4>
                            <p class="champion-name">${escapeHtml(driverChamp?.driver_name || 'Unknown')}</p>
                            <p class="text-secondary">${driverChamp?.points || 0} points</p>
                        </div>
                        <div>
                            <h4>Constructors' Champion</h4>
                            <p class="champion-name">${escapeHtml(constructorChamp?.team_name || 'Unknown')}</p>
                            <p class="text-secondary">${constructorChamp?.points || 0} points</p>
                        </div>
                    </div>
                </div>

                <div class="card mb-xl">
                    <h3>Your Team Finished</h3>
                    <p class="season-position">${playerPosition}${getOrdinalSuffix(playerPosition)}</p>
                    <p class="text-secondary">${state.player_team?.season_points || 0} points</p>
                </div>

                <a href="#/games" class="btn btn-primary btn-lg">Return to Lobby</a>
            </div>
        </div>
    `;
}

/**
 * Transfer Window Screen - End of season driver market
 */
function renderTransferWindow(container, state) {
    const team = state.player_team;
    const drivers = team?.drivers || [];

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <h1>Transfer Window</h1>
                <p class="text-secondary">Season ${state.current_season} has ended. Manage your driver lineup for next season.</p>
            </div>

            <div class="game-content">
                <!-- Team Status -->
                <div class="card mb-lg">
                    <div class="flex" style="justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-md);">
                        <div>
                            <h3>${escapeHtml(team?.name || 'Your Team')}</h3>
                            <p class="text-secondary">Budget: <strong>$${team?.budget?.toFixed(1) || 0}M</strong></p>
                        </div>
                        <div class="team-stats">
                            <span class="stat-pill">Car: ${calculateCarOverall(team?.car)}</span>
                            <span class="stat-pill">Points: ${team?.season_points || 0}</span>
                        </div>
                    </div>
                </div>

                <!-- Current Drivers -->
                <div class="card mb-lg">
                    <h3>Current Drivers</h3>
                    <p class="text-secondary mb-md">You can release drivers to make room for new signings. You must keep at least 1 driver.</p>
                    <div class="drivers-grid mt-md">
                        ${drivers.map(driver => `
                            <div class="driver-card">
                                <div class="driver-card-header">
                                    <div>
                                        <h4>${escapeHtml(driver.name)}</h4>
                                        <span class="driver-meta">${driver.age} yrs | ${escapeHtml(driver.nationality)}</span>
                                    </div>
                                    <span class="driver-overall">${calculateOverall(driver.stats)}</span>
                                </div>
                                <div class="driver-stats-mini">
                                    <span class="stat-mini">PAC ${driver.stats.pace}</span>
                                    <span class="stat-mini">OVT ${driver.stats.overtaking}</span>
                                    <span class="stat-mini">DEF ${driver.stats.defending}</span>
                                </div>
                                <div class="driver-contract mt-sm">
                                    <span class="text-secondary">Salary: $${driver.salary?.toFixed(1) || 0}M/yr</span>
                                    ${driver.contract ? `<span class="text-secondary"> | ${driver.contract.years_remaining} yr${driver.contract.years_remaining !== 1 ? 's' : ''} left</span>` : ''}
                                </div>
                                ${drivers.length > 1 ? `
                                    <button class="btn btn-danger btn-sm mt-md release-driver-btn" data-driver-id="${driver.id}" data-driver-name="${escapeHtml(driver.name)}">
                                        Release Driver
                                    </button>
                                ` : '<p class="text-secondary mt-md text-xs">Cannot release last driver</p>'}
                            </div>
                        `).join('') || '<p class="text-secondary">No drivers signed</p>'}
                    </div>
                </div>

                <!-- Available Drivers -->
                ${drivers.length < 2 ? `
                    <div class="card mb-lg">
                        <h3>Available Drivers</h3>
                        <p class="text-secondary mb-md">Your improved car and reputation may attract better drivers than before!</p>
                        <div style="overflow-x: auto;">
                            <table class="driver-table">
                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Age</th>
                                        <th>Nat</th>
                                        <th>OVR</th>
                                        <th>POT</th>
                                        <th>Interest</th>
                                        <th>PAC</th>
                                        <th>OVT</th>
                                        <th>DEF</th>
                                        <th>CON</th>
                                        <th>TIR</th>
                                        <th>WET</th>
                                        <th>Value</th>
                                        <th>Salary</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${state.market_drivers?.map(driver => {
                                        const cantAfford = driver.market_value > (team?.budget || 0);
                                        const notInterested = driver.interested === false;
                                        const cannotSign = cantAfford || notInterested;

                                        return `<tr class="${cantAfford ? 'unaffordable' : ''} ${notInterested ? 'not-interested' : ''}">
                                            <td><strong>${escapeHtml(driver.name)}</strong></td>
                                            <td>${driver.age}</td>
                                            <td>${escapeHtml(driver.nationality.substring(0, 3).toUpperCase())}</td>
                                            <td><span class="stat-badge">${calculateOverall(driver.stats)}</span></td>
                                            <td><span class="stat-badge potential">${driver.potential}</span></td>
                                            <td>
                                                ${driver.interested !== false ?
                                                    `<span class="interest-badge interested" title="Willing to join your team">Interested</span>` :
                                                    `<span class="interest-badge not-interested" title="${escapeHtml(driver.interest_reason || 'Not interested')}">${escapeHtml(driver.interest_reason || 'Not interested')}</span>`
                                                }
                                            </td>
                                            <td>${driver.stats.pace}</td>
                                            <td>${driver.stats.overtaking}</td>
                                            <td>${driver.stats.defending}</td>
                                            <td>${driver.stats.consistency}</td>
                                            <td>${driver.stats.tire_management}</td>
                                            <td>${driver.stats.wet_skill}</td>
                                            <td class="price-tag">$${driver.market_value?.toFixed(1)}M</td>
                                            <td>$${driver.salary?.toFixed(1)}M</td>
                                            <td>
                                                <button class="btn ${cannotSign ? 'btn-secondary' : 'btn-primary'} btn-sm transfer-sign-btn"
                                                        data-driver-id="${driver.id}"
                                                        data-driver-name="${escapeHtml(driver.name)}"
                                                        data-salary="${driver.salary}"
                                                        data-value="${driver.market_value}"
                                                        ${cannotSign ? 'disabled' : ''}
                                                        title="${notInterested ? 'Driver not interested' : cantAfford ? 'Cannot afford' : 'Sign driver'}">
                                                    ${notInterested ? 'No' : cantAfford ? 'Too $$$' : 'Sign'}
                                                </button>
                                            </td>
                                        </tr>`;
                                    }).join('') || '<tr><td colspan="15">No drivers available</td></tr>'}
                                </tbody>
                            </table>
                        </div>
                    </div>
                ` : `
                    <div class="alert alert-info mb-lg">
                        Your team is full (2 drivers). Release a driver to sign someone new.
                    </div>
                `}

                <!-- Continue Button -->
                <div class="text-center">
                    <button class="btn btn-primary btn-lg skip-transfer-btn">
                        ${drivers.length >= 2 ? 'Start Next Season' : 'Continue with Current Lineup'}
                    </button>
                </div>
            </div>
        </div>
    `;

    // Event listeners for releasing drivers
    container.querySelectorAll('.release-driver-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const driverId = btn.dataset.driverId;
            const driverName = btn.dataset.driverName;

            const confirmed = await modalConfirm(`Release ${driverName}? This cannot be undone.`, 'Release Driver');
            if (confirmed) {
                setButtonLoading(btn, true);
                try {
                    const newState = await api.post(`/gameplay/${state.game_id}/transfer-release-driver`, {
                        driver_id: driverId
                    });
                    renderGameScreen(container, newState);
                } catch (error) {
                    showAlert(container.querySelector('.game-content'), error.message, 'error');
                    setButtonLoading(btn, false);
                }
            }
        });
    });

    // Event listeners for signing drivers
    container.querySelectorAll('.transfer-sign-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
            const driverId = btn.dataset.driverId;
            const driverName = btn.dataset.driverName;
            const salary = parseFloat(btn.dataset.salary);

            const confirmed = await modalConfirm(`Sign ${driverName} for $${salary.toFixed(1)}M/year?`, 'Sign Driver');
            if (confirmed) {
                setButtonLoading(btn, true);
                try {
                    const newState = await api.post(`/gameplay/${state.game_id}/transfer-sign-driver`, {
                        driver_id: driverId,
                        salary: salary,
                        years: 2,
                        is_number_one: false
                    });
                    renderGameScreen(container, newState);
                } catch (error) {
                    showAlert(container.querySelector('.game-content'), error.message, 'error');
                    setButtonLoading(btn, false);
                }
            }
        });
    });

    // Skip transfer window
    container.querySelector('.skip-transfer-btn').addEventListener('click', async () => {
        const btn = container.querySelector('.skip-transfer-btn');
        if (drivers.length < 2) {
            const confirmed = await modalConfirm('You only have 1 driver. Are you sure you want to continue without signing another?', 'Continue with 1 Driver');
            if (!confirmed) {
                return;
            }
        }
        setButtonLoading(btn, true);
        try {
            const newState = await api.post(`/gameplay/${state.game_id}/skip-transfer-window`);
            renderGameScreen(container, newState);
        } catch (error) {
            showAlert(container.querySelector('.game-content'), error.message, 'error');
            setButtonLoading(btn, false);
        }
    });
}

// Helper functions
function calculateOverall(stats) {
    return Math.round(
        stats.pace * 0.25 +
        stats.overtaking * 0.15 +
        stats.defending * 0.15 +
        stats.consistency * 0.20 +
        stats.tire_management * 0.15 +
        stats.wet_skill * 0.10
    );
}

function calculateCarOverall(car) {
    if (!car) return 0;
    return Math.round(
        (car.downforce || 0) * 0.18 +
        (car.aero_efficiency || 0) * 0.18 +
        (car.chassis || 0) * 0.22 +
        (car.power_unit || 0) * 0.18 +
        (car.reliability || 0) * 0.12 +
        (car.tire_cooling || 0) * 0.12
    );
}

function getDriverQualifyingPosition(state, driverName) {
    const result = state.qualifying_results?.find(r => r.driver_name === driverName);
    return result?.position || '?';
}

function getPointsForPosition(position) {
    const points = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1];
    return position <= 10 ? points[position - 1] : 0;
}

function getOrdinalSuffix(n) {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return s[(v - 20) % 10] || s[v] || s[0];
}

function formatNewsCategory(category) {
    const categories = {
        'race_result': 'RACE',
        'driver_performance': 'DRIVER',
        'team_news': 'TEAM',
        'contract': 'CONTRACT',
        'injury': 'INJURY',
        'rivalry': 'RIVALRY',
        'achievement': 'ACHIEVEMENT',
        'controversy': 'DRAMA'
    };
    return categories[category] || category.toUpperCase();
}

function formatFormLevel(level) {
    const levels = {
        'hot_streak': 'On Fire',
        'good_form': 'Good Form',
        'normal': 'Normal',
        'poor_form': 'Poor Form',
        'slump': 'Struggling'
    };
    return levels[level] || level;
}

function getFormClass(level) {
    const classes = {
        'hot_streak': 'form-hot',
        'good_form': 'form-good',
        'normal': 'form-normal',
        'poor_form': 'form-poor',
        'slump': 'form-slump'
    };
    return classes[level] || '';
}

function formatTraitName(trait) {
    const traits = {
        'aggressive': 'Aggressive',
        'consistent': 'Consistent',
        'wet_weather_specialist': 'Wet Specialist',
        'tire_whisperer': 'Tire Whisperer',
        'qualifying_king': 'Quali King'
    };
    return traits[trait] || trait;
}

function formatRelationshipType(type) {
    const types = {
        'rivalry': 'Rival',
        'friendship': 'Friend',
        'neutral': 'Neutral',
        'respect': 'Respect',
        'animosity': 'Bad Blood'
    };
    return types[type] || type;
}

function renderCarStat(name, value) {
    return `
        <div class="car-stat">
            <span class="stat-name">${name}</span>
            <div class="stat-bar-container">
                <div class="stat-bar" style="width: ${value || 0}%"></div>
            </div>
            <span class="stat-value">${value || 0}</span>
        </div>
    `;
}

function renderDriverStat(name, value) {
    return `
        <div class="driver-stat">
            <span class="stat-name">${name}</span>
            <div class="stat-bar-container">
                <div class="stat-bar" style="width: ${value || 0}%; background: ${getStatColor(value)}"></div>
            </div>
            <span class="stat-value">${value || 0}</span>
        </div>
    `;
}

function getStatColor(value) {
    if (value >= 85) return 'var(--success)';
    if (value >= 70) return 'var(--accent-primary)';
    if (value >= 55) return 'var(--warning)';
    return 'var(--error)';
}

function formatTrackType(trackType) {
    if (!trackType) return 'Unknown';
    // Convert snake_case to Title Case (e.g., "high_speed" -> "High Speed")
    return trackType
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

function getTireWearLevel(degradation) {
    // degradation is a multiplier (1.0 = normal, >1.0 = higher wear, <1.0 = lower wear)
    if (degradation >= 1.2) return 'High';
    if (degradation >= 0.9) return 'Medium';
    return 'Low';
}

/**
 * Other Teams Screen - View rival teams' car ratings, drivers, and upgrade history
 */
function renderOtherTeamsScreen(container, state) {
    const rivalTeams = state.rival_teams || [];

    container.innerHTML = `
        <div class="game-container">
            <div class="game-header">
                <button class="btn btn-secondary" id="back-btn">Back</button>
                <h1>Other Teams</h1>
            </div>

            <div class="game-content">
                <p class="text-secondary mb-lg">View rival teams' car development and performance throughout the season.</p>

                <div class="rival-teams-grid">
                    ${rivalTeams.length > 0 ? rivalTeams.map(team => `
                        <div class="card rival-team-card">
                            <div class="rival-team-header">
                                <div>
                                    <h3 class="rival-team-name">${escapeHtml(team.name)}</h3>
                                    <span class="constructor-position">P${team.constructor_position}</span>
                                </div>
                                <div class="rival-overall-badge">${team.car_overall}</div>
                            </div>

                            <div class="rival-team-stats">
                                <span class="rival-stat">
                                    <span class="stat-icon">🏆</span>
                                    <span class="stat-text">${team.race_wins} wins</span>
                                </span>
                                <span class="rival-stat">
                                    <span class="stat-icon">📊</span>
                                    <span class="stat-text">${team.season_points} pts</span>
                                </span>
                            </div>

                            <div class="rival-drivers">
                                <h4>Drivers</h4>
                                <div class="driver-list">
                                    ${team.drivers?.map(d => `<span class="driver-name-tag">${escapeHtml(d)}</span>`).join('') || '<span class="text-muted">No drivers</span>'}
                                </div>
                            </div>

                            <div class="rival-car-stats">
                                <h4>Car Stats</h4>
                                ${renderRivalCarStat('Downforce', team.car_stats?.downforce)}
                                ${renderRivalCarStat('Aero Eff.', team.car_stats?.aero_efficiency)}
                                ${renderRivalCarStat('Chassis', team.car_stats?.chassis)}
                                ${renderRivalCarStat('Power Unit', team.car_stats?.power_unit)}
                                ${renderRivalCarStat('Reliability', team.car_stats?.reliability)}
                                ${renderRivalCarStat('Tire Cool.', team.car_stats?.tire_cooling)}
                            </div>

                            ${team.recent_upgrades?.length > 0 ? `
                                <div class="rival-upgrades">
                                    <h4>Recent Upgrades</h4>
                                    <div class="upgrade-list">
                                        ${team.recent_upgrades.slice(0, 3).map(upgrade => `
                                            <div class="upgrade-item">
                                                <span class="upgrade-race">R${upgrade.race_number}</span>
                                                <span class="upgrade-stat">${formatStatName(upgrade.stat_name)}</span>
                                                <span class="upgrade-change">+${upgrade.new_value - upgrade.old_value}</span>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : `
                                <div class="rival-upgrades">
                                    <h4>Recent Upgrades</h4>
                                    <p class="text-muted no-upgrades">No upgrades yet</p>
                                </div>
                            `}
                        </div>
                    `).join('') : '<p class="text-muted">No rival teams data available.</p>'}
                </div>
            </div>
        </div>
    `;

    document.getElementById('back-btn')?.addEventListener('click', () => {
        renderMainMenu(container, state);
    });
}

function renderRivalCarStat(name, value) {
    return `
        <div class="rival-car-stat">
            <span class="rival-stat-name">${name}</span>
            <div class="rival-stat-bar">
                <div class="rival-stat-fill" style="width: ${value || 0}%"></div>
            </div>
            <span class="rival-stat-value">${value || 0}</span>
        </div>
    `;
}

function formatStatName(statName) {
    const names = {
        'downforce': 'Downforce',
        'aero_efficiency': 'Aero',
        'chassis': 'Chassis',
        'power_unit': 'Power',
        'reliability': 'Reliability',
        'tire_cooling': 'Tires'
    };
    return names[statName] || statName;
}

export { GamePhase, renderGameScreen };
