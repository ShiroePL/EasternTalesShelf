import { initializeAnimations, startAnimationSequence } from './RightsidebarAnimations.js';
import { typeWriter } from './RightSidebarUtilities.js';

import {
    updateSidebarCover,
    updateSidebarTitle,
    updateSidebarInfo,
    updateMangaUpdatesInfo,
    updateSidebarDescription,
    updateSidebarNotes,
    updateExternalLinks,
    updateGenres,
    updateSidebarLinks
} from './RightSidebarUIUpdaters.js';

// Use local variables for the function's private use
let localAnilistId;
let localSeriesName;

export async function showDetails(element) {
    // First, immediately reset animations and clear existing timers
    resetAnimationsAndTimers();

    // Get the anilist ID from the clicked element
    localAnilistId = $(element).data('anilist-id');
    localSeriesName = $(element).data('title');
    
    console.log('DEBUG: showDetails called for:', { 
        element: element,
        dataAnilistId: $(element).data('anilist-id'),
        dataTitle: $(element).data('title')
    });
    
    // Set the global variables that other modules expect
    window.currentAnilistId = localAnilistId;
    window.currentSeriesName = localSeriesName;
    
    console.log('DEBUG: Global variables set to:', { 
        currentAnilistId: window.currentAnilistId,
        currentSeriesName: window.currentSeriesName
    });

    try {
        // Fetch data from GraphQL
        const data = await fetchMangaDetailsFromGraphQL(localAnilistId);
        
        if (!data) {
            console.error('Failed to fetch manga details');
            return;
        }

        // Update UI elements (title first to ensure container is sized properly)
        updateSidebarTitle(data);
        updateSidebarCover(data);
        updateSidebarInfo(data);
        updateMangaUpdatesInfo(data);
        updateSidebarDescription(data);
        updateSidebarNotes(data);
        updateExternalLinks(data);
        updateGenres(data);
        updateSidebarLinks(data);

        // Initialize animations
        initializeAnimations();

        // Start animation sequence
        startAnimationSequence();

        // Wait a bit longer before starting typewriter effect for title
        window.typewriterTimeout = setTimeout(function() {
            // Calculate typing speed - much faster now, especially for longer titles
            // For short titles (< 15 chars), use 30ms delay
            // For longer titles, use even shorter delays (15-20ms)
            const typingSpeed = data.title.length < 15 ? 30 : 15;
            
            // Fade in and start typewriter after title container is properly sized
            $('#sidebar-title').fadeIn(300);
            typeWriter(data.title, 'sidebar-title', typingSpeed);
        }, 800);
    } catch (error) {
        console.error('Error showing details:', error);
        // Reset global variables when an error occurs
        window.currentAnilistId = null;
        window.currentSeriesName = null;
    }
}

async function fetchMangaDetailsFromGraphQL(anilistId) {
    // Update GraphQL query to match Directus's standard query structure
    const query = `
    query GetMangaDetails($id: GraphQLStringOrFloat!) {
        # Get a single manga by ID from the manga_list table
        manga_list(filter: { id_anilist: { _eq: $id } }, limit: 1) {
            id_anilist
            title_english
            title_romaji
            is_favourite
            on_list_status
            score
            chapters_progress
            all_chapters
            volumes_progress
            all_volumes
            status
            notes
            description
            bato_link
            reread_times
            user_startedAt
            user_completedAt
            media_start_date
            media_end_date
            genres
            external_links
        }
        # Get related manga updates
        mangaupdates_details(filter: { anilist_id: { _eq: $id } }, limit: 1) {
            status
            licensed
            completed
            last_updated_timestamp
        }
    }
`;

    try {
        // Use the common GraphQL request handler to handle authentication/fallback
        const result = await window.sendGraphQLRequest({
            query,
            variables: { id: anilistId.toString() } // Convert to string as Directus expects string IDs
        });
        
        if (result.errors) {
            console.error('GraphQL errors:', result.errors);
            return null;
        }

        // Update object names to match the new query structure
        const manga = result.data.manga_list ? result.data.manga_list[0] : null;
        const mangaUpdates = result.data.mangaupdates_details?.length > 0 ? 
                            result.data.mangaupdates_details[0] : null;
                            
        if (!manga) {
            console.error('No manga found with ID:', anilistId);
            window.currentAnilistId = null; // Reset global variable if no manga found
            window.currentSeriesName = null;
            return null;
        }

        // Format the data to match what the UI expects
        // Determine which title to use - use title_romaji if title_english is 'None' or null/undefined
        const displayTitle = (manga.title_english === 'None' || !manga.title_english) ? 
                             manga.title_romaji : 
                             manga.title_english;
        
        return {
            anilistId: manga.id_anilist,
            title: displayTitle,
            anilistUrl: `https://anilist.co/manga/${manga.id_anilist}`,
            id_mal: manga.id_mal || 0,
            myanimelistUrl: manga.id_mal ? `https://myanimelist.net/manga/${manga.id_mal}` : null,
            batoLink: manga.bato_link,
            description: manga.description,
            is_favorite: manga.is_favourite,
            chapters_progress: manga.chapters_progress,
            chapters_total: manga.all_chapters,
            volumes_progress: manga.volumes_progress,
            volumes_total: manga.all_volumes,
            user_status: manga.on_list_status,
            user_startedat: manga.user_startedAt || 'not started',
            user_completedat: manga.user_completedAt || 'not completed',
            release_status: manga.status,
            media_start_date: manga.media_start_date || 'None',
            media_end_date: manga.media_end_date || 'None',
            reread_times: manga.reread_times || 0,
            mangaupdates_status: mangaUpdates?.status || null,
            mangaupdates_licensed: mangaUpdates?.licensed || null,
            mangaupdates_completed: mangaUpdates?.completed || null,
            mangaupdates_last_updated: mangaUpdates?.last_updated_timestamp || null,
            user_notes: manga.notes || 'None',
            // Parse JSON strings if needed
            externalLinksData: manga.external_links || '[]',
            genresData: manga.genres || '[]'
        };
    } catch (error) {
        console.error('Error fetching manga details:', error);
        return null;
    }
}

function resetAnimationsAndTimers() {
    // Reset UI elements
    $('#sidebar-toggle').html('Read more &#9660;');
    $('#sidebar-shownotes').html('Show Notes');
    $('#sidebar-links a').hide();
    $('#sidebar-reread-icon').remove();
    
    // Clear the title completely
    if (document.getElementById('sidebar-title')) {
        document.getElementById('sidebar-title').textContent = '';
    }
    
    // Stop any ongoing animations and hide elements
    $('#sidebar-cover, #sidebar-toggle, #sidebar-title, #sidebar-info, #mangaupdates-info, #sidebar-description, #sidebar-notes, #sidebar-external-links, #sidebar-genres, #sidebar-links, #sidebar-shownotes').stop(true, true).hide();
    
    // Clear all animation timeouts
    clearTimeout(window.typewriterTimeout);
    
    // Clear any global animation variables that might exist
    window.typewriterCompleted = false;
    
    // Ensure sidebar is visible
    $('#side-menu-right').removeClass('sidebar-hidden').addClass('sidebar-visible');
}

// Functions for opening external links
export function openAniList(url) {
    if (url) {
        window.open(url, '_blank');
    }
}

export function openBatoFromCover(url) {
    if (url && url !== 'None') {
        window.open(url, '_blank');
    }
}

window.showDetails = showDetails;
window.openAniList = openAniList;
window.openBatoFromCover = openBatoFromCover;
