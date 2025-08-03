// filters.js - Handles filtering manga grid items

document.addEventListener('DOMContentLoaded', function() {
    window.currentFilterType = 'ALL'; // Default to 'ALL' on page load
    window.currentStatusFilter = ''; // Initialize a variable to keep track of the current status filter
    window.currentReleasingStatusFilter = ''; // Initialize a variable to keep track of the current releasing status filter
    window.currentSortType = 'default'; // Global variable to track active sort state

    // Export the filterEntries function to make it globally accessible
    window.filterEntries = filterEntries;
    // Export filterByType to make it globally accessible
    window.filterByType = filterByType;
    // Export sorting functions to make them globally accessible
    window.applySorting = applySorting;
    window.updateSortDropdownText = updateSortDropdownText;
    window.updateSortDropdownActiveState = updateSortDropdownActiveState;

    // Initial filter application
    filterByType(currentFilterType);

    // Initialize sorting functionality
    initializeSorting();

    // Listen for mangaGridLoaded event to reapply filters after grid is loaded
    document.addEventListener('mangaGridLoaded', () => {
        filterEntries();
    });
});

/**
 * Filter manga grid entries based on all active filters
 */
function filterEntries() {
    const titleFilter = document.getElementById('titleFilter')?.value.toLowerCase() || '';
    const countryJapan = document.getElementById('countryJapan')?.checked || false;
    const countryKorea = document.getElementById('countryKorea')?.checked || false;
    const isFavorite_checkbox = document.getElementById('isFavorite_checkbox')?.checked || false;
    const isRereaded_checkbox = document.getElementById('isRereaded_checkbox')?.checked || false;

    const items = document.querySelectorAll('.grid-item');
    let visibleCount = 0;

    items.forEach(function(item) {
        const title = (item.getAttribute('data-title') || '').toLowerCase();
        const country = item.getAttribute('data-country') || ''; // This should now contain JP or KR
        const type = item.getAttribute('data-type') || ''; // This may be empty, so default to empty string
        const itemStatus = (item.getAttribute('data-user-status') || '').toLowerCase();
        const itemReleasingStatus = (item.getAttribute('data-release-status') || '').toLowerCase();
        const isFavorite = item.getAttribute('data-is-favourite') === '1';
        const rereadTimes = parseInt(item.getAttribute('data-reread-times') || '0');

        // Match title (text search)
        const matchesTitle = titleFilter === '' || title.includes(titleFilter);
        
        // Proper country filtering for sidebar checkboxes
        const sidebarCountryFilter = (!countryJapan && !countryKorea) || // No country filtering selected
                                     (countryJapan && country === 'JP') || // Japan selected and matches
                                     (countryKorea && country === 'KR');   // Korea selected and matches
        
        // Match favorite filter
        const matchesFavorite = !isFavorite_checkbox || isFavorite;
        
        // Match reread filter
        const matchesRereaded = !isRereaded_checkbox || rereadTimes > 0;
        
        // Match user status (COMPLETED, CURRENT, etc.)
        const matchesStatus = !window.currentStatusFilter || window.currentStatusFilter === '' || 
                              itemStatus === window.currentStatusFilter.toLowerCase();
        
        // Match content type filter (ALL, MANGA, MANHWA, NOVEL) from navbar
        let matchesFilterType = true; // Default to true
        
        if (window.currentFilterType === 'MANGA') {
            // Japanese manga - typically format is MANGA and country is JP
            matchesFilterType = country === 'JP' && (type === 'MANGA' || type === '' || type === null);
        } else if (window.currentFilterType === 'MANHWA') {
            // Korean manhwa - typically format could be MANGA but country is KR
            matchesFilterType = country === 'KR';
        } else if (window.currentFilterType === 'NOVEL') {
            // Japanese light novels - typically format is NOVEL and country is JP
            matchesFilterType = country === 'JP' && (type === 'NOVEL' || type === 'LIGHT_NOVEL');
        }
        // If ALL, matchesFilterType remains true
        
        // Match release status (RELEASING, FINISHED)
        const matchesReleasingStatus = !window.currentReleasingStatusFilter || window.currentReleasingStatusFilter === '' || 
                                      itemReleasingStatus.toUpperCase() === window.currentReleasingStatusFilter;

        // All filters must match for the item to be visible
        if (matchesTitle && sidebarCountryFilter && matchesStatus && matchesFilterType && 
            matchesReleasingStatus && matchesFavorite && matchesRereaded) {
                item.style.display = '';
            visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });

    // Note: No need to reapply sorting since we now use GraphQL-based sorting
    // that loads data pre-sorted from the database

    // Refresh AOS animations after filtering
    if (typeof AOS !== 'undefined') {
        AOS.refresh();
    }
}

/**
 * Filter by content type (ALL, MANGA, MANHWA, NOVEL)
 */
function filterByType(filterType) {
    window.currentFilterType = filterType;
    updateNavigationStyles(filterType);
    filterEntries();
}

/**
 * Update navigation styles to highlight the active filter
 */
function updateNavigationStyles(selectedFilter) {
    // Remove 'active' class from all nav links
    document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
        link.classList.remove('active');
    });

    // Add 'active' class to the selected nav link
    const selectedNavLink = document.querySelector(`.navbar-nav .nav-link[onclick*="${selectedFilter}"]`);
    if (selectedNavLink) {
        selectedNavLink.classList.add('active');
    }
}

/**
 * Initialize sorting functionality - set up event listeners and initial state
 */
function initializeSorting() {
    // Set up event listeners for sort dropdown items
    const sortDropdownItems = document.querySelectorAll('[data-sort]');
    sortDropdownItems.forEach(item => {
        item.addEventListener('click', async function(e) {
            e.preventDefault();
            const sortType = this.getAttribute('data-sort');
            await applySorting(sortType);
        });
    });

    // Initialize with default sort state
    window.currentSortType = 'default';
    
    // Set initial visual state for dropdown
    updateSortDropdownText('default');
}

/**
 * Apply sorting to the manga grid based on the specified sort type
 * @param {string} sortType - The type of sorting to apply ('default', 'score', etc.)
 */
async function applySorting(sortType) {
    // Performance monitoring
    const startTime = performance.now();
    
    // Update the current sort type
    window.currentSortType = sortType;
    
    // Map sort types to GraphQL sort parameters
    let graphQLSortBy;
    switch (sortType) {
        case 'score':
            graphQLSortBy = '-score'; // Descending score
            break;
        case 'default':
        default:
            graphQLSortBy = '-last_updated_on_site'; // Default sort
            break;
    }

    // Import loadMangaGrid function dynamically to avoid circular imports
    const { loadMangaGrid } = await import('./MangaGridLoader.js');
    
    // Reload the grid with the new sort order
    await loadMangaGrid(graphQLSortBy);
    
    // Reapply any active filters after reloading
    filterEntries();

    // Update dropdown text to reflect current sort
    updateSortDropdownText(sortType);
    
    // Log performance metrics for debugging
    const endTime = performance.now();
    const duration = endTime - startTime;
    console.log(`GraphQL sorting by ${sortType} (${graphQLSortBy}) completed in ${duration.toFixed(2)}ms`);
}

// Note: sortByScore function removed - now using GraphQL-based sorting for better performance

/**
 * Update the sort dropdown button text to reflect the current sort type
 * @param {string} sortType - The current sort type
 */
function updateSortDropdownText(sortType) {
    const dropdownButton = document.getElementById('sortDropdown');
    if (!dropdownButton) {
        console.warn('Sort dropdown button not found');
        return;
    }

    let buttonText;
    switch (sortType) {
        case 'score':
            buttonText = '<i class="fas fa-star"></i> Sort by Score';
            break;
        case 'default':
        default:
            buttonText = '<i class="fas fa-clock"></i> Default Order';
            break;
    }

    dropdownButton.innerHTML = buttonText;
    
    // Update visual feedback in dropdown items
    updateSortDropdownActiveState(sortType);
}

/**
 * Update visual feedback to show active sort option in dropdown
 * @param {string} sortType - The current active sort type
 */
function updateSortDropdownActiveState(sortType) {
    // Remove active class from all dropdown items
    const dropdownItems = document.querySelectorAll('[data-sort]');
    dropdownItems.forEach(item => {
        item.classList.remove('active');
        // Remove any existing checkmark icons
        const existingIcon = item.querySelector('.fas.fa-check');
        if (existingIcon) {
            existingIcon.remove();
        }
    });

    // Add active class and checkmark to the current sort option
    const activeItem = document.querySelector(`[data-sort="${sortType}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
        // Add checkmark icon to show it's selected
        const checkIcon = document.createElement('i');
        checkIcon.className = 'fas fa-check ms-auto';
        activeItem.appendChild(checkIcon);
    }
}