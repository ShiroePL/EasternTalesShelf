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

/**
 * Admin Access Handler
 * 
 * This file handles the routing of GraphQL requests based on user authentication status.
 * It provides a unified interface for making GraphQL requests that automatically 
 * routes to either the authenticated or public endpoint.
 */

// Check if user is logged in - relies on a global variable or cookie that should be set by the server
function isUserLoggedIn() {
    // Method 1: Check for a specific class on the body that's added when logged in
    if (document.body.classList.contains('logged-in')) {
        return true;
    }
    
    // Method 2: Check for a specific cookie or localStorage value
    // This depends on how your app handles login state
    if (document.cookie.split(';').some(item => item.trim().startsWith('logged_in='))) {
        return true;
    }
    
    // Method 3: Check for user info in localStorage or sessionStorage
    if (localStorage.getItem('user_info') || sessionStorage.getItem('user_info')) {
        return true;
    }
    
    return false;
}

/**
 * Send a GraphQL request to the appropriate endpoint based on user authentication status
 * 
 * @param {Object} requestData - GraphQL request body (contains query and variables)
 * @param {boolean} forcePublic - Force using the public endpoint even if logged in
 * @returns {Promise} - Promise resolving to the GraphQL response
 */
async function sendGraphQLRequest(requestData, forcePublic = false) {
    // Determine which endpoint to use based on authentication status
    const endpoint = (!isUserLoggedIn() || forcePublic) 
        ? '/graphql/public' 
        : '/graphql/';
    
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Include CSRF token if your app uses it
                'X-CSRFToken': document.cookie.split('; ').find(row => row.startsWith('csrf_token='))?.split('=')[1] || '',
                // Include the GraphQL safety key from the global variable
                'X-GraphQL-Key': typeof GRAPHQL_SAFETY_KEY !== 'undefined' ? GRAPHQL_SAFETY_KEY : ''
            },
            body: JSON.stringify(requestData),
            credentials: 'same-origin'  // Include cookies in the request
        });
        
        if (!response.ok) {
            // For demo purposes, if we're logged in and get a 401/403, try the public endpoint
            if ((response.status === 401 || response.status === 403) && !forcePublic && endpoint !== '/graphql/public') {
                console.warn('Authentication error, falling back to public endpoint');
                return sendGraphQLRequest(requestData, true);
            }
            
            throw new Error(`HTTP error ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('GraphQL request failed:', error);
        throw error;
    }
}

// Export the main function for use in other modules
window.sendGraphQLRequest = sendGraphQLRequest;