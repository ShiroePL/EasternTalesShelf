// New variables for MangaUpdates information
window.mangaupdates_status = null;
window.mangaupdates_licensed = null;
window.mangaupdates_completed = null;
window.mangaupdates_last_updated = null; 
window.currentActiveAnilistId = null;

// for addBatoLinkButton 
window.currentAnilistId = null; // This will store the currently focused entry's AniList ID
window.currentSeriesName = null; // This will store the currently focused entry's series name


// Initialize a variable to keep track of the current status filter
window.currentReleasingStatusFilter = null;


// Default to 'ALL' on page load
window.currentFilterType = null;


// ----------------- viariables for timeouts for animating right menu ---------------------
// Global variables for timeout and animation tracking
window.globalTimeout = null;
window.isAnimating = false;

// Global variables for animation timeouts
window.timeouts = {
    cover: null,
    info: null,
    mangaupdates_info: null,
    link: null,
    description: null,
    readmore: null,
    externalLinks: null,
    genres: null,
    title_placeholder: null,
    shownotes: null,
    notes: null
};

// ----------------- ENDDDD viariables for timeouts for animating right menu ---------------------


window.mangaUpdatesHTML = '';

// Global utility functions

// Open AniList URL in a new tab
function openAniList(url) {
    if (url) {
        window.open(url, '_blank');
    }
}

// Make functions available globally
window.openAniList = openAniList;