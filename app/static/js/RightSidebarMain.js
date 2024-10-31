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

export function showDetails(element) {
    resetAnimationsAndTimers();

    currentAnilistId = $(element).data('anilist-id');
    currentSeriesName = $(element).data('title');

    // Extract data from the element
    const data = extractDataFromElement(element);

    // Update UI elements
    updateSidebarCover(data);
    updateSidebarTitle(data);
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

    // Start typewriter effect for title
    window.typewriterTimeout = setTimeout(function() {
        typeWriter(data.title, 'sidebar-title', 40);
        $('#sidebar-title').fadeIn(300);
    }, 650);

    
}

function extractDataFromElement(element) {
    // Extract all the data attributes from the element
    return {
        anilistId: $(element).data('anilist-id'),
        title: $(element).data('title'),
        anilistUrl: $(element).data('anilist-url'),
        id_mal: $(element).data('id-mal'),
        myanimelistUrl: 'https://myanimelist.net/manga/' + $(element).data('id-mal'),
        batoLink: $(element).data('bato-link'),
        description: $(element).data('description'),
        is_favorite: $(element).data('is-favourite'),
        chapters_progress: $(element).data('chapters-progress'),
        chapters_total: $(element).data('all-chapters'),
        volumes_progress: $(element).data('volumes-progress'),
        volumes_total: $(element).data('all-volumes'),
        user_status: $(element).data('user-status'),
        user_startedat: $(element).data('user-startedat'),
        user_completedat: $(element).data('user-completedat'),
        release_status: $(element).data('release-status'),
        media_start_date: $(element).data('media-start-date'),
        media_end_date: $(element).data('media-end-date'),
        reread_times: $(element).data('reread-times'),
        mangaupdates_status: $(element).data('mangaupdates-status'),
        mangaupdates_licensed: $(element).data('mangaupdates-licensed'),
        mangaupdates_completed: $(element).data('mangaupdates-completed'),
        mangaupdates_last_updated: $(element).data('mangaupdates-last-updated'),
        user_notes: $(element).data('notes'),
        externalLinksData: $(element).attr('data-external-links'),
        genresData: $(element).attr('data-genres')
    };
}

function resetAnimationsAndTimers() {
    // Reset animations and clear timeouts
    $('#sidebar-toggle').html('Read more &#9660;');
    $('#sidebar-shownotes').html('Show Notes');
    $('#sidebar-links a').hide();
    $('#sidebar-reread-icon').remove();
    $('#sidebar-cover, #sidebar-toggle, #sidebar-title, #sidebar-info, #mangaupdates-info, #sidebar-description, #sidebar-notes, #sidebar-external-links, #sidebar-genres, #sidebar-links, #sidebar-shownotes').stop(true, true).hide();
    clearTimeout(window.typewriterTimeout);
    $('#side-menu-right').removeClass('sidebar-hidden').addClass('sidebar-visible');
}

window.showDetails = showDetails;
