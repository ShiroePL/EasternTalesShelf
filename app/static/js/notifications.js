// Notifications.js - DEPRECATED
// This functionality is now handled by notification-drawer.js Vue component

// Just expose empty/stub functions for backward compatibility
function fetchNotifications() {
    console.log('Notifications now handled by Vue component');
}

function toggleNotifications() {
    // This will be overridden by the Vue component
    console.log('Notification system loading...');
}

function markAsRead(source, id, element) {
    console.log('Using Vue-based notification system');
}

function updateNotificationCount() {
    // Do nothing - handled by Vue component
}

// No DOM listeners or intervals - these are handled by the Vue component 