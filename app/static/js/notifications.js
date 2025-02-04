let notificationsVisible = false;

function toggleNotifications() {
    const panel = document.querySelector('.notifications-panel');
    notificationsVisible = !notificationsVisible;
    panel.style.display = notificationsVisible ? 'block' : 'none';
    
    if (notificationsVisible) {
        fetchNotifications();
    }
}

async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const notifications = await response.json();
        displayNotifications(notifications);
    } catch (error) {
        console.error('Error fetching notifications:', error);
    }
}

function displayNotifications(notifications) {
    const container = document.querySelector('.notifications-content');
    container.innerHTML = '';

    if (notifications.length === 0) {
        container.innerHTML = '<div class="p-3 text-center text-muted">No new notifications</div>';
        return;
    }

    notifications.forEach(notification => {
        const notificationEl = document.createElement('div');
        notificationEl.className = `notification-item notification-${notification.type} importance-${notification.importance}`;
        notificationEl.innerHTML = `
            <div class="notification-title">${notification.title}</div>
            <div class="notification-message">${notification.message}</div>
            <div class="notification-time text-muted small">${formatDate(notification.created_at)}</div>
        `;
        notificationEl.onclick = () => {
            markAsRead(notification.id);
            if (notification.url) {
                window.open(notification.url, '_blank');
            }
        };
        container.appendChild(notificationEl);
    });
}

async function markAsRead(notificationId) {
    try {
        await fetch(`/api/notifications/${notificationId}/read`, {
            method: 'POST'
        });
        fetchNotifications(); // Refresh the list
    } catch (error) {
        console.error('Error marking notification as read:', error);
    }
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff/3600000)}h ago`;
    return `${Math.floor(diff/86400000)}d ago`;
}

// Check for new notifications every minute
setInterval(fetchNotifications, 60000); 