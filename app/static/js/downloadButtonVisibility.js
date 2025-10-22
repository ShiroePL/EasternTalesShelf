// Performance optimization: Only show download buttons for visible grid items
// This reduces the number of DOM elements the browser needs to render

let visibilityObserver = null;

function initializeDownloadButtonVisibility() {
    // Clean up existing observer if any
    if (visibilityObserver) {
        visibilityObserver.disconnect();
    }

    // Create intersection observer with a margin to preload items slightly before they're visible
    visibilityObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Item is visible or about to be visible
                entry.target.classList.add('is-visible');
            } else {
                // Item is off-screen
                entry.target.classList.remove('is-visible');
            }
        });
    }, {
        // Start showing buttons 200px before they enter viewport
        rootMargin: '200px',
        // Trigger when at least 1% of the item is visible
        threshold: 0.01
    });

    // Observe all grid items
    const gridItems = document.querySelectorAll('.grid-item');
    gridItems.forEach(item => {
        visibilityObserver.observe(item);
    });

    console.log(`Observing ${gridItems.length} grid items for download button visibility`);
}

// Initialize when manga grid is loaded
document.addEventListener('mangaGridLoaded', () => {
    console.log('Initializing download button visibility optimization');
    initializeDownloadButtonVisibility();
});

// Also initialize on page load as fallback
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(initializeDownloadButtonVisibility, 1000);
    });
} else {
    setTimeout(initializeDownloadButtonVisibility, 1000);
}
