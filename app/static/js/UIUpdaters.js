function toggleMenu() {
    let menu = document.getElementById("side-menu");
    if (menu.style.left === "-250px") {
        menu.style.left = "0px";
    } else {
        menu.style.left = "-250px";
    }
}

function scoreToColor(score) {
    let displayText = score === 0.0 ? '?' : score.toString();
    let color;

    if (score === 0.0) {
        color = '#9E9E9E'; // Default color for score 0.0
    } else {
        let roundedScore = Math.floor(score); // Round down to nearest whole number
        switch (roundedScore) {
            case 10:
                color = '#4CAF50'; // Bright green
                break;
            case 9:
                color = '#8BC34A'; // Light green
                break;
            case 8:
                color = '#CDDC39'; // Lime
                break;
            case 7:
                color = '#D4E157'; // Light lime
                break;
            case 6:
                color = '#FFEB3B'; // Yellow
                break;
            case 5:
                color = '#FFC107'; // Amber
                break;
            case 4:
                color = '#FF9800'; // Orange
                break;
            case 3:
                color = '#FF5722'; // Deep orange
                break;
            case 2:
                color = '#F44336'; // Red
                break;
            case 1:
                color = '#B71C1C'; // Deep red
                break;
            default:
                color = '#9E9E9E'; // Default color for invalid scores
                break;
        }
    }

    return { color: color, text: displayText };
}

// Apply colors to score elements
document.querySelectorAll('.score-icon').forEach(function(element, index) {
    let score = parseFloat(element.getAttribute('data-score')); // Assuming you store the score in a data attribute
    let result = scoreToColor(score);
    element.style.backgroundColor = result.color;
    element.textContent = result.text;
});

$(document).ready(function() {
    $('.favorite-icon').each(function() {
        let isFavourite = $(this).data('is-favourite');
        if (isFavourite === 1) {
            // Adds a heart icon inside the div if data-is-favourite is 1
            $(this).html('<i class="fas fa-heart" id="heart-icon-grid"></i>');
        }
    });

    $('.reread-cover-icon').each(function() {
        // Handle favorite icon    
        // Handle reread icon
        let rereadTimes = $(this).data('reread-times');
        if (rereadTimes > 0) {
            $(this).append('<i class="fas fa-book-reader" id="reread-icon-grid">' + rereadTimes + '</i>'); // Append reread icon with times
        }
    });

    $('.bato-icon').each(function() {
    // Get the URL from the data-bato-link attribute
    let url = $(this).parent().attr('data-bato-link');

    // Check if the URL exists and is valid
    if (url && url !== "None") {
        // If the URL exists, ensure the icon is visible
        $(this).show(); // This line assumes you're using display:none to hide by default
    } else {
        // If the URL does not exist, hide the icon
        $(this).hide(); // Ensure the icon is not visible
    }
    });

});