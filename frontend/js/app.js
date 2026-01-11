// Main application entry point
import { auth } from './auth.js';
import { router } from './router.js';
import { showAlert, setButtonLoading, validatePassword, validateUsername, isValidEmail, formatDate, clearAlerts, escapeHtml, debounce } from './utils.js';
import { api, ApiError } from './api.js';
import { startGameSession } from './gameplay.js';
import { modalConfirm } from './modal.js';

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    if (theme === 'dark') {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="5"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>`;
    } else {
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>`;
    }
}

// Update navbar based on auth state
function updateNavbar() {
    const navAuth = document.getElementById('nav-auth');
    if (!navAuth) return;

    if (auth.isAuthenticated()) {
        const user = auth.getUser();
        navAuth.innerHTML = `
            <li><a href="#/games">My Games</a></li>
            <li class="user-menu" id="user-menu">
                <button class="user-menu-button" id="user-menu-btn">
                    ${escapeHtml(user?.username || 'User')}
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                </button>
                <div class="user-menu-dropdown">
                    <a href="#/profile">Profile</a>
                    <a href="#/change-password">Change Password</a>
                    <div class="divider"></div>
                    <button id="logout-btn">Logout</button>
                </div>
            </li>
        `;

        // User menu toggle
        const menuBtn = document.getElementById('user-menu-btn');
        const userMenu = document.getElementById('user-menu');

        menuBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            userMenu.classList.toggle('open');
        });

        // Close menu when clicking outside
        document.addEventListener('click', () => {
            userMenu?.classList.remove('open');
        });

        // Logout button
        document.getElementById('logout-btn')?.addEventListener('click', async () => {
            await auth.logout();
            router.navigate('/');
        });
    } else {
        navAuth.innerHTML = `
            <li><a href="#/login">Login</a></li>
            <li><a href="#/register" class="btn btn-primary btn-sm">Sign Up</a></li>
        `;
    }
}

// Page handlers
async function welcomePage(container) {
    container.innerHTML = `
        <div class="hero">
            <h1 class="hero-title">F1 <span>Manager</span> 2026</h1>
            <p class="hero-subtitle">
                Build your dream team, develop your car, and compete for the World Championship.
                The ultimate Formula 1 management experience.
            </p>
            <div class="hero-buttons">
                <a href="#/register" class="btn btn-primary btn-lg">Get Started</a>
                <a href="#/login" class="btn btn-secondary btn-lg">Sign In</a>
            </div>
        </div>
        <div class="features container">
            <div class="feature">
                <div class="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                        <circle cx="9" cy="7" r="4"/>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                    </svg>
                </div>
                <h3 class="feature-title">Manage Your Team</h3>
                <p class="feature-description">Sign drivers, manage contracts, and build a championship-winning squad.</p>
            </div>
            <div class="feature">
                <div class="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                    </svg>
                </div>
                <h3 class="feature-title">Develop Your Car</h3>
                <p class="feature-description">Invest in R&D, upgrade components, and fine-tune your car for each circuit.</p>
            </div>
            <div class="feature">
                <div class="feature-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                    </svg>
                </div>
                <h3 class="feature-title">Win Championships</h3>
                <p class="feature-description">Compete across a full season and claim the Drivers' and Constructors' titles.</p>
            </div>
        </div>
    `;
}

async function loginPage(container) {
    container.innerHTML = `
        <div class="page-center">
            <div class="card container-sm">
                <div class="card-header">
                    <h2 class="card-title">Welcome Back</h2>
                    <p class="card-subtitle">Sign in to continue to F1 Manager</p>
                </div>
                <form id="login-form">
                    <div class="form-group">
                        <label class="form-label" for="email">Email</label>
                        <input type="email" id="email" class="form-input" placeholder="you@example.com" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="password">Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="password" class="form-input" placeholder="Enter your password" required>
                            <button type="button" class="password-toggle" id="toggle-password">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block btn-lg">Sign In</button>
                </form>
                <p class="form-link">
                    Don't have an account? <a href="#/register">Sign up</a>
                </p>
            </div>
        </div>
    `;

    // Password toggle
    const toggleBtn = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');
    toggleBtn?.addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
    });

    // Form submission
    const form = document.getElementById('login-form');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        clearAlerts(form);
        setButtonLoading(submitBtn, true);

        try {
            await auth.login(email, password);
            updateNavbar();
            router.navigate('/dashboard');
        } catch (error) {
            const message = error instanceof ApiError ? error.message : 'Login failed';
            showAlert(form, message, 'error');
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

async function registerPage(container) {
    container.innerHTML = `
        <div class="page-center">
            <div class="card container-sm">
                <div class="card-header">
                    <h2 class="card-title">Create Account</h2>
                    <p class="card-subtitle">Join F1 Manager and start your journey</p>
                </div>
                <form id="register-form">
                    <div class="form-group">
                        <label class="form-label" for="username">Username</label>
                        <input type="text" id="username" class="form-input" placeholder="Choose a username" required>
                        <p class="form-hint">3-50 characters, letters, numbers, and underscores only</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="email">Email</label>
                        <input type="email" id="email" class="form-input" placeholder="you@example.com" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="password">Password</label>
                        <div class="password-input-wrapper">
                            <input type="password" id="password" class="form-input" placeholder="Create a password" required>
                            <button type="button" class="password-toggle" id="toggle-password">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                                    <circle cx="12" cy="12" r="3"/>
                                </svg>
                            </button>
                        </div>
                        <p class="form-hint">Min 8 chars, with uppercase, lowercase, and number</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="confirm-password">Confirm Password</label>
                        <input type="password" id="confirm-password" class="form-input" placeholder="Confirm your password" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block btn-lg">Create Account</button>
                </form>
                <p class="form-link">
                    Already have an account? <a href="#/login">Sign in</a>
                </p>
            </div>
        </div>
    `;

    // Password toggle
    const toggleBtn = document.getElementById('toggle-password');
    const passwordInput = document.getElementById('password');
    toggleBtn?.addEventListener('click', () => {
        const type = passwordInput.type === 'password' ? 'text' : 'password';
        passwordInput.type = type;
    });

    // Form submission
    const form = document.getElementById('register-form');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        clearAlerts(form);

        // Validate
        const usernameErrors = validateUsername(username);
        if (usernameErrors.length) {
            showAlert(form, usernameErrors[0], 'error');
            return;
        }

        if (!isValidEmail(email)) {
            showAlert(form, 'Please enter a valid email address', 'error');
            return;
        }

        const passwordErrors = validatePassword(password);
        if (passwordErrors.length) {
            showAlert(form, passwordErrors[0], 'error');
            return;
        }

        if (password !== confirmPassword) {
            showAlert(form, 'Passwords do not match', 'error');
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            await auth.register(email, username, password);
            showAlert(form, 'Registration successful! Please sign in.', 'success');
            setTimeout(() => router.navigate('/login'), 2000);
        } catch (error) {
            const message = error instanceof ApiError ? error.message : 'Registration failed';
            showAlert(form, message, 'error');
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

async function gamesPage(container) {
    const user = auth.getUser();
    container.innerHTML = `
        <div class="container" style="padding-top: var(--space-xl);">
            <div class="flex" style="justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-md);">
                <h1>My Games</h1>
                <a href="#/games/new" class="btn btn-primary">Create New Game</a>
            </div>

            <div id="pending-invites-section" class="mt-xl" style="display: none;">
                <h3>Pending Invites</h3>
                <div id="pending-invites-list" class="mt-md"></div>
            </div>

            <div class="mt-xl">
                <h3>Your Games</h3>
                <div id="games-list" class="mt-md">
                    <div class="app-loading" style="min-height: 200px;">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Load games and invites
    await Promise.all([loadGames(), loadPendingInvites()]);
}

async function loadGames() {
    const gamesList = document.getElementById('games-list');
    if (!gamesList) return;

    try {
        const games = await api.get('/games');

        if (games.length === 0) {
            gamesList.innerHTML = `
                <div class="card" style="text-align: center; padding: var(--space-2xl);">
                    <p style="color: var(--text-secondary);">No games yet. Create your first game to get started!</p>
                    <a href="#/games/new" class="btn btn-primary mt-lg">Create New Game</a>
                </div>
            `;
            return;
        }

        gamesList.innerHTML = games.map(game => `
            <div class="card mb-md game-card" data-game-id="${game.id}">
                <div class="flex" style="justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: var(--space-md);">
                    <div>
                        <h4 style="margin-bottom: var(--space-xs);">${escapeHtml(game.name)}</h4>
                        <p style="color: var(--text-secondary); font-size: var(--font-sm);">
                            Created by ${escapeHtml(game.creator_username)} &bull;
                            ${game.player_count}/${game.max_players} players &bull;
                            <span class="status-badge status-${game.status}">${game.status}</span>
                        </p>
                    </div>
                    <div class="flex gap-sm">
                        ${game.status === 'pending' && game.is_creator ? `
                            <button class="btn btn-primary btn-sm start-game-btn" data-game-id="${game.id}">Start Game</button>
                            <a href="#/games/${game.id}" class="btn btn-secondary btn-sm">Manage</a>
                        ` : ''}
                        ${game.status === 'active' || game.status === 'stopped' ? `
                            <a href="#/games/${game.id}/play" class="btn btn-primary btn-sm">${game.status === 'stopped' ? 'Resume' : 'Play'}</a>
                        ` : ''}
                        ${game.status === 'pending' && !game.is_creator ? `
                            <span style="color: var(--text-muted); font-size: var(--font-sm);">Waiting to start...</span>
                        ` : ''}
                        <button class="btn btn-danger btn-sm delete-game-btn" data-game-id="${game.id}" data-game-name="${escapeHtml(game.name)}">Delete</button>
                    </div>
                </div>
            </div>
        `).join('');

        // Add start game button event listeners
        gamesList.querySelectorAll('.start-game-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const gameId = btn.dataset.gameId;

                setButtonLoading(btn, true);
                try {
                    await api.post(`/games/${gameId}/start`);
                    await loadGames();
                } catch (error) {
                    showAlert(gamesList, error.message || 'Failed to start game', 'error');
                    setButtonLoading(btn, false);
                }
            });
        });

        // Add delete button event listeners
        gamesList.querySelectorAll('.delete-game-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                const gameId = btn.dataset.gameId;
                const gameName = btn.dataset.gameName;
                const confirmed = await modalConfirm(`Are you sure you want to delete "${gameName}"? This cannot be undone.`, 'Delete Game');
                if (!confirmed) return;

                setButtonLoading(btn, true);
                try {
                    await api.delete(`/games/${gameId}`);
                    await loadGames();
                } catch (error) {
                    showAlert(gamesList, error.message || 'Failed to delete game', 'error');
                    setButtonLoading(btn, false);
                }
            });
        });
    } catch (error) {
        gamesList.innerHTML = `
            <div class="alert alert-error">Failed to load games. Please try again.</div>
        `;
    }
}

async function loadPendingInvites() {
    const section = document.getElementById('pending-invites-section');
    const list = document.getElementById('pending-invites-list');
    if (!section || !list) return;

    try {
        const invites = await api.get('/games/invites/pending');

        if (invites.length === 0) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';
        list.innerHTML = invites.map(invite => `
            <div class="card mb-md invite-card" data-invite-id="${invite.id}">
                <div class="flex" style="justify-content: space-between; align-items: center; flex-wrap: wrap; gap: var(--space-md);">
                    <div>
                        <p><strong>${escapeHtml(invite.inviter_username)}</strong> invited you to join <strong>${escapeHtml(invite.game_name)}</strong></p>
                        <p style="color: var(--text-muted); font-size: var(--font-sm);">${formatDate(invite.created_at)}</p>
                    </div>
                    <div class="flex gap-sm">
                        <button class="btn btn-primary btn-sm accept-invite-btn" data-invite-id="${invite.id}">Accept</button>
                        <button class="btn btn-secondary btn-sm decline-invite-btn" data-invite-id="${invite.id}">Decline</button>
                    </div>
                </div>
            </div>
        `).join('');

        // Add event listeners
        list.querySelectorAll('.accept-invite-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const inviteId = btn.dataset.inviteId;
                setButtonLoading(btn, true);
                try {
                    await api.post(`/games/invites/${inviteId}/accept`);
                    await Promise.all([loadGames(), loadPendingInvites()]);
                } catch (error) {
                    showAlert(list, error.message || 'Failed to accept invite', 'error');
                }
            });
        });

        list.querySelectorAll('.decline-invite-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const inviteId = btn.dataset.inviteId;
                setButtonLoading(btn, true);
                try {
                    await api.post(`/games/invites/${inviteId}/decline`);
                    await loadPendingInvites();
                } catch (error) {
                    showAlert(list, error.message || 'Failed to decline invite', 'error');
                }
            });
        });
    } catch (error) {
        section.style.display = 'none';
    }
}

async function newGamePage(container) {
    container.innerHTML = `
        <div class="page-center">
            <div class="card container-sm">
                <div class="card-header">
                    <h2 class="card-title">Create New Game</h2>
                    <p class="card-subtitle">Start a new F1 Manager career</p>
                </div>
                <form id="create-game-form">
                    <div class="form-group">
                        <label class="form-label" for="game-name">Game Name</label>
                        <input type="text" id="game-name" class="form-input" placeholder="My Championship" required maxlength="100">
                    </div>
                    <button type="submit" class="btn btn-primary btn-block btn-lg">Create Game</button>
                </form>
                <p class="form-link">
                    <a href="#/games">Back to Games</a>
                </p>
            </div>
        </div>
    `;

    const form = document.getElementById('create-game-form');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('game-name').value.trim();
        const submitBtn = form.querySelector('button[type="submit"]');

        if (!name) {
            showAlert(form, 'Please enter a game name', 'error');
            return;
        }

        clearAlerts(form);
        setButtonLoading(submitBtn, true);

        try {
            const game = await api.post('/games', { name });
            router.navigate(`/games/${game.id}`);
        } catch (error) {
            const message = error instanceof ApiError ? error.message : 'Failed to create game';
            showAlert(form, message, 'error');
            setButtonLoading(submitBtn, false);
        }
    });
}

async function gameDetailPage(container, gameId) {
    container.innerHTML = `
        <div class="container" style="padding-top: var(--space-xl);">
            <div class="app-loading" style="min-height: 300px;">
                <div class="spinner spinner-lg"></div>
            </div>
        </div>
    `;

    try {
        const game = await api.get(`/games/${gameId}`);
        const invites = game.status === 'pending' ? await api.get(`/games/${gameId}/invites`) : [];
        const user = auth.getUser();
        const isCreator = game.creator_id === user?.id;

        container.innerHTML = `
            <div class="container" style="padding-top: var(--space-xl);">
                <div class="flex" style="justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: var(--space-md);">
                    <div>
                        <a href="#/games" style="color: var(--text-secondary); font-size: var(--font-sm);">&larr; Back to Games</a>
                        <h1 class="mt-sm">${escapeHtml(game.name)}</h1>
                        <p style="color: var(--text-secondary);">
                            Status: <span class="status-badge status-${game.status}">${game.status}</span>
                        </p>
                    </div>
                    ${isCreator && game.status === 'pending' ? `
                        <div class="flex gap-sm">
                            <button id="start-game-btn" class="btn btn-primary">Start Game</button>
                            <button id="delete-game-btn" class="btn btn-secondary">Delete Game</button>
                        </div>
                    ` : ''}
                </div>

                <div class="card mt-xl">
                    <h3>Players (${game.players.length}/${game.max_players})</h3>
                    <div class="mt-md" id="players-list">
                        ${game.players.map(p => `
                            <div class="flex" style="justify-content: space-between; align-items: center; padding: var(--space-sm) 0; border-bottom: 1px solid var(--border-color);">
                                <span>${escapeHtml(p.username)} ${p.is_creator ? '<span style="color: var(--accent-primary);">(Creator)</span>' : ''}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>

                ${isCreator && game.status === 'pending' ? `
                    <div class="card mt-lg">
                        <h3>Invite Players</h3>
                        <div class="mt-md">
                            <div class="form-group">
                                <label class="form-label" for="invite-username">Search by username</label>
                                <input type="text" id="invite-username" class="form-input" placeholder="Type to search...">
                                <div id="user-search-results" class="mt-sm"></div>
                            </div>
                        </div>

                        ${invites.length > 0 ? `
                            <h4 class="mt-lg">Pending Invites</h4>
                            <div id="pending-invites" class="mt-md">
                                ${invites.map(inv => `
                                    <div class="flex" style="justify-content: space-between; align-items: center; padding: var(--space-sm) 0; border-bottom: 1px solid var(--border-color);">
                                        <span>${escapeHtml(inv.invitee_username)}</span>
                                        <button class="btn btn-secondary btn-sm withdraw-invite-btn" data-invite-id="${inv.id}">Withdraw</button>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
            </div>
        `;

        // Event listeners for creator actions
        if (isCreator && game.status === 'pending') {
            // Start game
            document.getElementById('start-game-btn')?.addEventListener('click', async () => {
                const confirmed = await modalConfirm('Are you sure you want to start this game?', 'Start Game');
                if (!confirmed) return;
                const btn = document.getElementById('start-game-btn');
                setButtonLoading(btn, true);
                try {
                    await api.post(`/games/${gameId}/start`);
                    router.navigate(`/games/${gameId}`);
                } catch (error) {
                    showAlert(container.querySelector('.container'), error.message || 'Failed to start game', 'error');
                    setButtonLoading(btn, false);
                }
            });

            // Delete game
            document.getElementById('delete-game-btn')?.addEventListener('click', async () => {
                const confirmed = await modalConfirm('Are you sure you want to delete this game? This cannot be undone.', 'Delete Game');
                if (!confirmed) return;
                const btn = document.getElementById('delete-game-btn');
                setButtonLoading(btn, true);
                try {
                    await api.delete(`/games/${gameId}`);
                    router.navigate('/games');
                } catch (error) {
                    showAlert(container.querySelector('.container'), error.message || 'Failed to delete game', 'error');
                    setButtonLoading(btn, false);
                }
            });

            // User search for invites
            const searchInput = document.getElementById('invite-username');
            const searchResults = document.getElementById('user-search-results');

            const doSearch = debounce(async (query) => {
                if (query.length < 2) {
                    searchResults.innerHTML = '';
                    return;
                }
                try {
                    const users = await api.get(`/games/users/search?q=${encodeURIComponent(query)}`);
                    if (users.length === 0) {
                        searchResults.innerHTML = '<p style="color: var(--text-muted); font-size: var(--font-sm);">No users found</p>';
                        return;
                    }
                    searchResults.innerHTML = users.map(u => `
                        <div class="flex" style="justify-content: space-between; align-items: center; padding: var(--space-sm); background: var(--bg-tertiary); border-radius: var(--radius-md); margin-bottom: var(--space-xs);">
                            <span>${escapeHtml(u.username)}</span>
                            <button class="btn btn-primary btn-sm invite-user-btn" data-username="${escapeHtml(u.username)}">Invite</button>
                        </div>
                    `).join('');

                    // Add invite button listeners
                    searchResults.querySelectorAll('.invite-user-btn').forEach(btn => {
                        btn.addEventListener('click', async () => {
                            const username = btn.dataset.username;
                            setButtonLoading(btn, true);
                            try {
                                await api.post(`/games/${gameId}/invites`, { username });
                                searchInput.value = '';
                                searchResults.innerHTML = '';
                                // Reload page to show new invite
                                await gameDetailPage(container, gameId);
                            } catch (error) {
                                showAlert(searchResults, error.message || 'Failed to send invite', 'error');
                                setButtonLoading(btn, false);
                            }
                        });
                    });
                } catch (error) {
                    searchResults.innerHTML = '<p style="color: var(--error);">Search failed</p>';
                }
            }, 300);

            searchInput?.addEventListener('input', (e) => doSearch(e.target.value));

            // Withdraw invite buttons
            document.querySelectorAll('.withdraw-invite-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const inviteId = btn.dataset.inviteId;
                    setButtonLoading(btn, true);
                    try {
                        await api.delete(`/games/invites/${inviteId}`);
                        await gameDetailPage(container, gameId);
                    } catch (error) {
                        showAlert(container.querySelector('.container'), error.message || 'Failed to withdraw invite', 'error');
                        setButtonLoading(btn, false);
                    }
                });
            });
        }
    } catch (error) {
        container.innerHTML = `
            <div class="container" style="padding-top: var(--space-xl);">
                <div class="alert alert-error">Failed to load game. It may have been deleted.</div>
                <a href="#/games" class="btn btn-secondary mt-lg">Back to Games</a>
            </div>
        `;
    }
}

async function profilePage(container) {
    const user = auth.getUser();
    container.innerHTML = `
        <div class="page-center">
            <div class="card container-sm">
                <div class="card-header">
                    <h2 class="card-title">Your Profile</h2>
                </div>
                <form id="profile-form">
                    <div class="form-group">
                        <label class="form-label" for="username">Username</label>
                        <input type="text" id="username" class="form-input" value="${user?.username || ''}" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="email">Email</label>
                        <input type="email" id="email" class="form-input" value="${user?.email || ''}" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Save Changes</button>
                </form>
                <div class="divider">Account Info</div>
                <p class="text-center" style="color: var(--text-secondary); font-size: var(--font-sm);">
                    Member since: ${formatDate(user?.created_at)}
                </p>
            </div>
        </div>
    `;

    const form = document.getElementById('profile-form');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const email = document.getElementById('email').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        clearAlerts(form);
        setButtonLoading(submitBtn, true);

        try {
            await auth.updateProfile({ username, email });
            updateNavbar();
            showAlert(form, 'Profile updated successfully!', 'success');
        } catch (error) {
            const message = error instanceof ApiError ? error.message : 'Update failed';
            showAlert(form, message, 'error');
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

async function changePasswordPage(container) {
    container.innerHTML = `
        <div class="page-center">
            <div class="card container-sm">
                <div class="card-header">
                    <h2 class="card-title">Change Password</h2>
                    <p class="card-subtitle">Update your account password</p>
                </div>
                <form id="password-form">
                    <div class="form-group">
                        <label class="form-label" for="current-password">Current Password</label>
                        <input type="password" id="current-password" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-password">New Password</label>
                        <input type="password" id="new-password" class="form-input" required>
                        <p class="form-hint">Min 8 chars, with uppercase, lowercase, and number</p>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="confirm-password">Confirm New Password</label>
                        <input type="password" id="confirm-password" class="form-input" required>
                    </div>
                    <button type="submit" class="btn btn-primary btn-block">Change Password</button>
                </form>
                <p class="form-link">
                    <a href="#/profile">Back to Profile</a>
                </p>
            </div>
        </div>
    `;

    const form = document.getElementById('password-form');
    form?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const currentPassword = document.getElementById('current-password').value;
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        clearAlerts(form);

        const passwordErrors = validatePassword(newPassword);
        if (passwordErrors.length) {
            showAlert(form, passwordErrors[0], 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            showAlert(form, 'New passwords do not match', 'error');
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            await auth.changePassword(currentPassword, newPassword);
            showAlert(form, 'Password changed! Please sign in again.', 'success');
            setTimeout(() => {
                updateNavbar();
                router.navigate('/login');
            }, 2000);
        } catch (error) {
            const message = error instanceof ApiError ? error.message : 'Password change failed';
            showAlert(form, message, 'error');
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

// Initialize app
async function initApp() {
    initTheme();

    // Theme toggle button
    document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);

    // Initialize auth
    await auth.initialize();

    // Update navbar
    updateNavbar();

    // Listen for auth changes
    window.addEventListener('auth-change', () => {
        updateNavbar();
    });

    // Setup routes
    const appElement = document.getElementById('app');
    router.init(appElement);

    router.addRoute('/', welcomePage, { guestOnly: true });
    router.addRoute('/login', loginPage, { guestOnly: true });
    router.addRoute('/register', registerPage, { guestOnly: true });
    router.addRoute('/games', gamesPage, { requiresAuth: true });
    router.addRoute('/games/new', newGamePage, { requiresAuth: true });
    router.addRoute('/dashboard', gamesPage, { requiresAuth: true }); // Redirect dashboard to games
    router.addRoute('/profile', profilePage, { requiresAuth: true });
    router.addRoute('/change-password', changePasswordPage, { requiresAuth: true });

    // Dynamic route for game detail pages
    router.addDynamicRoute(/^\/games\/([a-f0-9-]+)$/, gameDetailPage, { requiresAuth: true });

    // Dynamic route for game play
    router.addDynamicRoute(/^\/games\/([a-f0-9-]+)\/play$/, gamePlayPage, { requiresAuth: true });

    // Start router
    router.start();
}

/**
 * Game Play Page - launches the game session
 */
async function gamePlayPage(container, gameId) {
    container.innerHTML = `
        <div class="app-loading" style="min-height: 400px;">
            <div class="spinner spinner-lg"></div>
        </div>
    `;

    await startGameSession(gameId, container);
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
