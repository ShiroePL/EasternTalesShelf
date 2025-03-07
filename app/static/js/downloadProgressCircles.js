/**
 * Download Progress Circles
 * This file handles the initialization and management of download progress circles
 */

class DownloadProgressCircles {
    constructor() {
        if (typeof isLoggedIn === 'undefined' || !isLoggedIn) {
            console.log('DownloadProgressCircles not initialized - user not logged in');
            return;
        }
        
        this.initializeProgressCircles();
        this.setupEventListeners();
    }

    /**
     * Initialize all progress circles on the page
     */
    initializeProgressCircles() {
        // Find all download progress containers
        const progressContainers = document.querySelectorAll('.download-progress-container');
        
        progressContainers.forEach(container => {
            this.createProgressCircle(container);
        });
    }
    
    /**
     * Create a progress circle for each container
     */
    createProgressCircle(container) {
        const status = container.dataset.status;
        let progress = parseFloat(container.dataset.progress || 0);
        
        // Always show completed as 100%
        if (status === 'completed') {
            progress = 1;
        }
        
        const tooltip = this.getTooltipText(status, progress * 100);
        
        // Set the tooltip
        container.setAttribute('data-tooltip', tooltip);
        
        // Set the progress as a CSS variable
        container.style.setProperty('--progress', progress);
        
        // Create progress circle element
        const progressCircle = document.createElement('div');
        progressCircle.className = 'progress-circle';
        container.appendChild(progressCircle);
        
        // Create icon element
        const icon = document.createElement('i');
        icon.className = this.getStatusIcon(status);
        icon.classList.add('progress-icon');
        container.appendChild(icon);
    }
    
    /**
     * Get the appropriate icon class for the status
     */
    getStatusIcon(status) {
        // Map status to Font Awesome icon classes
        const iconMap = {
            'downloading': 'fas fa-circle-notch fa-spin',
            'pending': 'fas fa-clock',
            'queued': 'fas fa-list',
            'completed': 'fas fa-star',  // Star icon for completed
            'error': 'fas fa-times-circle',
            'stopped': 'fas fa-pause-circle',
            'not_downloaded': 'fas fa-arrow-circle-down'
        };
        return iconMap[status] || 'fas fa-arrow-circle-down';
    }
    
    /**
     * Get tooltip text based on status and progress
     */
    getTooltipText(status, progressPercent) {
        // Format the progress percentage
        const progress = Math.round(progressPercent);
        
        // Get proper text for the tooltip
        const tooltipTexts = {
            'not_downloaded': `Click to Download`,
            'pending': `Queued for Download (${progress}%)`,
            'downloading': `Downloading... (${progress}%)`,
            'completed': `Download Complete! 🎉`,  // Added celebration emoji
            'error': `Download Failed`,
            'stopped': `Download Paused (${progress}%)`,
            'queued': `In Queue`
        };
        return tooltipTexts[status] || 'Unknown Status';
    }
    
    /**
     * Update a progress circle with new status and progress
     */
    updateProgressCircle(anilistId, status, progress = {}) {
        const container = document.querySelector(`.download-progress-container[data-anilist-id="${anilistId}"]`);
        
        if (container) {
            // Update status attribute
            container.dataset.status = status;
            
            // Update progress
            let progressValue;
            
            // For completed status, always show 100%
            if (status === 'completed') {
                progressValue = 1;
            } else {
                progressValue = progress.total_chapters > 0 
                    ? (progress.current_chapter / progress.total_chapters)
                    : 0;
            }
            
            container.style.setProperty('--progress', progressValue);
            
            // Update tooltip
            container.setAttribute('data-tooltip', this.getTooltipText(status, progressValue * 100));
            
            // Update icon
            const icon = container.querySelector('.progress-icon');
            if (icon) {
                icon.className = this.getStatusIcon(status) + ' progress-icon';
            }
        }
    }
    
    /**
     * Setup event listeners for the progress circles
     */
    setupEventListeners() {
        // Use event delegation for download buttons
        document.addEventListener('click', (e) => {
            const container = e.target.closest('.download-progress-container');
            if (container) {
                e.preventDefault();
                e.stopPropagation();  // Prevent triggering parent element clicks
                this.toggleDownload(container);
            }
        });
    }
    
    /**
     * Toggle download when clicked
     */
    async toggleDownload(container) {
        const anilistId = container.dataset.anilistId;
        const title = container.dataset.title;
        const batoUrl = container.dataset.batoUrl;

        if (!batoUrl) {
            this.showError('No Bato.to link available for this manhwa');
            return;
        }

        const currentStatus = container.dataset.status;
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
                // Update the status immediately to pending
                this.updateProgressCircle(anilistId, 'pending', { current_chapter: 0, total_chapters: 1 });
                
                // Refresh the queue manager if available
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
    
    /**
     * Sanitize folder name
     */
    sanitizeFolderName(folderName) {
        let name = folderName.replace(/:/g, '_')
                            .replace(/\(/g, '_')
                            .replace(/\)/g, '_');
        
        name = name.replace(/[^a-zA-Z0-9\-]/g, '_');
        name = name.replace(/_+/g, '_');
        name = name.trim('_');
        
        return name || "unnamed";
    }
    
    /**
     * Show error message
     */
    showError(message) {
        console.error(message);
        // You could create a toast notification or use existing alert system
    }
}

// Initialize on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
    if (typeof isLoggedIn !== 'undefined' && isLoggedIn) {
        window.downloadProgressCircles = new DownloadProgressCircles();
    }
}); 