// Authentication state management
import { api, ApiError } from './api.js';

class AuthManager {
    constructor() {
        this.user = null;
        this.initialized = false;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!localStorage.getItem('access_token');
    }

    /**
     * Initialize auth state (load user if token exists)
     */
    async initialize() {
        if (this.initialized) return;

        if (this.isAuthenticated()) {
            try {
                await this.loadUser();
            } catch (e) {
                // Token invalid, clear it
                this.clearAuth();
            }
        }

        this.initialized = true;
    }

    /**
     * Register a new user
     */
    async register(email, username, password) {
        const response = await api.post('/auth/register', {
            email,
            username,
            password
        });
        return response;
    }

    /**
     * Log in user
     */
    async login(email, password) {
        const response = await api.post('/auth/login', {
            email,
            password
        });

        localStorage.setItem('access_token', response.access_token);
        localStorage.setItem('refresh_token', response.refresh_token);

        await this.loadUser();
        this.notifyAuthChange(true);

        return response;
    }

    /**
     * Log out user
     */
    async logout() {
        try {
            await api.post('/auth/logout');
        } catch (e) {
            // Ignore errors, still clear local state
        } finally {
            this.clearAuth();
            this.notifyAuthChange(false);
        }
    }

    /**
     * Load current user profile
     */
    async loadUser() {
        try {
            this.user = await api.get('/users/me');
            return this.user;
        } catch (e) {
            this.user = null;
            throw e;
        }
    }

    /**
     * Update user profile
     */
    async updateProfile(data) {
        this.user = await api.patch('/users/me', data);
        return this.user;
    }

    /**
     * Change password
     */
    async changePassword(currentPassword, newPassword) {
        await api.post('/users/me/change-password', {
            current_password: currentPassword,
            new_password: newPassword
        });

        // Force re-login after password change
        this.clearAuth();
        this.notifyAuthChange(false);
    }

    /**
     * Delete account
     */
    async deleteAccount() {
        await api.delete('/users/me');
        this.clearAuth();
        this.notifyAuthChange(false);
    }

    /**
     * Clear authentication state
     */
    clearAuth() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        this.user = null;
    }

    /**
     * Notify listeners of auth state change
     */
    notifyAuthChange(authenticated) {
        window.dispatchEvent(new CustomEvent('auth-change', {
            detail: { authenticated, user: this.user }
        }));
    }

    /**
     * Get current user
     */
    getUser() {
        return this.user;
    }
}

// Export singleton instance
export const auth = new AuthManager();
