// filters.js - Handles filtering manga grid items

document.addEventListener('DOMContentLoaded', function() {
    window.currentFilterType = 'ALL'; // Default to 'ALL' on page load
    window.currentStatusFilter = ''; // Initialize a variable to keep track of the current status filter
    window.currentReleasingStatusFilter = ''; // Initialize a variable to keep track of the current releasing status filter

    // Export the filterEntries function to make it globally accessible
    window.filterEntries = filterEntries;
    // Export filterByType to make it globally accessible
    window.filterByType = filterByType;

    // Initial filter application
    filterByType(currentFilterType);

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