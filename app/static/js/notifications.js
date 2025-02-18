let notificationsVisible = false;

function toggleNotifications() {
    const panel = document.querySelector('.notifications-panel');
    if (panel.style.display === 'none' || !panel.style.display) {
        fetchNotifications();
        panel.style.display = 'block';
    } else {
        panel.style.display = 'none';
    }
}

function fetchNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(notifications => {
            const panel = document.querySelector('.notifications-panel');
            panel.innerHTML = ''; // Clear existing notifications
            
            if (notifications.length === 0) {
                panel.innerHTML = '<div class="notification-item">No new notifications</div>';
                return;
            }
            
            notifications.forEach(notification => {
                const notificationElement = createNotificationElement(notification);
                panel.appendChild(notificationElement);
            });
        })
        .catch(error => console.error('Error fetching notifications:', error));
}

function createNotificationElement(notification) {
    const div = document.createElement('div');
    div.className = 'notification-item';
    
    // Add source-specific class
    div.classList.add(`notification-${notification.source}`);
    
    // Create notification content
    const content = document.createElement('div');
    content.className = 'notification-content';
    
    // Add title
    const title = document.createElement('div');
    title.className = 'notification-title';
    title.textContent = notification.title;
    content.appendChild(title);
    
    // Add message
    const message = document.createElement('div');
    message.className = 'notification-message';
    message.textContent = notification.message;
    content.appendChild(message);
    
    // Add timestamp
    const timestamp = document.createElement('div');
    timestamp.className = 'notification-timestamp';
    timestamp.textContent = new Date(notification.created_at).toLocaleString();
    content.appendChild(timestamp);
    
    div.appendChild(content);
    
    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'notification-close';
    closeBtn.innerHTML = '×';
    closeBtn.onclick = () => markAsRead(notification.source, notification.id, div);
    div.appendChild(closeBtn);
    
    // Add click handler for the notification content
    if (notification.url) {
        content.style.cursor = 'pointer';
        content.onclick = () => window.open(notification.url, '_blank');
    }
    
    return div;
}

function markAsRead(source, id, element) {
    fetch(`/api/notifications/${source}/${id}/read`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            element.remove();
            // Check if there are no more notifications
            const panel = document.querySelector('.notifications-panel');
            if (!panel.children.length) {
                panel.innerHTML = '<div class="notification-item">No new notifications</div>';
            }
        }
    })
    .catch(error => console.error('Error marking notification as read:', error));
}

function displayNotifications(notifications) {
    const container = document.querySelector('.notifications-content');
    container.innerHTML = '';

    if (notifications.length === 0) {
        container.innerHTML = '<div class="p-3 text-center text-muted">No new notifications</div>';
        return;
    }

    // Group notifications by title and time
    const groupedNotifications = groupNotifications(notifications);
    
    groupedNotifications.forEach(group => {
        const notificationEl = document.createElement('div');
        notificationEl.className = `notification-item notification-${group.notifications[0].type} importance-${group.notifications[0].importance}`;
        
        let content = `
            <div class="notification-title">${group.title}</div>
        `;
        
        if (group.notifications.length === 1) {
            // Single notification
            content += `
                <div class="notification-message">${group.notifications[0].message}</div>
                <div class="notification-footer">
                    <div class="notification-time text-muted small">${formatDate(group.notifications[0].created_at)}</div>
                    <button class="btn-close-notification" onclick="event.stopPropagation(); markGroupAsRead(${JSON.stringify(group.notifications.map(n => n.id))});">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        } else {
            // Multiple notifications
            content += `<div class="notification-messages">`;
            group.notifications.forEach(notification => {
                content += `
                    <div class="notification-message">${notification.message}</div>
                `;
            });
            content += `</div>
                <div class="notification-footer">
                    <div class="notification-time text-muted small">${formatDate(group.notifications[0].created_at)}</div>
                    <button class="btn-close-notification" onclick="event.stopPropagation(); markGroupAsRead(${JSON.stringify(group.notifications.map(n => n.id))});">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }
        
        notificationEl.innerHTML = content;
        notificationEl.onclick = () => {
            // Show manga details in sidebar
            showDetails(document.querySelector(`[data-anilist-id="${group.notifications[0].anilist_id}"]`));
        };
        container.appendChild(notificationEl);
    });
}

function groupNotifications(notifications) {
    const groups = [];
    const timeThreshold = 1000 * 60 * 60; // 1 hour threshold
    
    notifications.forEach(notification => {
        const notificationTime = new Date(notification.created_at).getTime();
        
        // Find existing group for this title within time threshold
        const existingGroup = groups.find(group => {
            const groupTime = new Date(group.notifications[0].created_at).getTime();
            return group.title === notification.title && 
                   Math.abs(notificationTime - groupTime) < timeThreshold;
        });
        
        if (existingGroup) {
            existingGroup.notifications.push(notification);
        } else {
            groups.push({
                title: notification.title,
                notifications: [notification]
            });
        }
    });
    
    // Sort groups by most recent notification
    groups.sort((a, b) => {
        const aTime = new Date(a.notifications[0].created_at).getTime();
        const bTime = new Date(b.notifications[0].created_at).getTime();
        return bTime - aTime;
    });
    
    return groups;
}

async function markGroupAsRead(notificationIds) {
    for (const id of notificationIds) {
        await markAsRead(id);
    }
    fetchNotifications(); // Refresh the list
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