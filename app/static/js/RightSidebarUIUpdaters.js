import { formatDates, adjustButtonSpacing } from './RightSidebarUtilities.js';
import { processExternalLinks, processGenres, capitalizeFirstLetter, formatBatoUploadStatus } from './RightSidebarDataHandlers.js';
import { animateHeartBurstWithParticles, startHeartsFlowingEffect, animateRereadIcon } from './RightsidebarAnimations.js';

export function updateSidebarCover(data) {
    let coverImage = '/static/covers/' + data.anilistId + '.avif';

    // Track the current active ID to avoid unnecessary animations
    let clickedAnilistId_for_hearts = data.anilistId;

    // Set the cover image for the sidebar
    $('#sidebar-cover').attr('src', coverImage).attr('alt', data.title);

    if (data.is_favorite === 1) {
        // If the favorite icon does not exist, append it
        if ($('#sidebar-favorite-icon').length === 0) {
            $('#cover-container').append('<i id="sidebar-favorite-icon" class="fas fa-heart"></i>');
        }

        // Only trigger animations if we are opening a new title
        if (!$('#side-menu-right').hasClass('active') || currentActiveAnilistId !== clickedAnilistId_for_hearts) {
            // Set the new current active ID
            currentActiveAnilistId = clickedAnilistId_for_hearts;

            // Trigger the heart animation with a small delay to allow for smooth transition
            setTimeout(function() {
                animateHeartBurstWithParticles();
            }, 200);
            
            // Start flowing hearts effect
            startHeartsFlowingEffect();
        }


    } else {
        $('#sidebar-favorite-icon').remove();
    }

    if (data.reread_times > 0) {
        // Remove any existing reread icon first to prevent duplicates
        $('#sidebar-reread-icon').remove();
        
        let rereadDisplayOriginal = `
            <div id="sidebar-reread-icon" class="reread-icon">
                <i class="fas fa-sync-alt rotate"></i>
                <span class="reread-count">${data.reread_times}</span>
            </div>`;
        $('#cover-container').append(rereadDisplayOriginal);
        
        setTimeout(function() {
            animateRereadIcon('#sidebar-reread-icon');
            
        }, 200);
    }
    
}

export function updateSidebarTitle(data) {
    // Set the placeholder text to calculate the required height
    const titlePlaceholder = $('#sidebar-title-placeholder');
    const titleContainer = $('#sidebar-title-container');
    
    // Set the text and make sure it's visible for accurate measurement
    titlePlaceholder.text(data.title);
    
    // Wait a tiny bit to ensure the browser has calculated dimensions
    setTimeout(() => {
        // Add extra padding to ensure enough space
        let titleHeight = titlePlaceholder.height() + 15;
        
        // Set container height with additional buffer
        titleContainer.height(titleHeight);
        
        // Ensure the title element is completely empty
        document.getElementById('sidebar-title').textContent = '';
    }, 0);
}

export function updateSidebarInfo(data) {
    let sidebarInfoHTML = `
        <p><i class="fas fa-book-open chapter-icon flip"></i> Chapters: ${data.chapters_progress} / ${data.chapters_total === 0 ? '?' : data.chapters_total}</p>`;
    
    // Add Bato.to latest chapter if available
    if (data.batoLatestChapter && data.batoLatestChapter.dname) {
        sidebarInfoHTML += `
        <p><i class="fas fa-book"></i> Batotwo: ${data.batoLatestChapter.dname}</p>`;
    }
    
    sidebarInfoHTML += `
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
    
    // Add Bato.to upload status if available
    if (data.batoUploadStatus) {
        const batoStatusData = formatBatoUploadStatus(data.batoUploadStatus);
        if (batoStatusData) {
            sidebarInfoHTML += `
        <p><i class="fas fa-cloud-upload-alt"></i> <span style="color: ${batoStatusData.color};">Batotwo: ${batoStatusData.statusCapitalized}</span></p>`;
        }
    }

    // Add Side Stories selector with custom dropdown design (admin only) or read-only display
    const currentStatus = data.side_stories_status || 'none';
    const statusLabels = {
        'none': '❓ None',
        'released': '✓ Released',
        'releasing': '📖 Releasing',
        'planned': '⏰ Planned'
    };
    
    const isNone = currentStatus === 'none';
    
    // Always show the compact display for everyone
    sidebarInfoHTML += `
        <div class="side-stories-inline mt-2" id="sideStoriesContainer">
            <div class="side-stories-header">
                <span class="side-stories-label">
                    <i class="fas fa-book-medical"></i> Side Stories:
                </span>
                <span class="side-stories-value" id="sideStoriesDisplay" data-current-status="${currentStatus}">${statusLabels[currentStatus]}</span>
            </div>
        </div>`;

    $('#sidebar-info').html(sidebarInfoHTML);
    
    // Check if user is admin and make the value clickable for dropdown functionality
    if (window.isUserAdmin && isLoggedIn) {
        window.isUserAdmin().then(isAdmin => {
            if (isAdmin) {
                // Make the value clickable and add visual cue for admins
                const $sideStoriesValue = $('#sideStoriesDisplay');
                $sideStoriesValue.addClass('admin-clickable');
                
                // Add click handler to show dropdown
                $sideStoriesValue.off('click').on('click', function(e) {
                    e.stopPropagation();
                    
                    // Replace with dropdown on first click
                    const currentStatus = $(this).attr('data-current-status');
                    const dropdownHTML = `
                        <div class="custom-side-stories-dropdown" id="sideStoriesDropdown">
                            <div class="custom-dropdown-selected active" data-value="${currentStatus}">
                                <span class="dropdown-text">${statusLabels[currentStatus]}</span>
                                <span class="dropdown-arrow">▼</span>
                            </div>
                            <div class="custom-dropdown-options show">
                                <div class="custom-dropdown-option ${currentStatus === 'none' ? 'active' : ''}" data-value="none">❓ None</div>
                                <div class="custom-dropdown-option ${currentStatus === 'released' ? 'active' : ''}" data-value="released">✓ Released</div>
                                <div class="custom-dropdown-option ${currentStatus === 'releasing' ? 'active' : ''}" data-value="releasing">📖 Releasing</div>
                                <div class="custom-dropdown-option ${currentStatus === 'planned' ? 'active' : ''}" data-value="planned">⏰ Planned</div>
                            </div>
                        </div>`;
                    
                    $('#sideStoriesContainer').html(`
                        <div class="side-stories-header">
                            <span class="side-stories-label">
                                <i class="fas fa-book-medical"></i> Side Stories:
                            </span>
                        </div>
                        ${dropdownHTML}
                    `);
                    
                    initializeSideStoriesDropdown();
                });
            }
        }).catch(err => {
            console.log('Could not check admin status, keeping read-only display');
        });
    }
}

// Separate function to initialize side stories dropdown (for admin users only)
function initializeSideStoriesDropdown() {
    // Initialize custom dropdown behavior
    const dropdown = $('#sideStoriesDropdown');
    const selected = dropdown.find('.custom-dropdown-selected');
    const options = dropdown.find('.custom-dropdown-options');
    const optionElements = dropdown.find('.custom-dropdown-option');
    
    // Toggle dropdown on click
    selected.off('click').on('click', function(e) {
        e.stopPropagation();
        selected.toggleClass('active');
        options.toggleClass('show');
    });
    
    // Handle option selection
    optionElements.off('click').on('click', async function(e) {
        e.stopPropagation();
        const newStatus = $(this).attr('data-value');
        const anilistId = window.currentAnilistId;
        
        if (!anilistId) {
            console.error('No anilist ID available');
            return;
        }
        
        // Add loading state
        dropdown.addClass('loading');
        
        try {
            const response = await fetch(`/api/manga/${anilistId}/side-stories`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status: newStatus })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update side stories status');
            }
            
            // Update the data attribute on the grid item
            const gridItem = document.querySelector(`[data-anilist-id="${anilistId}"]`);
            if (gridItem) {
                gridItem.setAttribute('data-side-stories-status', newStatus);
                
                // Update the side stories icon on the cover
                const sideStoriesIcon = gridItem.querySelector('.side-stories-icon');
                if (sideStoriesIcon) {
                    sideStoriesIcon.setAttribute('data-side-stories-status', newStatus);
                }
            }
            
            // Update UI
            optionElements.removeClass('active');
            $(this).addClass('active');
            selected.find('.dropdown-text').text($(this).text());
            selected.attr('data-value', newStatus);
            
            // Close dropdown
            selected.removeClass('active');
            options.removeClass('show');
            
            // Success feedback
            selected.addClass('success');
            setTimeout(() => {
                selected.removeClass('success');
                
                // If changed back to 'none', hide dropdown and show reveal button again
                if (newStatus === 'none') {
                    setTimeout(() => {
                        dropdown.slideUp(300, function() {
                            dropdown.addClass('hidden');
                            $('.side-stories-header').append(`<button class="side-stories-reveal-btn" id="revealSideStoriesBtn"><i class="fas fa-eye"></i></button>`);
                            
                            // Re-attach click handler for the new button
                            $('#revealSideStoriesBtn').off('click').on('click', function(e) {
                                e.stopPropagation();
                                $(this).fadeOut(200, function() {
                                    $(this).remove();
                                    dropdown.removeClass('hidden').hide().slideDown(300);
                                    setTimeout(() => {
                                        selected.addClass('active');
                                        options.addClass('show');
                                    }, 100);
                                });
                            });
                        });
                    }, 500);
                }
            }, 600);
            
        } catch (error) {
            console.error('Error updating side stories status:', error);
            
            // Error feedback
            selected.addClass('error');
            setTimeout(() => selected.removeClass('error'), 600);
        } finally {
            selected.removeClass('loading');
        }
    });
    
    // Close dropdown when clicking outside
    $(document).off('click.sideStoriesDropdown').on('click.sideStoriesDropdown', function(e) {
        if (!$(e.target).closest('#sideStoriesDropdown').length) {
            selected.removeClass('active');
            options.removeClass('show');
        }
    });
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
    let processedLinks = processExternalLinks(data.externalLinksData, data.mangaupdates_url);
    
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