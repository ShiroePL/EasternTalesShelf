// Notifications.js - completely replaced
// This file now just redirects to the Vue-based notification drawer

// Initialize an empty function that the old code might call
function fetchNotifications() {
    console.log('Old fetchNotifications called - now handled by Vue component');
}

// This function will be overridden by the Vue app
function toggleNotifications() {
    console.log('Notification system loading...');
}

// Placeholder for backward compatibility
function markAsRead(source, id, element) {
    console.log('Using Vue-based notification system instead');
}

// All other functions are now handled by the Vue component

// We still check notification count for the badge
function updateNotificationCount() {
    fetch('/api/notifications/count')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            const badge = document.getElementById('notification-count');
            if (!badge) {
                console.log('Notification badge element not found yet');
                return;
            }
            
            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.classList.add('has-notifications');
            } else {
                badge.textContent = '';
                badge.classList.remove('has-notifications');
            }
        })
        .catch(error => {
            console.log('Error getting notification count:', error);
        });
}

// Call on page load
document.addEventListener('DOMContentLoaded', function() {
    updateNotificationCount();
    setInterval(updateNotificationCount, 60000); // Check every minute
}); 