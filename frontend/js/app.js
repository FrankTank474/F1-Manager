// Main application entry point
import { auth } from './auth.js';
import { router } from './router.js';
import { showAlert, setButtonLoading, validatePassword, validateUsername, isValidEmail, formatDate, clearAlerts } from './utils.js';
import { ApiError } from './api.js';

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
            <li><a href="#/dashboard">Dashboard</a></li>
            <li class="user-menu" id="user-menu">
                <button class="user-menu-button" id="user-menu-btn">
                    ${user?.username || 'User'}
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

async function dashboardPage(container) {
    const user = auth.getUser();
    container.innerHTML = `
        <div class="container" style="padding-top: var(--space-xl);">
            <h1>Welcome, ${user?.username || 'Player'}!</h1>
            <p class="mt-md">Your F1 Manager dashboard. Game features coming soon...</p>

            <div class="card mt-xl">
                <h3>Quick Stats</h3>
                <p class="mt-md text-secondary">Account created: ${formatDate(user?.created_at)}</p>
                <p class="text-secondary">Last login: ${formatDate(user?.last_login)}</p>
            </div>
        </div>
    `;
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
    router.addRoute('/dashboard', dashboardPage, { requiresAuth: true });
    router.addRoute('/profile', profilePage, { requiresAuth: true });
    router.addRoute('/change-password', changePasswordPage, { requiresAuth: true });

    // Start router
    router.start();
}

// Start app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}
