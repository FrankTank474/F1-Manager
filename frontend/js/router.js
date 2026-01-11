// Simple hash-based SPA router
import { auth } from './auth.js';

class Router {
    constructor() {
        this.routes = {};
        this.dynamicRoutes = []; // For pattern-based routes
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
     * Register a dynamic route with a regex pattern
     */
    addDynamicRoute(pattern, handler, options = {}) {
        this.dynamicRoutes.push({ pattern, handler, options });
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
     * Find matching dynamic route
     */
    findDynamicRoute(path) {
        for (const route of this.dynamicRoutes) {
            const match = path.match(route.pattern);
            if (match) {
                return { route, match };
            }
        }
        return null;
    }

    /**
     * Handle current route
     */
    async handleRoute() {
        const path = this.getPath();
        let route = this.routes[path];
        let dynamicMatch = null;

        // Check for dynamic route match if no exact match
        if (!route) {
            const dynamicResult = this.findDynamicRoute(path);
            if (dynamicResult) {
                route = dynamicResult.route;
                dynamicMatch = dynamicResult.match;
            }
        }

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
            if (dynamicMatch) {
                // Pass captured groups to handler
                await route.handler(this.appElement, ...dynamicMatch.slice(1));
            } else {
                await route.handler(this.appElement);
            }
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
