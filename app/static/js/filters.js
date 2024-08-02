document.addEventListener('DOMContentLoaded', function() {
    window.currentFilterType = 'ALL'; // Default to 'ALL' on page load
    window.currentStatusFilter = ''; // Initialize a variable to keep track of the current status filter
    window.currentReleasingStatusFilter = ''; // Initialize a variable to keep track of the current releasing status filter

    window.filterEntries = function() {
        const titleFilter = document.getElementById('titleFilter').value.toLowerCase();
        const countryJapan = document.getElementById('countryJapan').checked;
        const countryKorea = document.getElementById('countryKorea').checked;
        const isFavorite_checkbox = document.getElementById('isFavorite_checkbox').checked;
        const isRereaded_checkbox = document.getElementById('isRereaded_checkbox').checked;

        const filterLogic = {
            'NOVEL': (country, type) => country === 'JP' && type === 'NOVEL',
            'MANHWA': (country, type) => country === 'KR' && type === 'MANGA',
            'MANGA': (country, type) => country === 'JP' && type === 'MANGA',
            'ALL': () => true
        };

        const items = document.querySelectorAll('.grid-item');

        items.forEach(function(item) {
            const title = (item.getAttribute('data-title') || '').toLowerCase();
            const country = item.getAttribute('data-country') || '';
            const type = item.getAttribute('data-type') || '';
            const itemStatus = (item.getAttribute('data-user-status') || '').toLowerCase();
            const itemReleasingStatus = (item.getAttribute('data-release-status') || '').toLowerCase();

            const matchesTitle = titleFilter === '' || title.includes(titleFilter);
            const matchesCountry = (!countryJapan && !countryKorea) ||
                                   (countryJapan && country === 'JP') ||
                                   (countryKorea && country === 'KR');
            const matchesFavorite = !isFavorite_checkbox || item.getAttribute('data-is-favourite') === '1';
            const matchesRereaded = !isRereaded_checkbox || item.getAttribute('data-reread-times') > '0';
            const matchesStatus = currentStatusFilter === '' || itemStatus === currentStatusFilter.toLowerCase();
            const matchesFilterType = filterLogic[currentFilterType] ? filterLogic[currentFilterType](country, type) : true;
            const matchesReleasingStatus = currentReleasingStatusFilter === '' || itemReleasingStatus === currentReleasingStatusFilter.toLowerCase();

            if (matchesTitle && matchesCountry && matchesStatus && matchesFilterType && matchesReleasingStatus && matchesFavorite && matchesRereaded) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });

        AOS.refresh();
    }

    // Add event listeners for filter type buttons
    document.querySelectorAll('.filter-type-btn').forEach(button => {
        button.addEventListener('click', function() {
            window.currentFilterType = this.getAttribute('data-filter-type');
            filterEntries();
        });
    });

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
    
    // Function to filter by type when a navbar item is clicked
    function filterByType(filterType) {
        currentFilterType = filterType;
        updateNavigationStyles(filterType);
        filterEntries();
    }
    
    // Make filterByType available globally
    window.filterByType = filterByType;

    // Initial filter application
    filterByType(currentFilterType);


});// end of DOMContentLoaded