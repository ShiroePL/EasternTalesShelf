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
            let statusText = 'Webhook: ';
            
            if (data.active) {
                if (data.last_heartbeat === null) {
                    statusText += 'Connecting...';
                    webhookStatus.classList.remove('connected');
                } else if (data.last_heartbeat === 0) {
                    statusText += 'Waiting for heartbeat...';
                    webhookStatus.classList.remove('connected');
                } else {
                    const timeSinceHeartbeat = (Date.now() / 1000) - data.last_heartbeat;
                    if (timeSinceHeartbeat < 45) {
                        // Calculate uptime from initial connection time, not last heartbeat
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
                window.queueManager.isConnected = data.active && data.last_heartbeat > 0 && 
                    ((Date.now() / 1000) - data.last_heartbeat < 45);
                window.queueManager.updateConnectionUI();
            }
        })
        .catch(error => {
            console.error('Error checking webhook status:', error);
            webhookStatus.textContent = 'Webhook: Error';
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

// Initial status check and start scheduling
updateWebhookStatus();
scheduleNextUpdate();

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