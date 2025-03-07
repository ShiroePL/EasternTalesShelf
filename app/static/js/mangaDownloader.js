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
                this.updateDownloadStatus(
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
            const button = e.target.closest('.download-progress-container');
            if (button && !window.downloadProgressCircles) {
                e.preventDefault();
                e.stopPropagation();  // Prevent triggering parent element clicks
                this.toggleDownload(button);
            }
        });
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
        const currentStatus = (status || 'not_downloaded').toLowerCase();
        
        // If we have the new implementation, use it
        if (window.downloadProgressCircles) {
            window.downloadProgressCircles.updateProgressCircle(anilistId, currentStatus, progress);
            return;
        }
        
        // Legacy implementation for backward compatibility
        const button = document.querySelector(`.download-progress-container[data-anilist-id="${anilistId}"]`);
        if (button) {
            button.setAttribute('data-status', currentStatus);
            
            // Calculate and set progress
            if (progress) {
                let progressValue;
                
                // For completed status, always show 100%
                if (currentStatus === 'completed') {
                    progressValue = 1;
                } else {
                    const { current_chapter, total_chapters } = progress;
                    progressValue = total_chapters > 0 ? current_chapter / total_chapters : 0;
                }
                
                button.style.setProperty('--progress', progressValue);
                
                // Update tooltip to include progress
                const progressText = progress.total_chapters > 0 ? 
                    ` (${progress.current_chapter}/${progress.total_chapters})` : '';
                
                const tooltipTexts = {
                    'not_downloaded': `Click to Download${progressText}`,
                    'pending': `Queued for Download${progressText}`,
                    'downloading': `Downloading...${progressText}`,
                    'completed': `Download Complete`,
                    'error': `Download Failed${progressText}`,
                    'stopped': `Download Paused${progressText}`,
                    'queued': `In Queue${progressText}`
                };
                button.setAttribute('data-tooltip', tooltipTexts[currentStatus] || 'Unknown Status');
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