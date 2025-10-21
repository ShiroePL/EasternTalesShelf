document.addEventListener('DOMContentLoaded', function() {
    // Create the Vue app for notifications
    const NotificationsApp = {
        // Change Vue delimiters to avoid conflict with Jinja2
        delimiters: ['${', '}'],
        data() {
            return {
                drawerVisible: false,
                notifications: [],
                showRead: false
            };
        },
        computed: {
            getNotificationsTitle() {
                const count = this.notifications.length;
                return count > 0 ? `Notifications (${count})` : 'Notifications';
            }
        },
        methods: {
            // Toggle drawer visibility
            toggleDrawer() {
                console.log("Toggle drawer called, current state:", this.drawerVisible);
                this.drawerVisible = !this.drawerVisible;
                if (this.drawerVisible) {
                    this.fetchNotifications();
                }
            },
            
            // Close drawer
            handleClose(done) {
                console.log("Closing drawer");
                done();
            },
            
            // Fetch notifications from API
            fetchNotifications() {
                const includeRead = 'true'
                console.log("Fetching notifications, includeRead:", includeRead);
                
                // Fetch both regular notifications and Bato notifications
                Promise.all([
                    fetch(`/api/notifications?include_read=${includeRead}`).then(r => r.json()),
                    fetch(`/api/bato/notifications`).then(r => r.json())
                ])
                .then(([regularData, batoData]) => {
                    console.log("Received regular notifications:", regularData);
                    console.log("Received Bato notifications:", batoData);
                    
                    let allNotifications = [];
                    
                    // Add regular notifications
                    if (regularData.notifications) {
                        allNotifications = allNotifications.concat(regularData.notifications);
                    }
                    
                    // Add Bato notifications with source identifier
                    if (batoData.success && batoData.notifications) {
                        const batoNotifications = batoData.notifications.map(n => ({
                            ...n,
                            source: 'bato',
                            title: n.manga_name,
                            read: n.is_read
                        }));
                        allNotifications = allNotifications.concat(batoNotifications);
                    }
                    
                    // Sort by importance (descending) then created_at (descending)
                    allNotifications.sort((a, b) => {
                        // First sort by importance (higher first)
                        if (b.importance !== a.importance) {
                            return b.importance - a.importance;
                        }
                        // Then sort by created_at (newer first)
                        const dateA = a.created_at ? new Date(a.created_at) : new Date(0);
                        const dateB = b.created_at ? new Date(b.created_at) : new Date(0);
                        return dateB - dateA;
                    });
                    
                    this.notifications = allNotifications;
                    console.log("Updated notifications:", this.notifications.length);
                })
                .catch(error => {
                    console.error('Error fetching notifications:', error);
                });
            },
            
            // Format date for display
            formatDate(dateString) {
                if (!dateString) return '';
                
                const date = new Date(dateString);
                const now = new Date();
                const diff = now - date;
                
                if (diff < 60000) return 'Just now';
                if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
                if (diff < 86400000) return `${Math.floor(diff/3600000)}h ago`;
                if (diff < 604800000) return `${Math.floor(diff/86400000)}d ago`;
                
                return date.toLocaleString();
            },
            
            // Mark a notification as read
            markAsRead(source, id, index) {
                console.log(`Marking as read: ${source} ${id}`);
                
                // Use different endpoint for Bato notifications
                const endpoint = source === 'bato' 
                    ? `/api/bato/notifications/${id}/read`
                    : `/api/notifications/${source}/${id}/read`;
                
                fetch(endpoint, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Instead of removing, mark as read in our local data
                        this.notifications[index].read = true;
                        
                        // Update notification count badge (unread count will decrease)
                        this.updateNotificationCount();
                    }
                })
                .catch(error => console.error('Error marking notification as read:', error));
            },
            
            // Mark all notifications as read
            markAllAsRead() {
                console.log("Marking all as read");
                
                // Mark all regular notifications as read
                const regularPromise = fetch('/api/notifications/read-all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }).then(r => r.json());
                
                // Mark all Bato notifications as read
                const batoPromises = this.notifications
                    .filter(n => n.source === 'bato' && !n.read)
                    .map(n => fetch(`/api/bato/notifications/${n.id}/read`, {
                        method: 'POST'
                    }).then(r => r.json()));
                
                Promise.all([regularPromise, ...batoPromises])
                    .then(() => {
                        // Mark all as read in local data
                        this.notifications.forEach(n => n.read = true);
                        this.updateNotificationCount();
                    })
                    .catch(error => console.error('Error marking all notifications as read:', error));
            },
            
            // Handle notification click
            handleNotificationClick(notification, index) {
                console.log("Notification clicked:", notification.title);
                
                // Handle Bato notifications with chapter_full_url
                if (notification.source === 'bato' && notification.chapter_full_url) {
                    // Open the chapter URL
                    window.open(notification.chapter_full_url, '_blank');
                    
                    // Mark as read
                    if (!notification.read) {
                        this.markAsRead(notification.source, notification.id, index);
                    }
                } else if (notification.url) {
                    window.open(notification.url, '_blank');
                } else if (notification.anilist_id) {
                    // Find the manga element and show details
                    const mangaElement = document.querySelector(`[data-anilist-id="${notification.anilist_id}"]`);
                    if (mangaElement && typeof showDetails === 'function') {
                        showDetails(mangaElement);
                        this.drawerVisible = false;
                    } else {
                        console.error("Either manga element not found or showDetails function not available");
                    }
                }
            },
            
            // Update notification count badge
            updateNotificationCount() {
                // First check if user is admin without triggering a popup
                window.isUserAdmin().then(isAdmin => {
                    if (!isAdmin) {
                        // Skip the request for non-admin users
                        return;
                    }
                    
                    // Fetch counts from both sources
                    Promise.all([
                        fetch('/api/notifications/count').then(r => r.json()),
                        fetch('/api/bato/notifications').then(r => r.json())
                    ])
                    .then(([regularData, batoData]) => {
                        const badge = document.getElementById('notification-count');
                        if (!badge) return;
                        
                        // Calculate total count
                        let totalCount = regularData.count || 0;
                        
                        // Add Bato unread count
                        if (batoData.success && batoData.notifications) {
                            const batoUnreadCount = batoData.notifications.filter(n => !n.is_read).length;
                            totalCount += batoUnreadCount;
                        }
                        
                        if (totalCount > 0) {
                            badge.textContent = totalCount > 99 ? '99+' : totalCount;
                            badge.classList.add('has-notifications');
                        } else {
                            badge.textContent = '';
                            badge.classList.remove('has-notifications');
                        }
                    })
                    .catch(error => {
                        console.error('Error getting notification count:', error);
                        // Don't show error UI for background operations
                    });
                }).catch(() => {/* Silently ignore errors */});
            }
        },
        mounted() {
            console.log("Vue app mounted");
            // Check for notifications on load
            this.updateNotificationCount();
        },
        created() {
            console.log("Vue app created");
            
            // Set up a global reference to the toggle method
            window.toggleNotifications = window.requireAdmin(() => {
                this.toggleDrawer();
            });
            
            // Check if user is admin before setting up notification polling
            window.isUserAdmin().then(isAdmin => {
                if (isAdmin) {
                    // Only set up interval for admin users
                    this.notificationInterval = setInterval(() => {
                        this.updateNotificationCount();
                    }, 60000); // Every minute
                    
                    // Initial update
                    this.updateNotificationCount();
                } else {
                    // For non-admin users, hide the notification badge 
                    const badge = document.getElementById('notification-count');
                    if (badge) {
                        badge.style.display = 'none';
                    }
                }
            });
        },
        beforeUnmount() {
            // Clear the interval when the component is unmounted
            if (this.notificationInterval) {
                clearInterval(this.notificationInterval);
            }
        }
    };

    // Mount the Vue app
    try {
        const app = Vue.createApp(NotificationsApp);
        app.use(ElementPlus);
        app.mount('#notifications-app');
        console.log('Vue notification app successfully mounted');
    } catch (error) {
        console.error('Error mounting Vue notification app:', error);
    }
}); 