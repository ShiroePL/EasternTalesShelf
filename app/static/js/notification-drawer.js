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
                
                fetch(`/api/notifications?include_read=${includeRead}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! Status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log("Received notifications data:", data);
                        if (data.notifications) {
                            this.notifications = data.notifications;
                            console.log("Updated notifications:", this.notifications.length);
                        } else {
                            console.warn("No notifications found in response");
                        }
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
                fetch(`/api/notifications/${source}/${id}/read`, {
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
                fetch('/api/notifications/read-all', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Clear notifications and update badge
                        this.notifications = [];
                        this.updateNotificationCount();
                    }
                })
                .catch(error => console.error('Error marking all notifications as read:', error));
            },
            
            // Handle notification click
            handleNotificationClick(notification) {
                console.log("Notification clicked:", notification.title);
                if (notification.url) {
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
                    
                    fetch('/api/notifications/count')
                        .then(response => response.json())
                        .then(data => {
                            const badge = document.getElementById('notification-count');
                            if (!badge) return;
                            
                            if (data.count > 0) {
                                badge.textContent = data.count > 99 ? '99+' : data.count;
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