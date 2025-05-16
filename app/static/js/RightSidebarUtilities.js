export function typeWriter(text, elementId, speed) {
    // Clear any existing text and stop any ongoing animation
    clearTimeout(window.typewriterTimeout);
    const element = document.getElementById(elementId);
    element.textContent = '';
    
    // Keep track of which characters have been displayed
    let displayedText = '';
    let currentIndex = 0;
    
    function typeNextChar() {
        if (currentIndex < text.length) {
            // Add the next character to our displayed text
            displayedText += text[currentIndex];
            // Update the element with the current text
            element.textContent = displayedText;
            currentIndex++;
            // Schedule the next character
            window.typewriterTimeout = setTimeout(typeNextChar, speed);
        }
    }
    
    // Start the animation
    typeNextChar();
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