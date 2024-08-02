export function typeWriter(text, elementId, speed) {
    let i = 0;
    function type() {
        if (i < text.length) {
            document.getElementById(elementId).innerHTML += text.charAt(i);
            i++;
            window.typewriterTimeout = setTimeout(type, speed);
        }
    }
    type();
}

// format dates in sidebar info and media info sections 
export function formatDates(user_startedat, user_completedat, media_start_date, media_end_date) {
    let userDatesHTML = '';
    let mediaDatesHTML = '';

    // User dates
    if (user_startedat !== 'not started') {
        // If started, check if completed
        let completedText = user_completedat !== 'not completed' ? user_completedat : '?';
        userDatesHTML = `<p class="date-info"><span class="icon-placeholder"></span>${user_startedat}  &bull;  ${completedText}</p>`;
    }

    // Media dates
    if (!media_start_date.includes('None')) {
        // If started, check if finished
        let finishedText = media_end_date.includes('None') ? '?' : media_end_date;
        mediaDatesHTML = `<p class="date-info"><span class="icon-placeholder"></span>${media_start_date}  &bull;  ${finishedText}</p>`;
    }

    return { userDatesHTML, mediaDatesHTML };
}

export function adjustButtonSpacing() {
    let visibleButtons = $('#sidebar-links a:visible').length;

    $('#sidebar-links a').removeClass('btn-solo btn-pair btn-trio');

    switch(visibleButtons) {
        case 1:
            $('#sidebar-links a:visible').addClass('btn-solo');
            break;
        case 2:
            $('#sidebar-links a:visible').addClass('btn-pair');
            break;
        case 3:
            $('#sidebar-links a').addClass('btn-trio');
            break;
    }
}