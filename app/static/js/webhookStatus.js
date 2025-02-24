document.addEventListener('DOMContentLoaded', function() {
    const webhookStatus = document.getElementById('webhookStatus');
    if (!webhookStatus) return;

    // Set initial state
    webhookStatus.textContent = 'Scraper: Connecting...';
    webhookStatus.classList.remove('connected');

    // Check initial connection status
    fetch('/webhook/status')
        .then(response => response.json())
        .then(data => {
            if (data.active) {
                webhookStatus.textContent = `Scraper: Connected (${formatUptime(Math.floor(data.uptime / 60))})`;
                webhookStatus.classList.add('connected');
            } else {
                webhookStatus.textContent = 'Scraper: Disconnected';
                webhookStatus.classList.remove('connected');
            }
        })
        .catch(error => {
            console.error('Error checking webhook status:', error);
            webhookStatus.textContent = 'Scraper: Error';
            webhookStatus.classList.remove('connected');
        });
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

// Only start WebSocket listener for logged-in users
if (typeof io !== 'undefined' && isLoggedIn) {
    const socket = io();
    
    // Handle connection states
    socket.on('webhook_status', (data) => {
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