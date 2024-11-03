// New variables for MangaUpdates information
let mangaupdates_status = null;
let mangaupdates_licensed = null;
let mangaupdates_completed = null;
let mangaupdates_last_updated = null; 
let currentActiveAnilistId = null;

// for addBatoLinkButton 
let currentAnilistId = null; // This will store the currently focused entry's AniList ID
let currentSeriesName = null; // This will store the currently focused entry's series name


// Initialize a variable to keep track of the current status filter
let currentReleasingStatusFilter = null;


// Default to 'ALL' on page load
let currentFilterType = null;


// ----------------- viariables for timeouts for animating right menu ---------------------
// Global variables for timeout and animation tracking
let globalTimeout;
let isAnimating = false;

// Global variables for animation timeouts
let timeouts = {
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


let mangaUpdatesHTML = '';