class MangaDownloader {
    constructor() {
        // Only initialize if user is logged in
        if (typeof isLoggedIn === 'undefined' || !isLoggedIn) {
            console.log('MangaDownloader not initialized - user not logged in');
            return;
        }

        // Check if user is admin before initialization
        this.checkAdminAndInitialize();
    }

    async checkAdminAndInitialize() {
        try {
            const isAdmin = await window.isUserAdmin();
            if (!isAdmin) {
                console.log('MangaDownloader not initialized - user is not admin');
                return;
            }
            
            // Only initialize for admin users
            this.setupEventListeners();
            this.setupWebSocketListeners();
            
            // Listen for the manga grid loaded event
            document.addEventListener('mangaGridLoaded', (event) => {
                console.log('Manga grid loaded event received, initializing download statuses');
                
                // First verify download buttons exist in the DOM
                const downloadButtons = document.querySelectorAll('.download-status-btn');
                console.log(`Found ${downloadButtons.length} download buttons on grid loaded event`);
                
                // If no buttons found, try to add them now
                if (downloadButtons.length === 0) {
                    this.ensureDownloadButtonsExist();
                } else {
                    // Wait a small amount of time to ensure all DOM elements are fully rendered
                    setTimeout(() => {
                        this.initializeDownloadStatuses();
                        this.hideButtonsWithoutBatoUrls();
                    }, 200);
                }
            });
            
            // Also initialize on page load as a fallback
            if (document.readyState === 'complete') {
                setTimeout(() => {
                    this.ensureDownloadButtonsExist();
                    this.initializeDownloadStatuses();
                    this.hideButtonsWithoutBatoUrls();
                }, 1000);
            } else {
                window.addEventListener('load', () => {
                    setTimeout(() => {
                        this.ensureDownloadButtonsExist();
                        this.initializeDownloadStatuses();
                        this.hideButtonsWithoutBatoUrls();
                    }, 1000);
                });
            }
        } catch (error) {
            console.error('Error checking admin status:', error);
        }
    }
    
    // New method to ensure download buttons exist
    ensureDownloadButtonsExist() {
        // Check if buttons already exist
        const existingButtons = document.querySelectorAll('.download-status-btn');
        if (existingButtons.length > 0) {
            console.log(`${existingButtons.length} download buttons already exist, no need to add them`);
            return;
        }
        
        // Find grid items without download buttons
        const gridItems = document.querySelectorAll('.grid-item');
        console.log(`Found ${gridItems.length} grid items, checking for missing buttons`);
        
        let buttonsAdded = 0;
        
        gridItems.forEach(gridItem => {
            const anilistId = gridItem.getAttribute('data-anilist-id');
            const title = gridItem.getAttribute('data-title');
            const batoLink = gridItem.getAttribute('data-bato-link');
            
            // Check if this grid item already has a download button
            if (!gridItem.querySelector('.manga-controls')) {
                // Create controls div
                const controlsDiv = document.createElement('div');
                controlsDiv.className = 'manga-controls';
                
                // Create download button
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'download-status-btn';
                downloadBtn.setAttribute('data-status', 'not_downloaded');
                downloadBtn.setAttribute('data-anilist-id', anilistId);
                downloadBtn.setAttribute('data-title', title);
                downloadBtn.setAttribute('data-bato-link', batoLink || '');
                
                // Add icon
                const icon = document.createElement('i');
                icon.className = 'fas fa-arrow-circle-down';
                downloadBtn.appendChild(icon);
                
                // Add to controls div and then to grid item
                controlsDiv.appendChild(downloadBtn);
                gridItem.appendChild(controlsDiv);
                
                buttonsAdded++;
            }
        });
        
        console.log(`Added ${buttonsAdded} missing download buttons`);
        
        // If we've added buttons, initialize their statuses
        if (buttonsAdded > 0) {
            setTimeout(() => this.initializeDownloadStatuses(), 100);
        }
    }

    async initializeDownloadStatuses() {
        try {
            // First check if user is admin before making the request
            const isAdmin = await window.isUserAdmin();
            
            // Get queue status (only attempt for admin users)
            let progressMap = new Map();
            if (isAdmin) {
                // Only make this request if the user is an admin
                const queueResponse = await fetch('/api/queue/status');
                const queueData = await queueResponse.json();
                
                // Create a map of anilist_id to progress info
                progressMap = new Map();
                
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
            }

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
        // First try to find the button
        let button = document.querySelector(`.download-status-btn[data-anilist-id="${anilistId}"]`);
        
        // If button doesn't exist but grid item does, try to add it
        if (!button) {
            const gridItem = document.querySelector(`.grid-item[data-anilist-id="${anilistId}"]`);
            
            if (gridItem && !gridItem.querySelector('.manga-controls')) {
                console.log(`Adding missing download button for ${anilistId}`);
                
                // Create the button on the fly
                const controlsDiv = document.createElement('div');
                controlsDiv.className = 'manga-controls';
                
                const title = gridItem.getAttribute('data-title') || 'Unknown';
                const batoLink = gridItem.getAttribute('data-bato-link') || '';
                
                const downloadBtn = document.createElement('button');
                downloadBtn.className = 'download-status-btn';
                downloadBtn.setAttribute('data-status', 'not_downloaded');
                downloadBtn.setAttribute('data-anilist-id', anilistId);
                downloadBtn.setAttribute('data-title', title);
                downloadBtn.setAttribute('data-bato-link', batoLink);
                
                const icon = document.createElement('i');
                icon.className = 'fas fa-arrow-circle-down';
                downloadBtn.appendChild(icon);
                
                controlsDiv.appendChild(downloadBtn);
                gridItem.appendChild(controlsDiv);
                
                // Now the button should exist
                button = downloadBtn;
            }
        }
        
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
            // Enhanced debug logging
            //console.warn(`Download button not found for anilist_id: ${anilistId} and couldn't be created`);
            
            // Log how many buttons exist in the DOM
            //const allButtons = document.querySelectorAll('.download-status-btn');
            //console.log(`Total download buttons in DOM: ${allButtons.length}`);
            
            // Check if the grid item exists but not the button
            const gridItem = document.querySelector(`.grid-item[data-anilist-id="${anilistId}"]`);
            if (gridItem) {
                //console.log(`Grid item exists for ${anilistId} but button could not be created`);
                // This error means something is preventing us from adding the button
                // Possibly missing data attributes or a JS error
            } else {
                //console.log(`No grid item found for ${anilistId} - item might not be visible yet`);
                // Queue this item for retry later
                setTimeout(() => this.updateDownloadButton(anilistId, status, progress), 1000);
            }
        }
    }

    async toggleDownload(button) {
        const anilistId = button.dataset.anilistId;
        const title = button.dataset.title;
        const batoUrl = button.dataset.batoUrl || button.dataset.batoLink || button.getAttribute('data-bato-url') || button.getAttribute('data-bato-link');
        
        if (!batoUrl) {
            console.error(`No Bato.to link available for manga: ${title} (${anilistId})`);
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
            const batoUrl = button.dataset.batoUrl || button.dataset.batoLink || 
                            button.getAttribute('data-bato-url') || button.getAttribute('data-bato-link');
            
            if (!batoUrl) {
               // console.log(`Hiding download button for anilist_id: ${button.dataset.anilistId} - no Bato URL`);
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
        // Create a global instance immediately, but only for admin users
        if (typeof window.isUserAdmin === 'function') {
            window.isUserAdmin().then(isAdmin => {
                if (isAdmin) {
                    console.log('Creating MangaDownloader instance (admin user confirmed)');
                    window.mangaDownloader = new MangaDownloader();
                } else {
                    console.log('User is not an admin, not creating MangaDownloader');
                    // Create stub with empty methods for non-admin users
                    window.mangaDownloader = {
                        initializeDownloadStatuses: () => {},
                        updateDownloadButton: () => {},
                        toggleDownload: () => window.showAdminRequiredPopup ? window.showAdminRequiredPopup() : alert('Admin access required'),
                        hideButtonsWithoutBatoUrls: () => {}
                    };
                }
            }).catch(error => {
                console.error('Error checking admin status:', error);
            });
        } else {
            console.log('window.isUserAdmin function not available yet, will retry');
            // Try again after a delay to allow admin-access-handler.js to load
            setTimeout(() => {
                if (typeof window.isUserAdmin === 'function') {
                    window.isUserAdmin().then(isAdmin => {
                        if (isAdmin) {
                            console.log('Creating MangaDownloader instance after delay (admin user confirmed)');
                            window.mangaDownloader = new MangaDownloader();
                        } else {
                            console.log('User is not an admin after delay check');
                        }
                    });
                } else {
                    console.log('window.isUserAdmin still not available after delay');
                    // As a last resort, check DOM attribute
                    const container = document.getElementById('manga-grid-container');
                    if (container && container.dataset.isAdmin === 'true') {
                        console.log('Creating MangaDownloader based on container data attribute');
                        window.mangaDownloader = new MangaDownloader();
                    }
                }
            }, 1000);
        }
    } else {
        console.log('User not logged in, not initializing MangaDownloader');
    }
}); 