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