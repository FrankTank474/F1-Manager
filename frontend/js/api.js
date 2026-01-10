// API client with automatic token handling

class ApiError extends Error {
    constructor(message, status, data = null) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.data = data;
    }
}

class ApiClient {
    constructor() {
        this.baseUrl = '/api/v1';
        this.refreshPromise = null;
    }

    /**
     * Make an API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = localStorage.getItem('access_token');

        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            // Handle 401 - try to refresh token
            if (response.status === 401 && token && !options._isRetry) {
                const refreshed = await this.refreshToken();
                if (refreshed) {
                    // Retry original request
                    return this.request(endpoint, { ...options, _isRetry: true });
                }
                // Refresh failed, redirect to login
                this.handleAuthFailure();
                throw new ApiError('Session expired', 401);
            }

            const data = await response.json().catch(() => null);

            if (!response.ok) {
                const message = data?.detail || 'Request failed';
                throw new ApiError(message, response.status, data);
            }

            return data;
        } catch (error) {
            if (error instanceof ApiError) throw error;
            throw new ApiError('Network error', 0);
        }
    }

    /**
     * Refresh the access token
     */
    async refreshToken() {
        // Prevent multiple simultaneous refresh attempts
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) return false;

        this.refreshPromise = (async () => {
            try {
                const response = await fetch(`${this.baseUrl}/auth/refresh`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: refreshToken })
                });

                if (response.ok) {
                    const data = await response.json();
                    localStorage.setItem('access_token', data.access_token);
                    return true;
                }
            } catch (e) {
                console.error('Token refresh failed:', e);
            }

            // Clear tokens on refresh failure
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            return false;
        })();

        const result = await this.refreshPromise;
        this.refreshPromise = null;
        return result;
    }

    /**
     * Handle authentication failure
     */
    handleAuthFailure() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        // Dispatch custom event for auth state change
        window.dispatchEvent(new CustomEvent('auth-change', { detail: { authenticated: false } }));
    }

    // Convenience methods
    get(endpoint) {
        return this.request(endpoint);
    }

    post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    patch(endpoint, data) {
        return this.request(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// Export singleton instance
export const api = new ApiClient();
export { ApiError };
