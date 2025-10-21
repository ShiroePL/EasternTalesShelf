// this prevents AOS to move down page each reloading.
if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
}

// Initialize AOS globally
document.addEventListener('DOMContentLoaded', function() {
    // Initial basic setup with default options
    AOS.init({
        offset: 120,
        duration: 800,
        easing: 'ease-in-out',
        once: false,
        mirror: true,
        delay: 50
    });
});

// Consolidated load event listener
window.addEventListener('load', function() {
    // Initialize or refresh AOS based on cumulative height logic
    let items = document.querySelectorAll('.grid-item');
    let cumulativeHeight = 0;
    
    items.forEach(function(item) {
        if (item.style.display !== 'none') {
            cumulativeHeight += item.offsetHeight + 10; // Adjust if necessary
        }
    });

    let windowHeight = window.innerHeight;
    if (cumulativeHeight > windowHeight) {
        setTimeout(function(){
            AOS.refresh(); // Just refresh, we already initialized in DOMContentLoaded
        }, 300); // Longer timeout for better reliability
    }

    // Set border color based on data-status
    items.forEach(function(item) {
        let status = item.getAttribute('data-user-status');
        if(status) {
            status = status.toUpperCase();
            let statusClass = 'border-' + status.toLowerCase();
            item.classList.add(statusClass);
        }
    });
});

// Consolidated resize event listener with debounce
let resizeTimer;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
        AOS.refresh();
    }, 150);
});

// Custom event handler for dynamic content update
window.refreshAOS = function() {
    if (typeof AOS !== 'undefined') {
        console.log('Manual AOS refresh triggered');
        AOS.refresh();
    }
};

// Add the 'fade-out' class when the item scrolls out of view (for a slower effect)
document.addEventListener('aos:out', ({ detail }) => {
    detail.classList.add('fade-out'); // Apply the slow fade-out effect
});

// Remove the 'fade-out' class when the item comes into view
document.addEventListener('aos:in', ({ detail }) => {
    detail.classList.remove('fade-out'); // Remove the slow fade-out effect
});
