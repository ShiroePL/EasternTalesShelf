class QueueManager {
    constructor() {
        // Only initialize if user is logged in
        if (typeof isLoggedIn === 'undefined' || !isLoggedIn) {
            console.log('QueueManager not initialized - user not logged in');
            return;
        }

        this.isVisible = false;
        this.updateInterval = null;
        this.isConnected = false;
        this.connectionAttempts = 0;
        this.maxConnectionAttempts = 2;
        this.initializeUI();
        this.setupEventListeners();
        this.setupWebSocket();
        this.checkConnectionStatus();
        this.updateButtonStates();

        // Add automatic connection attempt on initialization
        this.initializeWebhookConnection();
    }

    setupWebSocket() {
        // Only setup WebSocket for logged-in users
        if (!isLoggedIn) {
            console.log('WebSocket not initialized - user not logged in');
            return;
        }

        try {
            if (typeof io !== 'undefined') {
                this.socket = io();
                this.socket.on('connect', () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.updateConnectionUI();
                });
                this.socket.on('disconnect', () => {
                    console.log('WebSocket disconnected');
                    this.isConnected = false;
                    this.updateConnectionUI();
                });
                this.socket.on('queue_update', (data) => {
                    console.log('Queue update received:', data);
                    if (this.isVisible) {
                        this.updateStatus();
                    }
                });
                this.socket.on('connect_error', (error) => {
                    console.warn('WebSocket connection error:', error);
                    this.isConnected = false;
                    this.updateConnectionUI();
                });
            } else {
                console.warn('Socket.IO not loaded, falling back to polling updates');
                this.isConnected = false;
                this.updateConnectionUI();
            }
        } catch (error) {
            console.warn('Error setting up WebSocket:', error);
            this.isConnected = false;
            this.updateConnectionUI();
        }
    }

    initializeUI() {
        // Only create UI if user is logged in
        if (typeof isLoggedIn === 'undefined' || !isLoggedIn) {
            return;
        }

        const queueManagerHTML = `
            <button class="queue-toggle" id="queueToggle">
                <i class="fas fa-tasks"></i>
            </button>
            <div class="queue-manager" id="queueManager">
                <div class="queue-header">
                    <h5 class="m-0">Scraper Status</h5>
                    <div>
                        <button class="btn btn-sm btn-outline-light" id="toggleConnection">
                            <i class="fas fa-plug"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-light" id="refreshQueue">
                            <i class="fas fa-sync-alt"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-light" id="startScraper" disabled>
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-light" id="stopScraper" disabled>
                            <i class="fas fa-stop"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-light ms-2" id="minimizeQueue">
                            <i class="fas fa-minus"></i>
                        </button>
                    </div>
                </div>
                <div class="queue-content">
                    <div id="connectionStatus" class="mb-2"></div>
                    <div id="scraperStatus" class="mb-3"></div>
                    <div id="currentTask"></div>
                    <div id="queuedTasks"></div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', queueManagerHTML);
    }

    setupEventListeners() {
        document.getElementById('queueToggle').addEventListener('click', () => this.toggleQueue());
        document.getElementById('minimizeQueue').addEventListener('click', () => this.toggleQueue());
        document.getElementById('refreshQueue').addEventListener('click', async () => {
            const button = document.getElementById('refreshQueue');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            
            try {
                await this.updateStatus();
            } finally {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-sync-alt"></i>';
            }
        });
        document.getElementById('startScraper').addEventListener('click', () => this.startScraper());
        document.getElementById('stopScraper').addEventListener('click', () => this.stopScraper());
        document.getElementById('toggleConnection').addEventListener('click', () => this.toggleConnection());
    }

    toggleQueue() {
        this.isVisible = !this.isVisible;
        const queueManager = document.getElementById('queueManager');
        const queueToggle = document.getElementById('queueToggle');
        
        queueManager.style.display = this.isVisible ? 'block' : 'none';
        queueToggle.style.display = this.isVisible ? 'none' : 'block';

        if (this.isVisible) {
            this.updateStatus();
            this.startAutoUpdate();
        } else {
            this.stopAutoUpdate();
        }
    }

    startAutoUpdate() {
        this.updateInterval = setInterval(() => this.updateStatus(), 30000);
    }

    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async checkConnectionStatus() {
        try {
            const response = await fetch('/webhook/status');
            const data = await response.json();
            this.isConnected = data.active;
            this.updateConnectionUI();
        } catch (error) {
            console.error('Error checking connection status:', error);
            this.isConnected = false;
            this.updateConnectionUI();
        }
    }

    updateConnectionUI() {
        const scraperStatus = document.getElementById('scraperStatus');
        if (!scraperStatus) return;

        if (this.isConnected) {
            // Only show errors or important messages, not the regular status
            scraperStatus.style.display = 'none';
        } else {
            scraperStatus.style.display = 'block';
            scraperStatus.innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> Scraper is disconnected
                </div>
            `;
        }

        // Update button states whenever connection status changes
        this.updateButtonStates();
    }

    async toggleConnection() {
        try {
            const button = document.getElementById('toggleConnection');
            const webhookStatus = document.getElementById('webhookStatus');
            
            if (!button) return; // Early return if button doesn't exist
            
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            // Set connecting state only if element exists
            if (webhookStatus && !this.isConnected) {
                webhookStatus.textContent = 'Webhook: Connecting...';
                webhookStatus.classList.remove('connected');
                webhookStatus.dataset.connecting = 'true';
            }

            console.log('Toggling webhook connection...');
            const action = this.isConnected ? 'stop' : 'start';
            console.log('Action:', action);

            const response = await fetch('/webhook/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });

            console.log('Response status:', response.status);
            const data = await response.json();
            console.log('Response data:', data);

            if (data.success) {
                this.isConnected = (data.status === 'connected');
                this.showAlert(
                    'success', 
                    `Successfully ${this.isConnected ? 'connected to' : 'disconnected from'} webhook server`
                );
                this.updateConnectionUI();
                
                // Only update webhook status if element exists
                if (webhookStatus) {
                    if (this.isConnected) {
                        webhookStatus.textContent = 'Scraper: Connected';
                        webhookStatus.classList.add('connected');
                    } else {
                        webhookStatus.textContent = 'Scraper: Disconnected';
                        webhookStatus.classList.remove('connected');
                    }
                    
                    // Remove connecting state
                    webhookStatus.dataset.connecting = 'false';
                }
                
                // Dispatch event for other listeners
                document.dispatchEvent(new CustomEvent('webhookConnectionChanged'));
            } else {
                console.error('Connection failed:', data.message);
                this.showAlert('danger', data.message || 'Failed to toggle connection');
                
                // Reset webhook status on failure if element exists
                if (webhookStatus) {
                    webhookStatus.textContent = 'Scraper: Disconnected';
                    webhookStatus.classList.remove('connected');
                    webhookStatus.dataset.connecting = 'false';
                }
            }
        } catch (error) {
            console.error('Error toggling connection:', error);
            this.showAlert('danger', 'Failed to toggle connection');
            
            // Reset webhook status on error if element exists
            const webhookStatus = document.getElementById('webhookStatus');
            if (webhookStatus) {
                webhookStatus.textContent = 'Scraper: Disconnected';
                webhookStatus.classList.remove('connected');
                webhookStatus.dataset.connecting = 'false';
            }
        } finally {
            const button = document.getElementById('toggleConnection');
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="fas fa-plug"></i>';
            }
        }
    }

    async startScraper() {
        if (!this.isConnected) {
            this.showAlert('warning', 'Please connect to webhook server first');
            return;
        }
        
        try {
            const button = document.getElementById('startScraper');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            console.log('Sending start scraper request...');
            const response = await fetch('/webhook/start_scraper', { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            console.log('Response received:', response.status);
            const data = await response.json();
            console.log('Response data:', data);
            
            if (response.ok && data.status === 'success') {
                console.log('Scraper started successfully');
                this.showAlert('success', data.message || 'Scraper started successfully');
                // Trigger an immediate status update
                this.updateStatus();
            } else {
                console.error('Failed to start scraper:', data);
                this.showAlert('danger', data.message || 'Failed to start scraper');
            }
        } catch (error) {
            console.error('Error starting scraper:', error);
            this.showAlert('danger', 'Failed to connect to server');
        } finally {
            const button = document.getElementById('startScraper');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-play"></i>';
        }
    }

    async stopScraper() {
        if (!this.isConnected) {
            this.showAlert('warning', 'Please connect to webhook server first');
            return;
        }
        
        try {
            const button = document.getElementById('stopScraper');
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

            const response = await fetch('/webhook/stop_scraper', { method: 'POST' });
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('Scraper stopped:', data);
                this.showAlert('success', 'Scraper stopped successfully');
            } else {
                console.error('Failed to stop scraper:', data);
                this.showAlert('danger', data.message || 'Failed to stop scraper');
            }
        } catch (error) {
            console.error('Failed to stop scraper:', error);
            this.showAlert('danger', 'Failed to stop scraper');
        } finally {
            const button = document.getElementById('stopScraper');
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-stop"></i>';
        }
    }

    async updateStatus() {
        try {
            // First check if user is admin before making the request
            const isAdmin = await window.isUserAdmin();
            if (!isAdmin) {
                // Skip queue status request for non-admin users
                return;
            }
            
            // If we're not connected, try to reconnect first
            if (!this.isConnected) {
                try {
                    await this.toggleConnection();
                } catch (error) {
                    console.error('Failed to reconnect:', error);
                }
            }

            // Get queue status (only for admin users)
            const queueResponse = await fetch('/api/queue/status');
            const queueData = await queueResponse.json();

            // Update UI with queue data
            this.updateUI(null, queueData);
        } catch (error) {
            console.error('Failed to update status:', error);
            // Don't show alerts for background operations
        }
    }

    updateUI(statusData, queueData) {
        const statusEl = document.getElementById('scraperStatus');
        const currentTaskEl = document.getElementById('currentTask');
        const queuedTasksEl = document.getElementById('queuedTasks');

        // Helper function to get proper title from grid items
        const getProperTitle = (anilistId) => {
            if (!anilistId) return null;
            const gridItem = document.querySelector(`.grid-item[data-anilist-id="${anilistId}"]`);
            return gridItem ? gridItem.getAttribute('data-title') : null;
        };

        // Only update scraper status if we have status data
        if (statusData) {
            const existingAlert = statusEl.querySelector('.alert-dismissible');
            statusEl.innerHTML = `
                ${existingAlert ? existingAlert.outerHTML : ''}
                <div class="alert ${statusData.active ? 'alert-success' : 'alert-warning'}">
                    Scraper is ${statusData.active ? 'active' : 'inactive'}
                    ${statusData.uptime ? `<br><small>Uptime: ${this.formatUptime(statusData.uptime)}</small>` : ''}
                </div>
            `;
        }

        // Update current task
        if (queueData.current_task) {
            const properTitle = getProperTitle(queueData.current_task.anilist_id) || queueData.current_task.title;
            const progress = queueData.current_task.total_chapters > 0 
                ? (queueData.current_task.current_chapter / queueData.current_task.total_chapters) * 100 
                : 0;
            
            currentTaskEl.innerHTML = `
                <div class="current-task">
                    <div class="task-header">
                        <h6>Currently Scraping: ${properTitle}</h6>
                        <div class="task-controls">
                            <button class="btn btn-sm btn-outline-warning" onclick="window.queueManager.pauseTask('${queueData.current_task.title}')">
                                <i class="fas fa-pause"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="window.queueManager.removeTask('${queueData.current_task.title}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="task-progress">
                        <div class="progress-bar" style="width: ${progress}%"></div>
                    </div>
                    <small>
                        Chapter ${queueData.current_task.current_chapter}/${queueData.current_task.total_chapters}
                        ${queueData.current_task.error_message ? `<br><span class="text-danger">${queueData.current_task.error_message}</span>` : ''}
                    </small>
                </div>
            `;
        } else {
            currentTaskEl.innerHTML = '<p class="text-secondary">No active scraping task</p>';
        }

        // Update queued tasks
        if (queueData && queueData.queued_tasks) {
            queuedTasksEl.innerHTML = `
                <h6 class="mb-3">Queue (${queueData.queued_tasks.length})</h6>
                <ul class="list-unstyled">
                    ${queueData.queued_tasks.map(task => {
                        // Get status badge class
                        let statusBadgeClass = '';
                        switch(task.status) {
                            case 'pending':
                                statusBadgeClass = 'bg-warning';
                                break;
                            case 'downloading':
                                statusBadgeClass = 'bg-info';
                                break;
                            case 'completed':
                                statusBadgeClass = 'bg-success';
                                break;
                            case 'error':
                                statusBadgeClass = 'bg-danger';
                                break;
                            case 'paused':
                                statusBadgeClass = 'bg-warning text-dark';
                                break;
                            case 'queued':
                                statusBadgeClass = 'bg-primary';
                                break;
                            case 'stopped':
                                statusBadgeClass = 'bg-secondary';
                                break;
                            default:
                                statusBadgeClass = 'bg-secondary';
                        }

                        return `
                            <li class="mb-3">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <strong>${task.title}</strong>
                                    </div>
                                    <div class="task-controls">
                                        ${task.status === 'stopped' ? `
                                            <button class="btn btn-sm btn-outline-success" onclick="window.queueManager.resumeTask('${task.title}')">
                                                <i class="fas fa-play"></i>
                                            </button>
                                        ` : `
                                            <button class="btn btn-sm btn-outline-warning" onclick="window.queueManager.pauseTask('${task.title}')">
                                                <i class="fas fa-pause"></i>
                                            </button>
                                        `}
                                        <button class="btn btn-sm btn-outline-primary" onclick="window.queueManager.forcePriority('${task.title}')">
                                            <i class="fas fa-angle-double-up"></i>
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger" onclick="window.queueManager.removeTask('${task.title}')">
                                            <i class="fas fa-times"></i>
                                        </button>
                                    </div>
                                </div>
                                <div>
                                    <small class="text-secondary">
                                        Progress: ${task.current_chapter}/${task.total_chapters || '?'} chapters
                                        <br>
                                        Added: ${new Date(task.created_at).toLocaleString()}
                                        <span class="badge ${statusBadgeClass}">${task.status}</span>
                                    </small>
                                </div>
                            </li>
                        `;
                    }).join('')}
                </ul>
            `;
        }
    }

    formatUptime(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours}h ${minutes}m ${secs}s`;
    }

    async removeFromQueue(title) {
        try {
            await fetch(`/api/queue/${encodeURIComponent(title)}`, {
                method: 'DELETE'
            });
            this.updateStatus();
        } catch (error) {
            console.error('Failed to remove task from queue:', error);
        }
    }

    showAlert(type, message) {
        const statusEl = document.getElementById('scraperStatus');
        statusEl.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alert = statusEl.querySelector('.alert');
            if (alert) {
                alert.remove();
            }
        }, 5000);
    }

    // Add new methods for task control
    async pauseTask(title) {
        try {
            const response = await fetch('/api/queue/pause', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: title })
            });
            if (response.ok) {
                this.updateStatus();
            }
        } catch (error) {
            console.error('Failed to pause task:', error);
            this.showAlert('danger', 'Failed to pause task');
        }
    }

    async resumeTask(title) {
        try {
            const response = await fetch('/api/queue/resume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: title })
            });
            if (response.ok) {
                this.updateStatus();
            }
        } catch (error) {
            console.error('Failed to resume task:', error);
            this.showAlert('danger', 'Failed to resume task');
        }
    }

    async removeTask(title) {
        try {
            const response = await fetch('/api/queue/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: title })
            });
            if (response.ok) {
                this.updateStatus();
            }
        } catch (error) {
            console.error('Failed to remove task:', error);
            this.showAlert('danger', 'Failed to remove task');
        }
    }

    async forcePriority(title) {
        try {
            const response = await fetch('/api/queue/force_priority', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title: title })
            });
            if (response.ok) {
                this.updateStatus();
            }
        } catch (error) {
            console.error('Failed to force priority:', error);
            this.showAlert('danger', 'Failed to change priority');
        }
    }

    updateButtonStates() {
        const startButton = document.getElementById('startScraper');
        const stopButton = document.getElementById('stopScraper');
        
        if (startButton && stopButton) {
            startButton.disabled = !this.isConnected;
            stopButton.disabled = !this.isConnected;
        }
    }

    async initializeWebhookConnection() {
        if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
            try {
                const response = await fetch('/webhook/toggle', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ action: 'start' })
                });
                
                const data = await response.json();
                if (data.success) {
                    console.log('Webhook connection initialized successfully');
                    this.isConnected = true;
                    this.updateConnectionUI();
                } else {
                    console.warn('Failed to initialize webhook connection:', data.message);
                }
            } catch (error) {
                console.error('Error initializing webhook connection:', error);
            }
        }
    }
}

// Initialize queue manager when document is ready, but only if logged in
document.addEventListener('DOMContentLoaded', () => {
    if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
        // Check if user is admin before initializing
        if (window.isUserAdmin) {
            window.isUserAdmin().then(isAdmin => {
                if (isAdmin) {
                    // User is admin, initialize queue manager
                    window.queueManager = new QueueManager();
                } else {
                    // Hide the queue toggle button if it exists
                    const queueToggle = document.getElementById('queueToggle');
                    if (queueToggle) {
                        queueToggle.style.display = 'none';
                    }
                    
                    // If user tries to access queue functionality directly, show admin popup
                    window.queueManager = {
                        toggleQueue: () => window.showAdminRequiredPopup(),
                        pauseTask: () => window.showAdminRequiredPopup(),
                        resumeTask: () => window.showAdminRequiredPopup(),
                        removeTask: () => window.showAdminRequiredPopup(),
                        forcePriority: () => window.showAdminRequiredPopup(),
                        startScraper: () => window.showAdminRequiredPopup(),
                        stopScraper: () => window.showAdminRequiredPopup(),
                        toggleConnection: () => window.showAdminRequiredPopup()
                    };
                }
            }).catch(error => {
                console.error('Error checking admin status:', error);
            });
        } else {
            console.warn('Admin check function not available yet. QueueManager initialization delayed.');
            
            // Try again after a delay to allow admin-access-handler.js to load
            setTimeout(() => {
                if (window.isUserAdmin) {
                    window.isUserAdmin().then(isAdmin => {
                        if (isAdmin) {
                            window.queueManager = new QueueManager();
                        }
                    });
                }
            }, 1000);
        }
    }
}); 