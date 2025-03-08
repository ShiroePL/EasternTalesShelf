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
        
        // Add new function call to hide buttons without Bato URLs
        this.hideButtonsWithoutBatoUrls();
    }

    async initializeDownloadStatuses() {
        try {
            // First get the queue status to get current progress for tasks
            const queueResponse = await fetch('/api/queue/status');
            const queueData = await queueResponse.json();
            
            // Create a map of anilist_id to progress info
            const progressMap = new Map();
            
            // Add current task if exists
            if (queueData.current_task && queueData.current_task.anilist_id) {
                progressMap.set(queueData.current_task.anilist_id, {
                    current_chapter: queueData.current_task.current_chapter,
                    total_chapters: queueData.current_task.total_chapters
                });
            }
            
            // Add queued tasks
            queueData.queued_tasks.forEach(task => {
                if (task.anilist_id) {
                    progressMap.set(task.anilist_id, {
                        current_chapter: task.current_chapter,
                        total_chapters: task.total_chapters
                    });
                }
            });

            // Now get download statuses and update with progress info
            const response = await fetch('/api/download/status');
            const statuses = await response.json();
            
            statuses.forEach(status => {
                const progress = progressMap.get(status.anilist_id);
                this.updateDownloadButton(
                    status.anilist_id, 
                    status.status,
                    progress || { current_chapter: 0, total_chapters: 0 }
                );
            });
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
        
        // Add event listener for DOM changes to handle dynamically added content
        const observer = new MutationObserver((mutations) => {
            this.hideButtonsWithoutBatoUrls();
        });
        
        // Start observing the document with the configured parameters
        observer.observe(document.body, { childList: true, subtree: true });
    }

    updateAllDownloadButtons(statuses) {
        statuses.forEach(status => {
            this.updateDownloadButton(status.anilist_id, status.status, {
                current_chapter: status.current_chapter || 0,
                total_chapters: status.total_chapters || 0
            });
        });
    }

    updateDownloadButton(anilistId, status, progress = null) {
        const button = document.querySelector(`.download-status-btn[data-anilist-id="${anilistId}"]`);
        if (button) {
            const currentStatus = (status || 'not_downloaded').toLowerCase();
            button.setAttribute('data-status', currentStatus);
            
            // Set progress to 100% for completed status
            if (currentStatus === 'completed') {
                button.style.setProperty('--progress', 1); // Set to 100% progress
            } else if (progress) {
                const { current_chapter, total_chapters } = progress;
                const progressValue = total_chapters > 0 ? current_chapter / total_chapters : 0;
                button.style.setProperty('--progress', progressValue);
                
                // Update tooltip to include progress
                const progressText = total_chapters > 0 ? 
                    ` (${current_chapter}/${total_chapters})` : '';
                
                const tooltipTexts = {
                    'not_downloaded': `Click to Download${progressText}`,
                    'pending': `Queued for Download${progressText}`,
                    'downloading': `Downloading...${progressText}`,
                    'completed': `Download Complete${progressText}`,
                    'error': `Download Failed${progressText}`,
                    'stopped': `Download Paused${progressText}`,
                    'queued': `In Queue${progressText}`
                };
                button.setAttribute('data-tooltip', tooltipTexts[currentStatus] || 'Unknown Status');
            } else {
                button.style.setProperty('--progress', 0);
                // Set tooltip text
                const tooltipTexts = {
                    'not_downloaded': 'Click to Download',
                    'pending': 'Queued for Download',
                    'downloading': 'Downloading...',
                    'completed': 'Download Complete',
                    'error': 'Download Failed',
                    'stopped': 'Download Paused',
                    'queued': 'In Queue'
                };
                button.setAttribute('data-tooltip', tooltipTexts[currentStatus] || 'Unknown Status');
            }
            
            // Update icon
            const icon = button.querySelector('i');
            switch(currentStatus) {
                case 'downloading':
                    icon.className = 'fas fa-circle-notch fa-spin';  // Spinning circle
                    break;
                case 'pending':
                    icon.className = 'fas fa-clock';  // Clock
                    break;
                case 'queued':
                    icon.className = 'fas fa-list';  // List
                    break;
                case 'completed':
                    icon.className = 'fas fa-star';  // Changed from check-circle to star
                    button.classList.add('completed-download'); // Add class for additional styling
                    break;
                case 'error':
                    icon.className = 'fas fa-times-circle';  // X circle
                    break;
                case 'stopped':
                    icon.className = 'fas fa-pause-circle';  // Pause circle
                    break;
                case 'not_downloaded':
                    icon.className = 'fas fa-arrow-circle-down';  // Download arrow circle
                    break;
                default:
                    icon.className = 'fas fa-arrow-circle-down';
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
                
                // Refresh the queue manager
                if (window.queueManager) {
                    await window.queueManager.updateStatus();
                }
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

    // Add new method to hide buttons without Bato URLs
    hideButtonsWithoutBatoUrls() {
        const downloadButtons = document.querySelectorAll('.download-status-btn');
        downloadButtons.forEach(button => {
            const batoUrl = button.dataset.batoUrl;
            if (!batoUrl) {
                button.style.display = 'none';
            } else {
                button.style.display = 'flex'; // or 'block' or whatever the default is
            }
        });
    }

    showError(message) {
        // Implement error display logic
        console.error(message);
        // You could create a toast notification or use existing alert system
        alert(message); // Add a basic alert for better visibility
    }
}

// Initialize downloader only if user is logged in
document.addEventListener('DOMContentLoaded', () => {
    if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
        window.mangaDownloader = new MangaDownloader();
    }
}); 