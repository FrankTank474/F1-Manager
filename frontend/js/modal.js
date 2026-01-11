// Modal component for F1 Manager
// Replaces default browser alerts with styled modal dialogs

/**
 * Show a styled modal dialog
 * @param {Object} options - Modal options
 * @param {string} options.title - Modal title
 * @param {string} options.message - Modal message
 * @param {string} options.type - Modal type: 'info', 'warning', 'error', 'success'
 * @param {Array} options.buttons - Array of button configs: { text, type, onClick }
 * @returns {Promise} - Resolves with the clicked button's value
 */
export function showModal({ title = 'Notice', message, type = 'info', buttons = null }) {
    return new Promise((resolve) => {
        // Default to OK button if none provided
        if (!buttons) {
            buttons = [{ text: 'OK', type: 'primary', value: true }];
        }

        // Create modal elements
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';

        const modal = document.createElement('div');
        modal.className = `modal modal-${type}`;

        // Icon based on type
        const icons = {
            info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>`,
            warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>`,
            error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>`,
            success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>`
        };

        modal.innerHTML = `
            <div class="modal-icon modal-icon-${type}">
                ${icons[type] || icons.info}
            </div>
            <h2 class="modal-title">${title}</h2>
            <p class="modal-message">${message}</p>
            <div class="modal-buttons">
                ${buttons.map((btn, index) => `
                    <button class="btn btn-${btn.type || 'secondary'}" data-index="${index}">
                        ${btn.text}
                    </button>
                `).join('')}
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Trigger animation
        requestAnimationFrame(() => {
            overlay.classList.add('modal-visible');
        });

        // Handle button clicks
        modal.querySelectorAll('button').forEach(button => {
            button.addEventListener('click', () => {
                const index = parseInt(button.dataset.index);
                const btnConfig = buttons[index];

                overlay.classList.remove('modal-visible');
                setTimeout(() => {
                    overlay.remove();
                    resolve(btnConfig.value !== undefined ? btnConfig.value : index);
                }, 200);
            });
        });

        // Handle escape key
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                overlay.classList.remove('modal-visible');
                setTimeout(() => {
                    overlay.remove();
                    resolve(false);
                }, 200);
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);

        // Focus first button
        modal.querySelector('button')?.focus();
    });
}

/**
 * Show an alert modal (replacement for window.alert)
 * @param {string} message - The message to display
 * @param {string} title - Optional title
 * @returns {Promise}
 */
export function modalAlert(message, title = 'Notice') {
    return showModal({
        title,
        message,
        type: 'info',
        buttons: [{ text: 'OK', type: 'primary', value: true }]
    });
}

/**
 * Show a confirm modal (replacement for window.confirm)
 * @param {string} message - The message to display
 * @param {string} title - Optional title
 * @returns {Promise<boolean>}
 */
export function modalConfirm(message, title = 'Confirm') {
    return showModal({
        title,
        message,
        type: 'warning',
        buttons: [
            { text: 'Cancel', type: 'secondary', value: false },
            { text: 'Confirm', type: 'primary', value: true }
        ]
    });
}

/**
 * Show an error modal
 * @param {string} message - The error message
 * @param {string} title - Optional title
 * @returns {Promise}
 */
export function modalError(message, title = 'Error') {
    return showModal({
        title,
        message,
        type: 'error',
        buttons: [{ text: 'OK', type: 'danger', value: true }]
    });
}

/**
 * Show a success modal
 * @param {string} message - The success message
 * @param {string} title - Optional title
 * @returns {Promise}
 */
export function modalSuccess(message, title = 'Success') {
    return showModal({
        title,
        message,
        type: 'success',
        buttons: [{ text: 'OK', type: 'primary', value: true }]
    });
}
