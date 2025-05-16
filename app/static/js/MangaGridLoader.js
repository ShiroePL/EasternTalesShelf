// MangaGridLoader.js - Handles fetching and rendering manga grid data
import { showDetails } from './RightSidebarMain.js';

// Constants for controlling progressive loading
const BATCH_SIZE = 12; // Number of manga entries to render at once
const BATCH_DELAY = 100; // Milliseconds between batches
const PAGE_SIZE = 50; // Number of manga entries to fetch per GraphQL request

// Main function to load manga grid data
export async function loadMangaGrid() {
    const container = document.getElementById('manga-grid-container');
    try {
        // Display initial loading state
        container.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <p>Loading your manga collection...</p>
            </div>
        `;

        // Get collection counts to determine total pages
        const counts = await fetchCollectionCounts();
        console.log(`Total manga items: ${counts.mangaCount}, Total pages: ${counts.totalPages}`);

        // Fetch download statuses once at the beginning
        const downloadStatuses = await fetchDownloadStatuses();

        // Clear the loading container before rendering the first batch
        container.innerHTML = '';

        // Use the total pages from our count
        const totalPages = counts.totalPages;

        for (let currentPage = 1; currentPage <= totalPages; currentPage++) {
            console.log(`Fetching page ${currentPage} of ${totalPages}...`);
            const pageData = await fetchMangaGridFromGraphQL(currentPage, PAGE_SIZE);
            
            if (!pageData || !pageData.mangaList || pageData.mangaList.length === 0) {
                console.log(`No data for page ${currentPage}, stopping.`);
                break;
            }

            // Merge manga data with download statuses and MangaUpdates details
            const mergedDataPage = pageData.mangaList.map(manga => ({
                ...manga,
                download_status: downloadStatuses[manga.id_anilist] || 'not_downloaded',
                mangaupdates_details: pageData.detailsMap[manga.id_anilist] || null
            }));

            // Load the current page of manga entries progressively
            await loadMangaProgressively(mergedDataPage, container);

            // Optional: Add a small delay between page fetches if needed
            // await new Promise(resolve => setTimeout(resolve, 200));
        }

        // Apply event listeners after all items from all pages are loaded
        applyGridItemEventListeners();

        // Initialize AOS after all content is loaded
        initializeAOS();

    } catch (error) {
        console.error('Error loading manga grid:', error);
        container.innerHTML = '<p class="error-message">Error loading manga data. Please try again.</p>';
    }
}

// Initialize or refresh AOS
function initializeAOS() {
    // Delay slightly to ensure DOM is fully updated
    setTimeout(() => {
        if (typeof AOS !== 'undefined') {
            console.log('Initializing AOS for dynamic content');
            // Refresh AOS to recognize all the newly added items
            AOS.refresh();
            
            // Optionally trigger the global refresh if needed elsewhere
            if (window.refreshAOS) {
                // window.refreshAOS(); // We call AOS.refresh directly here, so this might be redundant
            }
        } else {
            console.warn('AOS library not loaded or available');
        }
    }, 200); // Increased delay slightly
}

// Load manga entries progressively in batches
async function loadMangaProgressively(mangaEntries, container) {
    // Prepare container for grid items
    const isAdmin = container.dataset.isAdmin === 'true';
    const isDevelopment = container.dataset.isDevelopment === 'true';
    
    // Create a fragment to minimize DOM operations
    const fragment = document.createDocumentFragment();
    
    // Process entries in batches
    for (let i = 0; i < mangaEntries.length; i += BATCH_SIZE) {
        const batch = mangaEntries.slice(i, i + BATCH_SIZE);
        
        // Create elements for this batch
        batch.forEach(entry => {
            const gridItem = createGridItem(entry, isDevelopment, isAdmin);
            fragment.appendChild(gridItem);
            
            // Load cover image asynchronously (doesn't block rendering)
            if (!entry.is_cover_downloaded) {
                checkAndLoadCover(entry, gridItem, isDevelopment);
            }
        });
        
        // Add this batch to the DOM
        container.appendChild(fragment);
        
        // Apply visual enhancements to this batch
        applyUiEnhancements();
        
        // Refresh AOS after each batch to handle scrolling during loading
        if (typeof AOS !== 'undefined' && i > 0 && i % (BATCH_SIZE * 2) === 0) {
            AOS.refresh();
        }
        
        // Allow the browser to render and process this batch
        await new Promise(resolve => setTimeout(resolve, BATCH_DELAY));
    }
}

// Create a single grid item element
function createGridItem(entry, isDevelopment, isAdmin) {
    const gridItem = document.createElement('div');
    gridItem.className = `grid-item ${!entry.is_cover_downloaded ? 'skeleton-cover' : ''}`;
    gridItem.setAttribute('data-anilist-id', entry.id_anilist);
    gridItem.setAttribute('data-title', entry.title_english);
    gridItem.setAttribute('data-user-status', entry.on_list_status);
    gridItem.setAttribute('data-bato-link', entry.bato_link || '');
    
    // Set AOS attributes
    gridItem.setAttribute('data-aos', 'fade-up');
    gridItem.setAttribute('data-aos-offset', '120');
    gridItem.setAttribute('data-aos-duration', '800');
    gridItem.setAttribute('data-aos-delay', '50');
    
    // Set background image if cover is downloaded
    if (entry.is_cover_downloaded) {
        gridItem.style.backgroundImage = `url('${isDevelopment ? '/dev_covers/' : '/static/covers/'}${entry.id_anilist}.avif')`;
        gridItem.style.backgroundSize = 'cover';
        gridItem.style.backgroundPosition = 'center';
    } else {
        // Add skeleton placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'skeleton-placeholder';
        
        const animation = document.createElement('div');
        animation.className = 'skeleton-animation';
        
        placeholder.appendChild(animation);
        gridItem.appendChild(placeholder);
    }
    
    // Add title
    const titleDiv = document.createElement('div');
    titleDiv.className = 'grid-item-title';
    titleDiv.textContent = entry.title_english;
    gridItem.appendChild(titleDiv);
    
    // Add score icon
    const scoreIcon = document.createElement('div');
    scoreIcon.className = 'score-icon';
    scoreIcon.setAttribute('data-score', entry.score);
    gridItem.appendChild(scoreIcon);
    
    // Add favorite icon
    const favoriteIcon = document.createElement('div');
    favoriteIcon.className = 'favorite-icon';
    favoriteIcon.setAttribute('data-is-favourite', entry.is_favourite);
    gridItem.appendChild(favoriteIcon);
    
    // Add reread icon
    const rereadIcon = document.createElement('div');
    rereadIcon.className = 'reread-cover-icon';
    rereadIcon.setAttribute('data-reread-times', entry.reread_times);
    gridItem.appendChild(rereadIcon);
    
    // Add bato icon
    const batoIcon = document.createElement('div');
    batoIcon.className = 'bato-icon';
    batoIcon.setAttribute('onclick', 'event.stopPropagation();');
    gridItem.appendChild(batoIcon);
    
    // Add anilist icon
    const anilistIcon = document.createElement('div');
    anilistIcon.className = 'anilist-icon';
    anilistIcon.setAttribute('onclick', `event.stopPropagation(); window.openAniList('https://anilist.co/manga/${entry.id_anilist}')`);
    gridItem.appendChild(anilistIcon);
    
    // Add stats
    const statsDiv = document.createElement('div');
    statsDiv.className = 'stats';
    statsDiv.innerHTML = `
        Chapters: ${entry.chapters_progress}/${entry.all_chapters || '?'}<br>
        Volumes: ${entry.volumes_progress}/${entry.all_volumes || '?'}<br>
        Status: ${entry.on_list_status}<br>
        Release: ${entry.status}<br>
    `;
    gridItem.appendChild(statsDiv);
    
    // Add download controls for admin users
    if (isAdmin) {
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'manga-controls';
        
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'download-status-btn';
        downloadBtn.setAttribute('data-status', entry.download_status || 'not_downloaded');
        downloadBtn.setAttribute('data-anilist-id', entry.id_anilist);
        downloadBtn.setAttribute('data-title', entry.title_english);
        downloadBtn.setAttribute('data-bato-link', entry.bato_link || '');
        
        const icon = document.createElement('i');
        icon.className = 'fas fa-arrow-circle-down';
        downloadBtn.appendChild(icon);
        
        controlsDiv.appendChild(downloadBtn);
        gridItem.appendChild(controlsDiv);
    }
    
    return gridItem;
}

// Asynchronously check if cover exists and load it
async function checkAndLoadCover(entry, gridItem, isDevelopment) {
    const coverUrl = `${isDevelopment ? '/dev_covers/' : '/static/covers/'}${entry.id_anilist}.avif`;
    
    // Create a new image to check if cover exists
    const img = new Image();
    
    img.onload = async function() {
        // Cover exists, update the UI
        gridItem.classList.remove('skeleton-cover');
        gridItem.style.backgroundImage = `url('${coverUrl}')`;
        gridItem.style.backgroundSize = 'cover';
        gridItem.style.backgroundPosition = 'center';
        
        // Remove placeholder
        const placeholder = gridItem.querySelector('.skeleton-placeholder');
        if (placeholder) {
            placeholder.remove();
        }
        
        // Update the database status if needed
        if (!entry.is_cover_downloaded) {
            try {
                await updateCoverStatus(entry.id_anilist, true);
            } catch (err) {
                console.error('Error updating cover status:', err);
            }
        }
    };
    
    img.onerror = function() {
        // Cover doesn't exist or error loading
        console.log(`Cover for ${entry.title_english} (ID: ${entry.id_anilist}) not found or error loading`);
        // Keep the skeleton placeholder visible
    };
    
    // Start loading the image
    img.src = coverUrl;
}

// First, fetch collection counts to calculate pages
async function fetchCollectionCounts() {
    const query = `
    query GetCollectionCounts {
        manga_list_aggregated {
            count {
                id_anilist
            }
        }
    }`;

    try {
        const response = await fetch('/graphql/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({ query })
        });

        const result = await response.json();

        if (result.errors) {
            console.error('GraphQL errors fetching collection counts:', result.errors);
            return { mangaCount: 0, totalPages: 0 };
        }

        // Extract the counts from the aggregated results
        const mangaCount = result.data.manga_list_aggregated[0]?.count?.id_anilist || 0;
        
        // Calculate total pages
        const totalPages = Math.ceil(mangaCount / PAGE_SIZE);

        return {
            mangaCount,
            totalPages
        };
    } catch (error) {
        console.error('Error fetching collection counts:', error);
        return { mangaCount: 0, totalPages: 0 };
    }
}

// Fetch manga data from GraphQL endpoint for a specific page
async function fetchMangaGridFromGraphQL(page, limit) {
    const query = `
    query GetMangaPage($page: Int, $limit: Int) {
        manga_list(sort: ["-last_updated_on_site"], page: $page, limit: $limit) {
            id_anilist
            id_mal
            title_english
            on_list_status
            status
            all_chapters
            all_volumes
            chapters_progress
            volumes_progress
            score
            is_cover_downloaded
            is_favourite
            reread_times
            bato_link
            last_updated_on_site
        }
        mangaupdates_details {
            anilist_id
            status
            licensed
            completed
            last_updated_timestamp
        }
    }`;

    const variables = { page, limit };

    try {
        const response = await fetch('/graphql/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({ query, variables })
        });

        const result = await response.json();

        if (result.errors) {
            console.error('GraphQL errors:', result.errors);
            return { mangaList: [], detailsMap: {} };
        }

        // Process manga entries and details
        const mangaList = result.data.manga_list || [];
        const mangaUpdatesDetails = result.data.mangaupdates_details || [];

        // Map mangaupdates_details by anilist_id for easier lookup
        const detailsMap = {};
        mangaUpdatesDetails.forEach(detail => {
            detailsMap[detail.anilist_id] = detail;
        });

        return {
            mangaList,
            detailsMap
        };
    } catch (error) {
        console.error(`Error fetching manga grid data for page ${page}:`, error);
        return { mangaList: [], detailsMap: {} };
    }
}

// Fetch download statuses from the server
async function fetchDownloadStatuses() {
    try {
        const response = await fetch('/api/download-statuses');
        const data = await response.json();
        
        if (!data.success) {
            console.error('Error fetching download statuses:', data.message);
            return {};
        }
        
        // Convert to a lookup object where keys are anilist_ids and values are statuses
        const statusMap = {};
        data.statuses.forEach(item => {
            statusMap[item.anilist_id] = item.status;
        });
        
        return statusMap;
    } catch (error) {
        console.error('Error fetching download statuses:', error);
        return {};
    }
}

// Update the cover status in the database
async function updateCoverStatus(anilistId, isDownloaded) {
    try {
        const response = await fetch('/update_cover_status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify({
                anilist_id: anilistId,
                is_downloaded: isDownloaded
            })
        });
        
        const result = await response.json();
        if (!result.success) {
            console.error('Error updating cover status:', result.message);
        }
        return result.success;
    } catch (error) {
        console.error('Error updating cover status:', error);
        return false;
    }
}

// Apply event listeners to grid items
function applyGridItemEventListeners() {
    document.querySelectorAll('.grid-item').forEach(item => {
        item.addEventListener('click', function() {
            showDetails(this);
        });
        
        const batoIcon = item.querySelector('.bato-icon');
        if (batoIcon) {
            batoIcon.addEventListener('click', function(e) {
                e.stopPropagation();
                const batoLink = item.dataset.batoLink;
                if (batoLink && batoLink !== 'None') {
                    window.open(batoLink, '_blank');
                }
            });
        }
    });
}

// Apply UI enhancements like colors, icons, etc.
function applyUiEnhancements() {
    // Apply score colors
    document.querySelectorAll('.score-icon').forEach(function(element) {
        let score = parseFloat(element.getAttribute('data-score'));
        let result = scoreToColor(score);
        element.style.backgroundColor = result.color;
        element.textContent = result.text;
    });

    // Apply border classes based on status
    document.querySelectorAll('.grid-item').forEach(function(item) {
        let status = item.dataset.userStatus;
        if (status) {
            status = status.toLowerCase();
            let statusClass = 'border-' + status;
            item.classList.add(statusClass);
        }
    });

    // Favorite icons
    document.querySelectorAll('.favorite-icon').forEach(function(icon) {
        let isFavourite = parseInt(icon.dataset.isFavourite);
        if (isFavourite === 1) {
            icon.innerHTML = '<i class="fas fa-heart" id="heart-icon-grid"></i>';
        }
    });

    // Reread icons
    document.querySelectorAll('.reread-cover-icon').forEach(function(icon) {
        let rereadTimes = parseInt(icon.dataset.rereadTimes);
        if (rereadTimes > 0) {
            icon.innerHTML = '<i class="fas fa-book-reader" id="reread-icon-grid">' + rereadTimes + '</i>';
        }
    });

    // Bato icons visibility
    document.querySelectorAll('.bato-icon').forEach(function(icon) {
        let url = icon.parentElement.dataset.batoLink;
        if (url && url !== "None") {
            icon.style.display = ''; // Show the icon
        } else {
            icon.style.display = 'none'; // Hide the icon
        }
    });
}

// Score to color function (copied from UIUpdaters.js for consistency)
function scoreToColor(score) {
    let displayText = score === 0.0 ? '?' : score.toString();
    let color;

    if (score === 0.0) {
        color = '#9E9E9E'; // Default color for score 0.0
    } else {
        let roundedScore = Math.floor(score); // Round down to nearest whole number
        switch (roundedScore) {
            case 10: color = '#4CAF50'; break; // Bright green
            case 9: color = '#8BC34A'; break; // Light green
            case 8: color = '#CDDC39'; break; // Lime
            case 7: color = '#D4E157'; break; // Light lime
            case 6: color = '#FFEB3B'; break; // Yellow
            case 5: color = '#FFC107'; break; // Amber
            case 4: color = '#FF9800'; break; // Orange
            case 3: color = '#FF5722'; break; // Deep orange
            case 2: color = '#F44336'; break; // Red
            case 1: color = '#B71C1C'; break; // Deep red
            default: color = '#9E9E9E'; break; // Default color for invalid scores
        }
    }

    return { color: color, text: displayText };
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', loadMangaGrid); 