document.addEventListener('DOMContentLoaded', async function() {
    // First check if user is admin
    if (typeof window.isUserAdmin === 'function') {
        try {
            const isAdmin = await window.isUserAdmin();
            if (!isAdmin) {
                // Hide webhook status element for non-admin users
                const webhookStatus = document.getElementById('webhookStatus');
                if (webhookStatus) {
                    webhookStatus.style.display = 'none';
                }
                // Don't set up any listeners for non-admin users
                return;
            }
        } catch (error) {
            console.error('Error checking admin status:', error);
        }
    }

    // Only proceed with webhook status initialization for admin users
    const webhookStatus = document.getElementById('webhookStatus');
    if (!webhookStatus) return;

    // Set initial state
    webhookStatus.textContent = 'Scraper: Initializing...';
    webhookStatus.classList.remove('connected');

    // Add delay before first connection attempt
    setTimeout(() => {
        // Check initial connection status
        fetch('/webhook/status')
            .then(response => response.json())
            .then(data => {
                console.log('Webhook status response:', data);  // Debug log
                if (data.active) {
                    webhookStatus.textContent = `Scraper: Connected (${formatUptime(Math.floor(data.uptime / 60))})`;
                    webhookStatus.classList.add('connected');
                } else {
                    webhookStatus.textContent = `Scraper: ${data.message || 'Disconnected'}`;
                    webhookStatus.classList.remove('connected');
                    // Try to establish connection if not connected
                    if (window.queueManager) {
                        window.queueManager.initializeWebhookConnection();
                    }
                }
            })
            .catch(error => {
                console.error('Error checking webhook status:', error);
                webhookStatus.textContent = 'Scraper: Connection Error';
                webhookStatus.classList.remove('connected');
            });
    }, 1000);  // Wait 1 second before first check
});

const webhookStatus = document.getElementById('webhookStatus');

// Function to format uptime
function formatUptime(minutes) {
    if (minutes < 60) {
        return `${minutes}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
}

// Move the socket connection inside the admin check
document.addEventListener('DOMContentLoaded', async function() {
    // Skip socket setup for non-admins
    if (typeof window.isUserAdmin === 'function') {
        try {
            const isAdmin = await window.isUserAdmin();
            if (!isAdmin) return;
        } catch (error) {
            console.error('Error checking admin status:', error);
            return;
        }
    }
    
    const webhookStatus = document.getElementById('webhookStatus');
    if (!webhookStatus) return;
    
    // Only start WebSocket listener for logged-in admin users
    if (typeof io !== 'undefined' && isLoggedIn) {
        const socket = io();
        
        // Handle connection states
        socket.on('webhook_status', (data) => {
            if (!webhookStatus) return; // Check again in case element was removed
            
            if (data.status === 'retrying') {
                webhookStatus.dataset.retrying = 'true';
                webhookStatus.textContent = `Scraper: Reconnecting (${data.attempt}/${data.max_attempts})`;
                webhookStatus.classList.remove('connected');
            } else if (data.status === 'failed') {
                webhookStatus.dataset.retrying = 'false';
                webhookStatus.textContent = 'Scraper: Connection lost';
                webhookStatus.classList.remove('connected');
            } else if (data.status === 'connected') {
                webhookStatus.dataset.retrying = 'false';
                webhookStatus.textContent = `Scraper: Connected (${formatUptime(data.uptime)})`;
                webhookStatus.classList.add('connected');
            } else if (data.status === 'disconnected') {
                webhookStatus.dataset.retrying = 'false';
                webhookStatus.textContent = 'Scraper: Disconnected';
                webhookStatus.classList.remove('connected');
            }
            
            // Update QueueManager state if it exists
            if (window.queueManager) {
                window.queueManager.isConnected = (data.status === 'connected');
                window.queueManager.updateConnectionUI();
            }
        });
    }
}); 