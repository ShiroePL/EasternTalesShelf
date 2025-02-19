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
        if (window.socket) {
            window.socket.on('download_status_update', (data) => {
                this.updateDownloadButton(data.anilist_id, data.status);
            });
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
            button.setAttribute('data-status', status);
        }
    }

    async toggleDownload(button) {
        // Get data directly from the button's data attributes instead of parent element
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
                    anilist_id: parseInt(anilistId) // Ensure anilistId is a number
                })
            });

            if (response.ok) {
                button.setAttribute('data-status', 'pending');
                // The actual status update will come through WebSocket
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