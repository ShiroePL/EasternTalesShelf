// Admin Access Handler - Protects admin-only functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Admin access handler initialized');
    
    // Cache for admin status to avoid unnecessary requests
    let isAdminCache = null;
    let adminCheckPromise = null;
    
    // Function to check if current user is admin
    window.isUserAdmin = function() {
        // Return cached result if available
        if (isAdminCache !== null) {
            return Promise.resolve(isAdminCache);
        }
        
        // If already checking, return the existing promise
        if (adminCheckPromise) {
            return adminCheckPromise;
        }
        
        // Otherwise, perform the check
        adminCheckPromise = fetch('/api/user/is-admin', { 
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.json())
        .then(data => {
            isAdminCache = data.is_admin === true;
            adminCheckPromise = null;
            return isAdminCache;
        })
        .catch(error => {
            console.error('Error checking admin status:', error);
            adminCheckPromise = null;
            // Default to false on error
            return false;
        });
        
        return adminCheckPromise;
    };
    
    // Function to show admin-required popup
    window.showAdminRequiredPopup = function() {
        // Remove any existing popups first
        const existingPopup = document.querySelector('.admin-popup-overlay');
        if (existingPopup) {
            document.body.removeChild(existingPopup);
        }
        
        // Create the modal elements
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'admin-popup-overlay';
        modalOverlay.style.position = 'fixed';
        modalOverlay.style.top = '0';
        modalOverlay.style.left = '0';
        modalOverlay.style.width = '100%';
        modalOverlay.style.height = '100%';
        modalOverlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modalOverlay.style.zIndex = '10000';
        modalOverlay.style.display = 'flex';
        modalOverlay.style.justifyContent = 'center';
        modalOverlay.style.alignItems = 'center';

        const modalBox = document.createElement('div');
        modalBox.className = 'admin-popup-box';
        modalBox.style.backgroundColor = '#2b2b2b';
        modalBox.style.borderRadius = '8px';
        modalBox.style.padding = '20px';
        modalBox.style.width = '400px';
        modalBox.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
        modalBox.style.color = 'white';
        modalBox.style.textAlign = 'center';

        const iconElement = document.createElement('i');
        iconElement.className = 'fas fa-lock';
        iconElement.style.fontSize = '48px';
        iconElement.style.color = '#007bff';
        iconElement.style.marginBottom = '15px';
        iconElement.style.display = 'block';

        const titleElement = document.createElement('h3');
        titleElement.textContent = 'Admin Access Required';
        titleElement.style.marginBottom = '10px';

        const messageElement = document.createElement('p');
        messageElement.textContent = 'This feature is only available to administrators.';
        messageElement.style.marginBottom = '20px';

        const closeButton = document.createElement('button');
        closeButton.textContent = 'Close';
        closeButton.className = 'btn btn-primary';
        closeButton.style.padding = '8px 20px';
        closeButton.onclick = () => {
            document.body.removeChild(modalOverlay);
        };

        // Assemble the modal
        modalBox.appendChild(iconElement);
        modalBox.appendChild(titleElement);
        modalBox.appendChild(messageElement);
        modalBox.appendChild(closeButton);
        modalOverlay.appendChild(modalBox);

        // Add to the document
        document.body.appendChild(modalOverlay);
    };
    
    // The key function: wraps any function with admin check
    window.requireAdmin = function(fn) {
        return function(...args) {
            return window.isUserAdmin().then(isAdmin => {
                if (isAdmin) {
                    // User is admin, execute the function
                    return fn.apply(this, args);
                } else {
                    // User is not admin, show popup
                    window.showAdminRequiredPopup();
                    return Promise.reject("Admin access required");
                }
            });
        };
    };
    
    // Override fetch globally to catch admin-required errors
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
        return originalFetch(url, options).then(response => {
            if (response.status === 403) {
                return response.clone().json().catch(() => ({})).then(data => {
                    if (data && data.message && (
                        data.message.includes('administrator') || 
                        data.message.includes('admin') ||
                        data.error === 'Unauthorized'
                    )) {
                        window.showAdminRequiredPopup();
                    }
                    return response;
                });
            }
            return response;
        });
    };
});