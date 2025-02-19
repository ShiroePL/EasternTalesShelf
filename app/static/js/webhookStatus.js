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

// Function to update webhook status
function updateWebhookStatus() {
    if (!webhookStatus) return;

    fetch('/webhook/status')
        .then(response => response.json())
        .then(data => {
            // Don't update if we're in the process of connecting
            if (webhookStatus.dataset.connecting === 'true') {
                return;
            }

            let statusText = 'Scraper: ';
            
            if (data.active) {
                // If we're in the initial connection phase (within first few seconds)
                const timeSinceConnection = (Date.now() / 1000) - data.connection_time;
                if (timeSinceConnection < 5) {  // Give 5 seconds grace period for first heartbeat
                    // Keep showing Connected without uptime
                    statusText += 'Connected';
                    webhookStatus.classList.add('connected');
                } else {
                    const timeSinceHeartbeat = (Date.now() / 1000) - data.last_heartbeat;
                    if (timeSinceHeartbeat < 45) {
                        // Show uptime only after initial connection period
                        const uptimeMinutes = Math.floor((Date.now() / 1000 - data.connection_time) / 60);
                        statusText += `Connected (${formatUptime(uptimeMinutes)})`;
                        webhookStatus.classList.add('connected');
                    } else {
                        statusText += data.message || 'Connection lost';
                        webhookStatus.classList.remove('connected');
                    }
                }
            } else {
                statusText += 'Disconnected';
                webhookStatus.classList.remove('connected');
            }
            
            webhookStatus.textContent = statusText;
            webhookStatus.title = `Connected since: ${data.connection_time ? new Date(data.connection_time * 1000).toLocaleString() : 'Never'}\nLast heartbeat: ${data.last_heartbeat ? new Date(data.last_heartbeat * 1000).toLocaleString() : 'Never'}`;

            // Also update the QueueManager's connection state if it exists
            if (window.queueManager) {
                window.queueManager.isConnected = data.active;  // Simplified connection check
                window.queueManager.updateConnectionUI();
            }
        })
        .catch(error => {
            console.error('Error checking webhook status:', error);
            webhookStatus.textContent = 'Scraper: Error';
            webhookStatus.classList.remove('connected');
            
            if (window.queueManager) {
                window.queueManager.isConnected = false;
                window.queueManager.updateConnectionUI();
            }
        });
}

// Update status more frequently initially
let updateInterval = 1000; // Start with 1 second
const maxInterval = 30000; // Max 30 seconds

function scheduleNextUpdate() {
    setTimeout(() => {
        updateWebhookStatus();
        // Increase interval gradually
        updateInterval = Math.min(updateInterval * 1.5, maxInterval);
        scheduleNextUpdate();
    }, updateInterval);
}

// Only start status updates for logged-in users
if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
    updateWebhookStatus();
    scheduleNextUpdate();
}

// Listen for webhook connection events
document.addEventListener('webhookConnectionChanged', (event) => {
    updateInterval = 1000; // Reset to quick updates when connection changes
    updateWebhookStatus();
});

// Listen for WebSocket heartbeat events
if (typeof io !== 'undefined') {
    const socket = io();
    socket.on('webhook_heartbeat', (data) => {
        updateWebhookStatus();
    });
} 