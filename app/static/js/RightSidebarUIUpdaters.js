import { formatDates, adjustButtonSpacing } from './RightSidebarUtilities.js';
import { processExternalLinks, processGenres, capitalizeFirstLetter } from './RightSidebarDataHandlers.js';
import { animateHeartBurstWithParticles, startHeartsFlowingEffect, animateRereadIcon } from './RightsidebarAnimations.js';

export function updateSidebarCover(data) {
    let coverImage = '/static/covers/' + data.anilistId + '.avif';
    $('#sidebar-cover').attr('src', coverImage).attr('alt', data.title);

    if (data.is_favorite === 1) {
        if ($('#sidebar-favorite-icon').length === 0) {
            $('#cover-container').append('<i id="sidebar-favorite-icon" class="fas fa-heart"></i>');
        }

        // Wait for next event loop tick to ensure DOM updates are processed
        setTimeout(function() {
            animateHeartBurstWithParticles();
        }, 0);
    
        startHeartsFlowingEffect();
        

    } else {
        $('#sidebar-favorite-icon').remove();
    }

    if (data.reread_times > 0) {
        let rereadDisplayOriginal = `
            <div id="sidebar-reread-icon" class="reread-icon">
                <i class="fas fa-sync-alt rotate"></i>
                <span class="reread-count">${data.reread_times}</span>
            </div>`;
        $('#cover-container').append(rereadDisplayOriginal);
        animateRereadIcon('#sidebar-reread-icon');
    }
    
}

export function updateSidebarTitle(data) {
    $('#sidebar-title-placeholder').text(data.title);
    let titleHeight = $('#sidebar-title-placeholder').height();
    $('#sidebar-title-container').height(titleHeight);
    document.getElementById('sidebar-title').innerHTML = '';
}

export function updateSidebarInfo(data) {
    let sidebarInfoHTML = `
        <p><i class="fas fa-book-open chapter-icon flip"></i> Chapters: ${data.chapters_progress} / ${data.chapters_total === 0 ? '?' : data.chapters_total}</p>
        <p><i class="fas fa-layer-group progress-icon bounce"></i> Volumes: ${data.volumes_progress} / ${data.volumes_total === 0 ? '?' : data.volumes_total}</p>`;

    let statusIcon = getStatusIcon(data.user_status);
    let statusColor = getStatusColor(data.user_status);
    let releaseStatusIcon = getReleaseStatusIcon(data.release_status);

    let { userDatesHTML, mediaDatesHTML } = formatDates(data.user_startedat, data.user_completedat, data.media_start_date, data.media_end_date);

    // Format the statuses using the helper function
    const formattedUserStatus = capitalizeFirstLetter(data.user_status);
    const formattedReleaseStatus = capitalizeFirstLetter(data.release_status);

    sidebarInfoHTML += `<p>${statusIcon} <span style="color: ${statusColor};">Status: ${formattedUserStatus}</span></p>
        ${userDatesHTML}
        <p>${releaseStatusIcon} OG Release: ${formattedReleaseStatus}</p>
        ${mediaDatesHTML}`;

    $('#sidebar-info').html(sidebarInfoHTML);
}




export function updateMangaUpdatesInfo(data) {
    let mangaUpdatesHTML = '';
    const mangaUpdatesContentElement = $('#mangaupdates-content');

    if (data.mangaupdates_status) {
        // Replace newline characters with <br> tags for HTML display
        let formattedStatus = data.mangaupdates_status.replace(/\n/g, '<br>');
    
        // Search for specific words and wrap them in spans with different colors
        formattedStatus = formattedStatus.replace(/Complete/g, '<span style="color: rgb(40, 167, 69);">Complete</span>');
        formattedStatus = formattedStatus.replace(/Ongoing/g, '<span style="color: rgb(255, 193, 7);">Ongoing</span>');
        
        
        // Build HTML for the status
        mangaUpdatesHTML += `<p id="mangaupdates-status" class="m-1"><i class="fas fa-info-circle"></i> <span style="color: rgb(55, 160, 249);">Status:</span> ${formattedStatus}</p>`;
    }

    if (data.mangaupdates_licensed) {
        mangaUpdatesHTML += `<p id="mangaupdates-licensed" class="m-1"><i class="fas fa-certificate"></i> Licensed: ${data.mangaupdates_licensed}</p>`;
    }
    if (data.mangaupdates_completed) {
        mangaUpdatesHTML += `<p id="mangaupdates-completed" class="m-1"><i class="fas fa-check"></i> Completed: ${data.mangaupdates_completed}</p>`;
    }
    if (data.mangaupdates_last_updated) {
        mangaUpdatesHTML += `<p id="mangaupdates-last-updated" class="m-1"><i class="fas fa-calendar-alt"></i> Last Updated: ${data.mangaupdates_last_updated}</p>`;
    }

    // Update the content of the element
    if (mangaUpdatesHTML !== '') {
        mangaUpdatesContentElement.html(mangaUpdatesHTML);
    } else {
        mangaUpdatesContentElement.html(''); // Clear the content if there's no data
    }
}



export function updateSidebarDescription(data) {
    $('#sidebar-description').html(data.description).removeClass('expanded').addClass('collapse');
    
    $('#sidebar-description').css('max-height', '7.5em');

    if ($('#sidebar-description')[0].scrollHeight <= 90) {
        $('#sidebar-shownotes').hide();
        $('#sidebar-toggle').hide();
    } else {
        $('#sidebar-shownotes').show();
        $('#sidebar-toggle').show();
    }
}

export function updateSidebarNotes(data) {
    $('#sidebar-notes').text(data.user_notes).removeClass('expanded').addClass('collapse');
    if (data.user_notes.trim() === "None") {
        $('#sidebar-shownotes').hide();
    } else {
        // Fade in the 'Show Notes' link after a delay only if the notes are not "None"
        timeouts.shownotes = setTimeout(() => {
            $('#sidebar-shownotes').fadeIn(650);
        }, 1100);
    }
}

export function updateExternalLinks(data) {
    let linksContainer = document.getElementById('sidebar-external-links');
    let processedLinks = processExternalLinks(data.externalLinksData);
    
    while (linksContainer.firstChild) {
        linksContainer.removeChild(linksContainer.firstChild);
    }
    linksContainer.appendChild(processedLinks);
}

export function updateGenres(data) {
    $('#sidebar-genres').html(processGenres(data.genresData));
}

export function updateSidebarLinks(data) {
    $('#link-anilist').attr('href', data.anilistUrl).show();

    if (data.id_mal != 0) {
        $('#link-mal').attr('href', data.myanimelistUrl).show();
    } else {
        $('#link-mal').hide();
    }

    if (data.batoLink && data.batoLink !== "None") {
        $('#link-bato').attr('href', data.batoLink).show();
    } else {
        $('#link-bato').hide();
    }

    adjustButtonSpacing();
}

function getStatusIcon(status) {
    switch (status.toLowerCase()) {
        case 'completed': return '<i class="fas fa-check-circle status-icon pulse"></i>';
        case 'planning': return '<i class="fas fa-hourglass-start status-icon fade"></i>';
        case 'current': return '<i class="fas fa-book-reader status-icon vertical-move"></i>';
        case 'paused': return '<i class="fas fa-pause-circle status-icon shake"></i>';
        default: return '<i class="fas fa-question-circle status-icon"></i>';
    }
}

function getStatusColor(status) {
    switch (status.toLowerCase()) {
        case 'completed': return 'rgb(40, 167, 69)';
        case 'planning': return 'rgb(255, 193, 7)';
        case 'current': return 'rgb(14, 159, 212)';
        case 'paused': return 'rgb(224, 33, 8)';
        default: return 'inherit';
    }
}

function getReleaseStatusIcon(status) {
    if (status.toLowerCase() === 'releasing') {
        return '<i class="fas fa-sync-alt status-icon rotate"></i>';
    } else if (status.toLowerCase() === 'finished') {
        return '<i class="fas fa-flag-checkered status-icon shake"></i>';
    } else {
        return '<i class="fas fa-circle-notch status-icon"></i>';
    }
}