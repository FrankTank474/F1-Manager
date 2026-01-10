// Utility functions

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show an alert message
 */
export function showAlert(container, message, type = 'error') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;

    // Remove existing alerts
    const existingAlerts = container.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());

    // Insert at the beginning
    container.insertBefore(alertDiv, container.firstChild);

    // Auto-remove after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => alertDiv.remove(), 5000);
    }

    return alertDiv;
}

/**
 * Clear all alerts in a container
 */
export function clearAlerts(container) {
    const alerts = container.querySelectorAll('.alert');
    alerts.forEach(alert => alert.remove());
}

/**
 * Show loading state on a button
 */
export function setButtonLoading(button, loading = true) {
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner"></span> Loading...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

/**
 * Validate email format
 */
export function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Validate password strength
 */
export function validatePassword(password) {
    const errors = [];

    if (password.length < 8) {
        errors.push('Password must be at least 8 characters');
    }
    if (!/[A-Z]/.test(password)) {
        errors.push('Password must contain an uppercase letter');
    }
    if (!/[a-z]/.test(password)) {
        errors.push('Password must contain a lowercase letter');
    }
    if (!/\d/.test(password)) {
        errors.push('Password must contain a digit');
    }

    return errors;
}

/**
 * Validate username format
 */
export function validateUsername(username) {
    const errors = [];

    if (username.length < 3) {
        errors.push('Username must be at least 3 characters');
    }
    if (username.length > 50) {
        errors.push('Username must be at most 50 characters');
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        errors.push('Username can only contain letters, numbers, and underscores');
    }

    return errors;
}

/**
 * Format date for display
 */
export function formatDate(dateString) {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
