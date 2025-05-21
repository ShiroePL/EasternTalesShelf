// LeftSidebarStats.js - Handles fetching and updating statistics for the left sidebar filters

/**
 * Fetches statistics for the left sidebar from GraphQL and updates the UI
 */
export async function initializeSidebarStats() {
    try {
        // Try the main aggregation query first
        let stats = await fetchSidebarStats();
        
        // If the main query fails, try the fallback method
        if (!stats) {
            stats = await fetchSidebarStatsFallback();
        }
        
        // If the fallback also fails, try the final individual queries fallback
        if (!stats) {
            stats = await fetchIndividualStats();
        }
        
        if (stats) {
            updateStatusCounts(stats);
            updateReleaseStatusCounts(stats);
            addFilterEventListeners();
        } else {
            console.error('Failed to fetch sidebar stats using any method');
            // Still add filter event listeners even if stats failed
            addFilterEventListeners();
        }
    } catch (error) {
        console.error('Error initializing sidebar stats:', error);
        // Still add filter event listeners even if stats failed
        addFilterEventListeners();
    }
}

/**
 * Fetch statistics from GraphQL endpoint
 */
async function fetchSidebarStats() {
    const query = `
    query GetSidebarStats {
        # Get list status counts
        completed: manga_list_aggregated(filter: { on_list_status: { _eq: "COMPLETED" } }) {
            count { id_anilist }
        }
        current: manga_list_aggregated(filter: { on_list_status: { _eq: "CURRENT" } }) {
            count { id_anilist }
        }
        planning: manga_list_aggregated(filter: { on_list_status: { _eq: "PLANNING" } }) {
            count { id_anilist }
        }
        paused: manga_list_aggregated(filter: { on_list_status: { _eq: "PAUSED" } }) {
            count { id_anilist }
        }
        
        # Get total count
        all_manga: manga_list_aggregated {
            count { id_anilist }
        }
        
        # Get release status counts
        releasing: manga_list_aggregated(filter: { status: { _eq: "RELEASING" } }) {
            count { id_anilist }
        }
        finished: manga_list_aggregated(filter: { status: { _eq: "FINISHED" } }) {
            count { id_anilist }
        }
        
        # Get favorite count - using 1 instead of true
        favorites: manga_list_aggregated(filter: { is_favourite: { _eq: 1 } }) {
            count { id_anilist }
        }
        
        # Get reread count - using _gt: 0 for numeric comparison
        reread: manga_list_aggregated(filter: { reread_times: { _gt: 0 } }) {
            count { id_anilist }
        }
    }`;

    try {
        // Use the common GraphQL request handler to handle authentication/fallback
        const result = await window.sendGraphQLRequest({ query });

        if (result.errors) {
            console.error('GraphQL errors in sidebar stats query:', result.errors);
            // Show more detailed error information
            if (result.errors[0]?.extensions?.errors) {
                console.error('Detailed validation errors:', result.errors[0].extensions.errors);
            }
            return null;
        }

        // Extract counts from aggregated results
        return {
            listStatus: {
                completed: result.data.completed[0]?.count?.id_anilist || 0,
                current: result.data.current[0]?.count?.id_anilist || 0,
                planning: result.data.planning[0]?.count?.id_anilist || 0,
                paused: result.data.paused[0]?.count?.id_anilist || 0,
                total: result.data.all_manga[0]?.count?.id_anilist || 0
            },
            releaseStatus: {
                releasing: result.data.releasing[0]?.count?.id_anilist || 0,
                finished: result.data.finished[0]?.count?.id_anilist || 0
            },
            special: {
                favorites: result.data.favorites[0]?.count?.id_anilist || 0,
                reread: result.data.reread[0]?.count?.id_anilist || 0
            }
        };
    } catch (error) {
        console.error('Error fetching sidebar stats:', error);
        return null;
    }
}

/**
 * Fallback method that fetches stats with individual queries
 * to avoid any issues with complex filtering
 */
async function fetchSidebarStatsFallback() {
    try {
        // Make individual simple queries
        const totalQuery = `
        query GetTotalCount {
            manga_list_aggregated {
                count { id_anilist }
            }
        }`;
        
        // Use the common GraphQL request handler
        const result = await window.sendGraphQLRequest({ query: totalQuery });
        
        if (result.errors) {
            console.error('Error in fallback query:', result.errors);
            return null;
        }
        
        const totalCount = result.data.manga_list_aggregated[0]?.count?.id_anilist || 0;
        
        // If we couldn't get a total count, we can't continue
        if (totalCount === 0) {
            return null;
        }
        
        // Use DOM counting as a last resort
        const gridItems = document.querySelectorAll('.grid-item');
        
        // Default response with at least the total count
        return {
            listStatus: {
                completed: countItems(gridItems, 'data-user-status', 'COMPLETED'),
                current: countItems(gridItems, 'data-user-status', 'CURRENT'),
                planning: countItems(gridItems, 'data-user-status', 'PLANNING'),
                paused: countItems(gridItems, 'data-user-status', 'PAUSED'),
                total: totalCount
            },
            releaseStatus: {
                releasing: countItems(gridItems, 'data-release-status', 'RELEASING'),
                finished: countItems(gridItems, 'data-release-status', 'FINISHED'),
            },
            special: {
                favorites: countItems(gridItems, 'data-is-favourite', '1'),
                reread: countItemsWithGreaterValue(gridItems, 'data-reread-times', 0)
            }
        };
    } catch (error) {
        console.error('Error in stats fallback method:', error);
        return null;
    }
}

/**
 * Helper function to count grid items matching a specific attribute value
 */
function countItems(items, attribute, value) {
    let count = 0;
    items.forEach(item => {
        if (item.getAttribute(attribute) === value) {
            count++;
        }
    });
    return count;
}

/**
 * Helper function to count grid items with attribute value > threshold
 */
function countItemsWithGreaterValue(items, attribute, threshold) {
    let count = 0;
    items.forEach(item => {
        const value = parseInt(item.getAttribute(attribute) || '0');
        if (value > threshold) {
            count++;
        }
    });
    return count;
}

/**
 * Update the user list status counts in the sidebar
 */
function updateStatusCounts(stats) {
    document.getElementById('count-completed').textContent = stats.listStatus.completed;
    document.getElementById('count-current').textContent = stats.listStatus.current;
    document.getElementById('count-planning').textContent = stats.listStatus.planning;
    document.getElementById('count-paused').textContent = stats.listStatus.paused;
    document.getElementById('count-all-user-stats').textContent = stats.listStatus.total;
    
    // Also update the label texts with the counts
    updateOptionLabel('isRereaded_checkbox', `<i class="fas fa-book-reader" style="color: #007bff;"></i>Reread`);
    updateOptionLabel('isFavorite_checkbox', `<i class="fas fa-heart" style="color: red;"></i>Favorite`);
}

/**
 * Update the release status counts in the sidebar
 */
function updateReleaseStatusCounts(stats) {
    document.getElementById('count-releasing').textContent = stats.releaseStatus.releasing;
    document.getElementById('count-finished').textContent = stats.releaseStatus.finished;
    document.getElementById('count-all-release-stats').textContent = stats.listStatus.total;
}

/**
 * Update the label text for a checkbox option
 */
function updateOptionLabel(checkboxId, newHtml) {
    const checkbox = document.getElementById(checkboxId);
    if (checkbox) {
        const label = document.querySelector(`label[for="${checkboxId}"]`);
        if (label) {
            label.innerHTML = newHtml;
        }
    }
}

/**
 * Add event listeners for filter options
 */
function addFilterEventListeners() {
    // List status filter options
    document.querySelectorAll('.status-option').forEach(function(option) {
        option.addEventListener('click', function() {
            // Remove 'selected' class from all options
            document.querySelectorAll('.status-option').forEach(function(opt) {
                opt.classList.remove('selected');
            });

            // Add 'selected' class to the clicked option
            this.classList.add('selected');

            // Update the currentStatusFilter variable with the new value
            window.currentStatusFilter = this.getAttribute('data-value');

            // Call filterEntries to apply the filters
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            }
        });
    });

    // Release status filter options
    document.querySelectorAll('.statusReleasing-option').forEach(function(option) {
        option.addEventListener('click', function() {
            // Remove 'selected' class from all options
            document.querySelectorAll('.statusReleasing-option').forEach(function(opt) {
                opt.classList.remove('selected');
            });

            // Add 'selected' class to the clicked option
            this.classList.add('selected');

            // Update the currentReleasingStatusFilter variable with the new value
            window.currentReleasingStatusFilter = this.getAttribute('data-value');

            // Call filterEntries to apply the filters
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            } else {
                console.error('filterEntries function not available');
            }
        });
    });
    
    // Country checkboxes
    const japanCheckbox = document.getElementById('countryJapan');
    if (japanCheckbox) {
        japanCheckbox.addEventListener('change', function() {
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            }
        });
    }
    
    const koreaCheckbox = document.getElementById('countryKorea');
    if (koreaCheckbox) {
        koreaCheckbox.addEventListener('change', function() {
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            }
        });
    }
    
    // Also handle checkbox changes for favorites and reread
    const favoriteCheckbox = document.getElementById('isFavorite_checkbox');
    if (favoriteCheckbox) {
        favoriteCheckbox.addEventListener('change', function() {
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            }
        });
    }
    
    const rereadCheckbox = document.getElementById('isRereaded_checkbox');
    if (rereadCheckbox) {
        rereadCheckbox.addEventListener('change', function() {
            if (typeof window.filterEntries === 'function') {
                window.filterEntries();
            }
        });
    }
}

/**
 * Final fallback that runs individual simple queries for each count
 * This is the most resilient approach, but requires multiple requests
 */
async function fetchIndividualStats() {
    try {
        // Start with a stats object with all zeros
        const stats = {
            listStatus: {
                completed: 0,
                current: 0,
                planning: 0,
                paused: 0,
                total: 0
            },
            releaseStatus: {
                releasing: 0,
                finished: 0
            },
            special: {
                favorites: 0,
                reread: 0
            }
        };
        
        // Helper function to fetch a single count
        async function fetchCount(query) {
            try {
                const result = await window.sendGraphQLRequest({ query });
                
                if (result.errors) {
                    return 0;
                }
                
                // Return the first aggregated count or 0
                return result.data?.manga_list_aggregated?.[0]?.count?.id_anilist || 0;
            } catch (error) {
                return 0;
            }
        }
        
        // Get total count
        const totalCountQuery = `
        query GetTotalCount {
            manga_list_aggregated {
                count { id_anilist }
            }
        }`;
        
        stats.listStatus.total = await fetchCount(totalCountQuery);
        
        // If we couldn't get the total count, early exit
        if (stats.listStatus.total === 0) {
            return null;
        }
        
        // Get completed count
        const completedQuery = `
        query GetCompletedCount {
            manga_list_aggregated(filter: { on_list_status: { _eq: "COMPLETED" } }) {
                count { id_anilist }
            }
        }`;
        stats.listStatus.completed = await fetchCount(completedQuery);
        
        // Get current count
        const currentQuery = `
        query GetCurrentCount {
            manga_list_aggregated(filter: { on_list_status: { _eq: "CURRENT" } }) {
                count { id_anilist }
            }
        }`;
        stats.listStatus.current = await fetchCount(currentQuery);
        
        // Get planning count
        const planningQuery = `
        query GetPlanningCount {
            manga_list_aggregated(filter: { on_list_status: { _eq: "PLANNING" } }) {
                count { id_anilist }
            }
        }`;
        stats.listStatus.planning = await fetchCount(planningQuery);
        
        // Get paused count
        const pausedQuery = `
        query GetPausedCount {
            manga_list_aggregated(filter: { on_list_status: { _eq: "PAUSED" } }) {
                count { id_anilist }
            }
        }`;
        stats.listStatus.paused = await fetchCount(pausedQuery);
        
        // Get release status counts
        const releasingQuery = `
        query GetReleasingCount {
            manga_list_aggregated(filter: { status: { _eq: "RELEASING" } }) {
                count { id_anilist }
            }
        }`;
        stats.releaseStatus.releasing = await fetchCount(releasingQuery);
        
        const finishedQuery = `
        query GetFinishedCount {
            manga_list_aggregated(filter: { status: { _eq: "FINISHED" } }) {
                count { id_anilist }
            }
        }`;
        stats.releaseStatus.finished = await fetchCount(finishedQuery);
        
        // Get favorites count using 1 instead of true
        const favoritesQuery = `
        query GetFavoritesCount {
            manga_list_aggregated(filter: { is_favourite: { _eq: 1 } }) {
                count { id_anilist }
            }
        }`;
        stats.special.favorites = await fetchCount(favoritesQuery);
        
        // Get reread count
        const rereadQuery = `
        query GetRereadCount {
            manga_list_aggregated(filter: { reread_times: { _gt: 0 } }) {
                count { id_anilist }
            }
        }`;
        stats.special.reread = await fetchCount(rereadQuery);
        
        return stats;
    } catch (error) {
        console.error('Error in individual stats queries:', error);
        return null;
    }
}

// Initialize when the document is fully loaded
document.addEventListener('DOMContentLoaded', initializeSidebarStats);

// Listen for the mangaGridLoaded event to refresh statistics
document.addEventListener('mangaGridLoaded', () => {
    initializeSidebarStats();
}); 