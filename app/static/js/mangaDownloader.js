class MangaDownloader {
    constructor() {
        // Only initialize if user is logged in
        if (typeof isLoggedIn === 'undefined' || !isLoggedIn) {
            console.log('MangaDownloader not initialized - user not logged in');
            return;
        }

        this.initializeDownloadStatuses();
        this.setupWebSocketListeners();
        this.setupEventListeners();
    }

    async initializeDownloadStatuses() {
        try {
            const response = await fetch('/api/download/status');
            const statuses = await response.json();
            this.updateAllDownloadButtons(statuses);
        } catch (error) {
            console.error('Failed to initialize download statuses:', error);
        }
    }

    setupWebSocketListeners() {
        if (typeof io !== 'undefined') {  // Check if Socket.IO is available
            // Use the existing socket if available, or create a new one
            this.socket = window.socket || io();
            
            // Listen for download status updates
            this.socket.on('download_status_update', (data) => {
                console.log('Received download status update:', data);  // Debug log
                if (data.anilist_id && data.status) {
                    this.updateDownloadButton(data.anilist_id, data.status);
                }
            });

            // Listen for queue updates that might affect download status
            this.socket.on('queue_update', (data) => {
                console.log('Received queue update:', data);  // Debug log
                // Refresh all statuses when queue changes
                this.initializeDownloadStatuses();
            });

            // Store socket reference globally if not already exists
            if (!window.socket) {
                window.socket = this.socket;
            }
        } else {
            console.error('Socket.IO not loaded');
        }
    }

    setupEventListeners() {
        // Use event delegation for download buttons
        document.addEventListener('click', (e) => {
            const button = e.target.closest('.download-status-btn');
            if (button) {
                e.preventDefault();
                e.stopPropagation();  // Prevent triggering parent element clicks
                this.toggleDownload(button);
            }
        });
    }

    updateAllDownloadButtons(statuses) {
        statuses.forEach(status => {
            this.updateDownloadButton(status.anilist_id, status.status);
        });
    }

    updateDownloadButton(anilistId, status) {
        const button = document.querySelector(`.download-status-btn[data-anilist-id="${anilistId}"]`);
        if (button) {
            console.log(`Updating button for ${anilistId} to status: ${status}`);  // Debug log
            const currentStatus = status || 'not_downloaded';
            button.setAttribute('data-status', currentStatus);
            
            const icon = button.querySelector('i');
            switch(currentStatus.toLowerCase()) {  // Make case-insensitive
                case 'downloading':
                    icon.className = 'fas fa-spinner fa-spin';
                    break;
                case 'pending':
                    icon.className = 'fas fa-clock';
                    break;
                case 'queued':
                    icon.className = 'fas fa-list';
                    break;
                case 'completed':
                    icon.className = 'fas fa-check';
                    break;
                case 'error':
                    icon.className = 'fas fa-exclamation-triangle';
                    break;
                case 'stopped':
                    icon.className = 'fas fa-stop';
                    break;
                case 'not_downloaded':
                    icon.className = 'fas fa-download';
                    break;
                default:
                    console.log(`Unknown status: ${currentStatus}`);  // Debug log
                    icon.className = 'fas fa-download';
            }
        } else {
            console.log(`Button not found for anilist_id: ${anilistId}`);  // Debug log
        }
    }

    async toggleDownload(button) {
        const anilistId = button.dataset.anilistId;
        const title = button.dataset.title;
        const batoUrl = button.dataset.batoUrl;

        if (!batoUrl) {
            this.showError('No Bato.to link available for this manhwa');
            return;
        }

        const currentStatus = button.getAttribute('data-status');
        if (currentStatus === 'downloading' || currentStatus === 'pending') {
            return; // Prevent multiple clicks while processing
        }

        try {
            const sanitizedTitle = this.sanitizeFolderName(title);
            const response = await fetch('/api/queue/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: sanitizedTitle,
                    bato_url: batoUrl,
                    anilist_id: parseInt(anilistId)
                })
            });

            if (response.ok) {
                // Update the button immediately with the correct pending status
                this.updateDownloadButton(anilistId, 'pending');
            } else {
                throw new Error('Failed to add to queue');
            }
        } catch (error) {
            console.error('Failed to toggle download:', error);
            this.showError('Failed to add to download queue');
        }
    }

    sanitizeFolderName(folderName) {
        let name = folderName.replace(/:/g, '_')
                            .replace(/\(/g, '_')
                            .replace(/\)/g, '_');
        
        name = name.replace(/[^a-zA-Z0-9\-]/g, '_');
        name = name.replace(/_+/g, '_');
        name = name.trim('_');
        
        return name || "unnamed";
    }

    showError(message) {
        // Implement error display logic
        console.error(message);
        // You could create a toast notification or use existing alert system
    }
}

// Initialize downloader only if user is logged in
document.addEventListener('DOMContentLoaded', () => {
    if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
        window.mangaDownloader = new MangaDownloader();
    }
}); 