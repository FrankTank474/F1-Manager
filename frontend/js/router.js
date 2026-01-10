// Simple hash-based SPA router
import { auth } from './auth.js';

class Router {
    constructor() {
        this.routes = {};
        this.currentRoute = null;
        this.appElement = null;

        // Listen for hash changes
        window.addEventListener('hashchange', () => this.handleRoute());
    }

    /**
     * Initialize router with app element
     */
    init(appElement) {
        this.appElement = appElement;
    }

    /**
     * Register a route
     */
    addRoute(path, handler, options = {}) {
        this.routes[path] = { handler, options };
    }

    /**
     * Navigate to a path
     */
    navigate(path) {
        window.location.hash = path;
    }

    /**
     * Get current path from hash
     */
    getPath() {
        return window.location.hash.slice(1) || '/';
    }

    /**
     * Handle current route
     */
    async handleRoute() {
        const path = this.getPath();
        const route = this.routes[path];

        if (!route) {
            // Default to welcome or dashboard based on auth state
            if (auth.isAuthenticated()) {
                this.navigate('/dashboard');
            } else {
                this.navigate('/');
            }
            return;
        }

        // Check if route requires auth
        if (route.options.requiresAuth && !auth.isAuthenticated()) {
            this.navigate('/login');
            return;
        }

        // Check if route is only for guests (login/register)
        if (route.options.guestOnly && auth.isAuthenticated()) {
            this.navigate('/dashboard');
            return;
        }

        this.currentRoute = path;

        // Call route handler
        try {
            await route.handler(this.appElement);
        } catch (e) {
            console.error('Route handler error:', e);
            this.appElement.innerHTML = `
                <div class="page-center">
                    <div class="card container-sm">
                        <h2>Error</h2>
                        <p>Something went wrong loading this page.</p>
                        <a href="#/" class="btn btn-primary mt-lg">Go Home</a>
                    </div>
                </div>
            `;
        }
    }

    /**
     * Start the router
     */
    start() {
        this.handleRoute();
    }
}

// Export singleton instance
export const router = new Router();
