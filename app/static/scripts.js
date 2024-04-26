

// EXAMPLE OF USING DOMCONTENTLOADED
//document.addEventListener('DOMContentLoaded', (event) => {
    // Your code to run after the DOM is fully loaded
//});


function toggleMenu() {
    let menu = document.getElementById("side-menu");
    if (menu.style.left === "-250px") {
        menu.style.left = "0px";
    } else {
        menu.style.left = "-250px";
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Code for chatInput
    let chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    } else {
        console.error('chatInput element not found!');
    }});


// Code for syncButton
let syncButton = document.getElementById('syncButton');

if (syncButton) {
    syncButton.addEventListener('click', function() {
        fetch('/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.ok && response.headers.get("content-type")?.includes("application/json")) {
                return response.json();
            }
            throw new Error('Server responded with a non-JSON response.');
        })
        .then(data => {
            console.log('Success:', data);
            alert('Sync successful!');
            window.location.reload(); // Reload the page
        })
        .catch((error) => {
            console.error('Error:', error);
            alert('An error occurred: ' + error.message);
        });
    });
} else {
    console.error('Sync button element not found!');
}

let currentAnilistId = null; // This will store the currently focused entry's AniList ID

document.getElementById('addBatoLinkButton').addEventListener('click', function() {
    if (currentAnilistId) {
        let batoLink = prompt("Please enter the Bato link for this entry:", "http://");
        if (batoLink !== null && batoLink !== "") {
            fetch('/add_bato', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    anilistId: currentAnilistId,
                    batoLink: batoLink
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Success:', data);
                alert('Bato link added successfully!');
                window.location.reload(); // Reload the page
            })
            .catch((error) => {
                console.error('Error:', error);
                alert('An error occurred: ' + error.message);
            });
        } else if (batoLink === "") {
            alert('No link entered. Please enter a valid Bato link.');
        }
    } else {
        alert('No entry is focused currently.');
    }
});








let currentFilterType = 'ALL'; // Default to 'ALL' on page load

// this prevents AOS to move down page each reloding.
if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }



// Consolidated load event listener
window.addEventListener('load', function() {

    // Initialize or refresh AOS based on cumulative height logic
    let items = document.querySelectorAll('.grid-item');
    let cumulativeHeight = 0;
    items.forEach(function(item) {
        if (item.style.display !== 'none') {
            cumulativeHeight += item.offsetHeight + 10; // Adjust if necessary
        }
    });

    let windowHeight = window.innerHeight;
    if (cumulativeHeight > windowHeight) {
        setTimeout(function(){
            AOS.init({
                offset: 120,
                duration: 1000,
            });
        }, 100); // Adjust the timeout as needed
    }

    // AOS refresh logic
    AOS.refresh();

    // Set border color based on data-status
    items.forEach(function(item) {
        let status = item.getAttribute('data-user-status');
        if(status) {
            status = status.toUpperCase();
            let statusClass = 'border-' + status.toLowerCase();
            item.classList.add(statusClass);
        }
    });
});

// Consolidated resize event listener
window.addEventListener('resize', () => {
    AOS.refresh();
});

// Initialize a variable to keep track of the current status filter
let currentStatusFilter = '';

// Event listener for status filter options
document.querySelectorAll('.status-option').forEach(function(option) {
    option.addEventListener('click', function() {
        // Remove 'selected' class from all options
        document.querySelectorAll('.status-option').forEach(function(opt) {
            opt.classList.remove('selected');
        });

        // Add 'selected' class to the clicked option
        this.classList.add('selected');

        // Update the currentStatusFilter variable with the new value
        currentStatusFilter = this.getAttribute('data-value');

        // Call filterEntries to apply the filters
        filterEntries();
    });
});

// Initialize a variable to keep track of the current status filter
let currentReleasingStatusFilter = '';

// Event listener for status filter options
document.querySelectorAll('.statusReleasing-option').forEach(function(option) {
    option.addEventListener('click', function() {
        // Remove 'selected' class from all options
        document.querySelectorAll('.statusReleasing-option').forEach(function(opt) {
            opt.classList.remove('selected');
        });

        // Add 'selected' class to the clicked option
        this.classList.add('selected');

        // Update the currentStatusFilter variable with the new value
        currentReleasingStatusFilter = this.getAttribute('data-value');

        // Call filterEntries to apply the filters
        filterEntries();
    });
});


function filterEntries() {
    const titleFilter = document.getElementById('titleFilter').value.toLowerCase();
    const countryJapan = document.getElementById('countryJapan').checked;
    const countryKorea = document.getElementById('countryKorea').checked;
    const isFavorite_checkbox = document.getElementById('isFavorite_checkbox').checked;
    const isRereaded_checkbox = document.getElementById('isRereaded_checkbox').checked;
    // Since we are not using select for status, we will use currentStatusFilter
    // const statusFilter = document.getElementById('status').value;

    const filterLogic = {
        'NOVEL': (country, type) => country === 'JP' && type === 'NOVEL',
        'MANHWA': (country, type) => country === 'KR' && type === 'MANGA',
        'MANGA': (country, type) => country === 'JP' && type === 'MANGA',
        'ALL': () => true
    };

    // Get all the grid items
    const items = document.querySelectorAll('.grid-item');

    items.forEach(function(item) {
        const title = (item.getAttribute('data-title') || '').toLowerCase();
        const country = item.getAttribute('data-country') || '';
        const type = item.getAttribute('data-type') || '';
        const itemStatus = item.getAttribute('data-user-status') || '';
        const itemReleasingStatus = item.getAttribute('data-release-status') || '';
        // Determine whether item should be visible based on the navbar filter and side menu filters
        const matchesTitle = titleFilter === '' || title.includes(titleFilter);
        const matchesCountry = (!countryJapan && !countryKorea) || 
                                (countryJapan && country === 'JP') || 
                                (countryKorea && country === 'KR');
        const matchesFavorite = !isFavorite_checkbox || item.getAttribute('data-is-favourite') === '1';
        const matchesRereaded = !isRereaded_checkbox || item.getAttribute('data-reread-times') > '0';
        //const matchesStatus = statusFilter === '' || itemStatus.toLowerCase() === statusFilter.toLowerCase();
        // Determine whether item should be visible based on the status filter
        // Using currentStatusFilter instead of statusFilter
        const matchesStatus = currentStatusFilter === '' || itemStatus.toLowerCase() === currentStatusFilter.toLowerCase();
        const matchesFilterType = filterLogic[currentFilterType](country, type);
        const matchesReleasingStatus = currentReleasingStatusFilter === '' || itemReleasingStatus.toLowerCase() === currentReleasingStatusFilter.toLowerCase();
        // Determine whether item should be visible based on the status filter
        // Using currentStatusFilter instead of statusFilter
        
        if (matchesTitle && matchesCountry  && matchesStatus && matchesFilterType && matchesReleasingStatus && matchesFavorite && matchesRereaded) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });

    AOS.refresh();
}




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

// Make sure to call filterEntries on page load to apply any default filters
filterEntries();



// Wait until the DOM is fully loaded before initializing the filter
document.addEventListener('DOMContentLoaded', function() {
    filterByType(currentFilterType);
});



document.addEventListener('aos:in', ({ detail }) => {
    console.log('animated in', detail);
    // You could trigger a layout update here, if necessary
    // For example, if you're using a layout library or need to manually update the footer position
  });
  
  document.addEventListener('aos:out', ({ detail }) => {
    console.log('animated out', detail);
    // Handle the animation out event
  });
  



// Global variables for timeout and animation tracking
let globalTimeout;
let isAnimating = false;

// Global variables for animation timeouts
let timeouts = {
    cover: null,
    info: null,
    link: null,
    description: null,
    readmore: null,
    externalLinks: null,
    genres: null,
    title_placeholder: null,
    shownotes: null,
    notes: null
};

function showDetails(element) {  
    resetAnimationsAndTimers(); // Reset animations and clear timeouts


    // Reset description to initial collapsed state
    
    $('#sidebar-toggle').html('Read more &#9660;'); // Reset the toggle button text
    $('#sidebar-shownotes').html('Show Notes');
    
    // Check if an animation is ongoing, if so, reset everything immediately
    currentAnilistId = $(element).data('anilist-id'); // Capture and store the anilist_id for the add bato link button
    $('#sidebar-links a').hide();
    $('#sidebar-reread-icon').remove();
    // Abort any ongoing animations, clear timeouts, and hide elements
    $('#sidebar-cover, #sidebar-toggle, #sidebar-title, #sidebar-info, #sidebar-description, #sidebar-notes, #sidebar-external-links, #sidebar-genres, #sidebar-links, #sidebar-shownotes').stop(true, true).hide();
    clearTimeout(window.typewriterTimeout); // Clear any ongoing typewriter timeouts

    // Ensure the sidebar is visible for height calculations
    $('#side-menu-right').removeClass('sidebar-hidden').addClass('sidebar-visible');


    let title = $(element).data('title');
    let anilistUrl = $(element).data('anilist-url');
    let myanimelistUrl = 'https://myanimelist.net/manga/' + $(element).data('id-mal'); // Assuming this is stored similarly
    let batoLink = $(element).data('bato-link');
    let description = $(element).data('description');
    let is_favorite = $(element).data('is-favourite');

    // SIDEBAR INFORMATIONS ABOUT ENTRIES
    let chapters_progress = $(element).data('chapters-progress');
    let chapters_total = $(element).data('all-chapters');
    let volumes_progress = $(element).data('volumes-progress');
    let volumes_total = $(element).data('all-volumes');
    let user_status = $(element).data('user-status');
    let user_startedat = $(element).data('user-startedat');
    let user_completedat = $(element).data('user-completedat');
    let release_status = $(element).data('release-status');
    let media_start_date = $(element).data('media-start-date');
    let media_end_date = $(element).data('media-end-date');
    let reread_times = $(element).data('reread-times'); // Assuming you have this data attribute set

    if (chapters_total === 0 || chapters_total == null) {
        chapters_total = '?';
    }
    if (volumes_total === 0 || volumes_total == null) {
        volumes_total = '?';
    }

    function updateSidebarLinks(anilistUrl, batoLink, myanimelistUrl) {
        $('#link-anilist').attr('href', anilistUrl);
        $('#link-bato').attr('href', batoLink);
        $('#link-mal').attr('href', myanimelistUrl);
    }
    function adjustButtonSpacing() {
        let visibleButtons = $('#sidebar-links a:visible').length;
        
        $('#sidebar-links a').removeClass('btn-solo btn-pair btn-trio'); // Clear previous classes
    
        // Apply new class based on how many buttons are visible
        switch(visibleButtons) {
            case 1:
                $('#sidebar-links a:visible').addClass('btn-solo'); // For when there's only 1 button visible
                break;
            case 2:
                $('#sidebar-links a:visible').addClass('btn-pair'); // For when there are 2 buttons visible
                break;
            case 3:
                $('#sidebar-links a').addClass('btn-trio'); // For when all 3 buttons are visible
                break;
        }
    }
    
    // Update the links
    updateSidebarLinks(anilistUrl, batoLink, myanimelistUrl);

    // Conditionally show buttons based on data
    $('#link-anilist').attr('href', anilistUrl).show();; // Always shown, adjust if necessary

    if ($(element).data('id-mal') != 0) {
      $('#link-mal').attr('href', myanimelistUrl).show();
    }

    if (batoLink !== '') {
      $('#link-bato').attr('href', batoLink).show()
    }

    // Adjust button spacing and centering dynamically
    adjustButtonSpacing();


    let user_notes = $(element).data('notes');
    
    // Convert user_status and release_status to uppercase
    user_status = user_status.toUpperCase();
    release_status = release_status.toUpperCase();

    // Convert user_status and release_status to first uppercase, then lowercase
    user_status = user_status.charAt(0).toUpperCase() + user_status.slice(1).toLowerCase();
    release_status = release_status.charAt(0).toUpperCase() + release_status.slice(1).toLowerCase();

    // Retrieve the raw data from the data attributes
    let externalLinksData = $(element).attr('data-external-links');
    let genresData = $(element).attr('data-genres');

    // Populate sidebar elements ----------------------------------------------------------------------------
    
    // Hide all elements before updating
    $('#sidebar-cover, #sidebar-toggle, #sidebar-shownotes, #sidebar-title, #sidebar-info, #sidebar-description,#sidebar-notes, #sidebar-external-links, #sidebar-genres, #sidebar-links').hide();

    // Debounce subsequent calls to prevent rapid execution
    clearTimeout(globalTimeout);
    globalTimeout = setTimeout(function() {
        


        let anilistId = $(element).data('anilist-id');
    
        // Construct the cover image path based on the Anilist ID
        // Adjust the file extension and path as necessary
        let coverImage = '/static/covers/' + anilistId + '.avif';

        
        // Update the elements
        $('#sidebar-cover').attr('src', coverImage).attr('alt', title);
        
        // Assuming is_favorite is already defined and holds a value of 0 or 1
        if (is_favorite === 1) {
            // Check if the heart icon already exists to avoid duplicates
            if ($('#sidebar-favorite-icon').length === 0) {
                $('#cover-container').append('<i id="sidebar-favorite-icon" class="fas fa-heart"></i>');
            }
            console.log("is favorite");
        
            // Wait for next event loop tick to ensure DOM updates are processed
            setTimeout(function() {
                animateHeartBurstWithParticles();
            }, 0);
        
            startHeartsFlowingEffect();
        } else {
            // If not a favorite, remove the heart icon if it exists
            $('#sidebar-favorite-icon').remove();
        }
        
        
        // Only if reread_times is greater than 0, append a new reread icon
        if (reread_times > 0) {
            // Existing icon append logic (keep it if you still need the original icon)
            let rereadDisplayOriginal = `
                <div id="sidebar-reread-icon" class="reread-icon">
                    <i class="fas fa-sync-alt rotate"></i>
                    <span class="reread-count">${reread_times}</span>
                </div>`;
            $('#cover-container').append(rereadDisplayOriginal);
                    
            // Trigger the animation for both icons
            animateRereadIcon('#sidebar-reread-icon'); // For the original icon
            
        }
        
        
        
                
            


        // Update the placeholder with the title content
        $('#sidebar-title-placeholder').text(title);

        // Calculate and set the height for the title container
        let titleHeight = $('#sidebar-title-placeholder').height();
        $('#sidebar-title-container').height(titleHeight);

        // Reset and start typewriter effect for title
        document.getElementById('sidebar-title').innerHTML = '';
        window.typewriterTimeout = setTimeout(function() {
            typeWriter(title, 'sidebar-title', 40);
            $('#sidebar-title').fadeIn(300);
        }, 650);

    
        // Initialize the sidebar info HTML with chapters and volumes
        let sidebarInfoHTML = `
            <p><i class="fas fa-book-open chapter-icon flip"></i> Chapters: ${chapters_progress} / ${chapters_total}</p>
            <p><i class="fas fa-layer-group progress-icon bounce"></i> Volumes: ${volumes_progress} / ${volumes_total}</p>`;

        // Apply animation classes based on the status
        let statusIcon = '';
        let statusColor = ''; // Variable to hold the color based on the status
        switch (user_status) {
            case 'Completed':
                statusIcon = '<i class="fas fa-check-circle status-icon pulse"></i>';
                statusColor = 'rgb(40, 167, 69)'; // green for completed
                break;
            case 'Planning':
                statusIcon = '<i class="fas fa-hourglass-start status-icon fade"></i>';
                statusColor = 'rgb(255, 193, 7)'; // yellow for planning
                break;
            case 'Current':
                statusIcon = '<i class="fas fa-book-reader status-icon vertical-move"></i>';
                statusColor = 'rgb(14, 159, 212)'; // blue for current
                break;
            case 'Paused':
                statusIcon = '<i class="fas fa-pause-circle status-icon shake"></i>';
                statusColor = 'rgb(224, 33, 8)'; // red for paused
                break;
            default:
                statusIcon = '<i class="fas fa-question-circle status-icon"></i>'; // No specific color for the default case
                statusColor = 'inherit'; // Use the default text color
        }

                // Determine the release status icon and apply animation
        let releaseStatusIcon = '';
        if (release_status === 'Releasing') {
            releaseStatusIcon = '<i class="fas fa-sync-alt status-icon rotate"></i>';
        } else if (release_status === 'Finished') {
            releaseStatusIcon = '<i class="fas fa-flag-checkered status-icon shake"></i>';
        } else {
            releaseStatusIcon = '<i class="fas fa-circle-notch status-icon"></i>'; // Placeholder icon for other statuses
        }

        // Call the function with your date variables
        let { userDatesHTML, mediaDatesHTML } = formatDates(user_startedat, user_completedat, media_start_date, media_end_date);

       
        // Append user status and release status to sidebar info
        sidebarInfoHTML += `<p>${statusIcon} <span style="color: ${statusColor};">Status: ${user_status}</span></p>
        ${userDatesHTML}
        <p>${releaseStatusIcon} OG Release: ${release_status}</p>
        ${mediaDatesHTML}
        `;

        // Set the HTML to the sidebar-info element
        $('#sidebar-info').html(sidebarInfoHTML);

        

        

        

        // Set the description and always start with it collapsed
        $('#sidebar-description').html(description).removeClass('expanded').addClass('collapse');
        
        $('#sidebar-notes').text(user_notes).removeClass('expanded').addClass('collapse');
        

        // Reset max-height to collapsed state
        $('#sidebar-description').css('max-height', '7.5em'); // The max-height for the collapsed state

        // Hide the Read More button if the content is short enough to not need expansion
        
        // Hide the Read More button if the content is short enough to not need expansion
        if ($('#sidebar-description')[0].scrollHeight <= 90) { // 90px is 5 lines here
            $('#sidebar-shownotes').hide();
            $('#sidebar-toggle').hide();
        } else {
            $('#sidebar-shownotes').show();
            $('#sidebar-toggle').show();
        }
        // ---------------------------OPERATION ON LINK BUTTONS--------------------

        let serviceMap = {
            'mangaupdates.com': { name: 'Manga Updates', class: 'mangaupdates' },
            'tapas.io': { name: 'Tapas', class: 'tapas' },
            'tappytoon.com': { name: 'Tappytoon', class: 'tappytoon' },
            'www.webtoons.com': { name: 'Webtoons', class: 'webtoons' },
            'yenpress.com': { name: 'Yen Press', class: 'yenpress' },
            'sevenseasentertainment.com': { name: 'Seven Seas', class: 'sevenseas' },
            'j-novel.club': { name: 'J-Novel Club', class: 'jnovel' },
            // Add more mappings as needed
        };

        // Safely parse the JSON string into an array for external links
        try {
            let externalLinks = JSON.parse(externalLinksData || "[]");
            let linksContainer = document.getElementById('sidebar-external-links');
        
            if (externalLinks.length === 0) {
                linksContainer.innerHTML = '<h5 class="mb-2">No links available</h5>';
            } else {
                let linksHtml = document.createElement('div');
                linksHtml.innerHTML = '<h5 class="mb-2">Links</h5>';
        
                externalLinks.forEach(function(url) {
                    Object.keys(serviceMap).forEach(function(key) {
                        if (url.includes(key)) {
                            let serviceName = serviceMap[key].name;
                            let linkClass = serviceMap[key].class; // Custom class for serviceMap links
                            let button = document.createElement('a');
                            button.href = url;
                            button.textContent = serviceName;
                            button.className = 'btn ' + linkClass + ' btn-sm m-1';
                            button.target = '_blank';
                            linksHtml.appendChild(button);
                        }
                    });
                });
        
                // Replace the container's content with the safe linksHtml
                while (linksContainer.firstChild) {
                    linksContainer.removeChild(linksContainer.firstChild);
                }
                linksContainer.appendChild(linksHtml);
            }
        } catch (e) {
            console.error('Parsing error for external-links data:', e);
            document.getElementById('sidebar-external-links').innerHTML = '<h5 class="mb-2">No links available</h5>';
        }
        

        // ------------------------------- end of link buttons ---------------------

        // Safely parse the JSON string into an array for genres
        try {
            let genres = JSON.parse(genresData || "[]"); // Default to an empty array if undefined
            let genresHtml = '<h5 class="mb-2">Genres</h5>';
            genres.forEach(function(genre) {
                genresHtml += '<span class="badge bg-secondary me-1">' + genre + '</span>';
            });
            $('#sidebar-genres').html(genresHtml);
        } catch (e) {
            console.error('Parsing error for genres data:', e);
            $('#sidebar-genres').html('<h5 class="mb-2">No genres available</h5>');
        }

        

        // Start animations with controlled timeouts
        timeouts.cover = setTimeout(() => $('#sidebar-cover').fadeIn(1500), 100);
        timeouts.info = setTimeout(() => $('#sidebar-info').fadeIn(700), 600);
        // Fade in the button group after a delay
        clearTimeout(timeouts.link); // Clear any existing timeout to prevent multiple triggers
        timeouts.link = setTimeout(() => {
            $('#sidebar-links').fadeIn(650);
        }, 750);
        
        timeouts.description = setTimeout(() => $('#sidebar-description').fadeIn(800), 900);
        
        timeouts.notes = setTimeout(() => $('#sidebar-notes').fadeIn(800), 900);
        
        timeouts.readmore = setTimeout(() => $('#sidebar-toggle').fadeIn(650), 1100);
        timeouts.externalLinks = setTimeout(() => $('#sidebar-external-links').fadeIn(750), 1300);
        timeouts.genres = setTimeout(() => $('#sidebar-genres').fadeIn(750), 1550);

        // Show the sidebar with Bootstrap styling
        $('#side-menu-right').addClass('active');

        // If you update the notes dynamically, you can also toggle the visibility of the 'Show Notes' link
        $(document).ready(function() {
            let notesText = $('#sidebar-notes').text().trim();
            
            // Clear any previous timeouts to avoid multiple triggers
            if (timeouts?.shownotes) {
                clearTimeout(timeouts.shownotes);
            }
        
            if (notesText === "None") {
                // Hide the 'Show Notes' link immediately without delay
                $('#sidebar-shownotes').hide();
            } else {
                // Fade in the 'Show Notes' link after a delay only if the notes are not "None"
                timeouts.shownotes = setTimeout(() => {
                    $('#sidebar-shownotes').fadeIn(650);
                }, 1100);
            }
        });
        


    }, 100);
    
}


function resetAnimationsAndTimers() {
    // Stop all ongoing animations immediately and clear queue
    $('#sidebar-cover, #sidebar-toggle, #sidebar-info, #sidebar-links, #sidebar-description, #sidebar-notes, #sidebar-shownotes, #sidebar-external-links, #sidebar-genres').stop(true, true).hide();

    // Clear all timeouts
    for (let key in timeouts) {
        clearTimeout(timeouts[key]);
    }
}


function animateRereadIcon(selector) {
    $(selector).addClass('scale-up');
    setTimeout(function() {
        $(selector).removeClass('scale-up');
    }, 500); // Adjust timing if needed
}



// JavaScript to toggle the description with animation
$(document).on('click', '#sidebar-toggle', function() {
    let content = $('#sidebar-description');
    let isExpanded = content.hasClass('expanded');
    
    if (isExpanded) {
        // Collapse the content
        content.animate({
            'max-height': '7.5em' // Animate towards the collapsed max-height
        }, 500, function() {
            content.removeClass('expanded').addClass('collapse');
            $('#sidebar-toggle').html('Read more &#9660;'); // Update the link text and arrow
        });
    } else {
        // Expand the content
        let fullHeight = content[0].scrollHeight; // Calculate the full height of the content
        content.animate({
            'max-height': fullHeight // Animate towards the full height
        }, 500, function() {
            content.removeClass('collapse').addClass('expanded');
            $('#sidebar-toggle').html('Read less &#9650;'); // Update the link text and arrow
        });
    }
});


$(document).on('click', '#sidebar-shownotes', function() {
    let notes = $('#sidebar-notes');
    notes.toggleClass('expanded'); // This toggles the visibility
    
    if (notes.hasClass('expanded')) {
        $(this).text('Hide Notes');
        notes.css('max-height', ''); // Remove the inline max-height style
    } else {
        $(this).text('Show Notes');
        notes.css('max-height', '0px'); // Apply the inline max-height style
    }
});







// Insert this code into chat-script.js
function toggleChatbot() {
    let chatbot = document.getElementById('chatbot');
    // Toggle the visibility without affecting the chat history
    chatbot.style.display = chatbot.style.display === 'none' ? 'flex' : 'none';
}

function sendMessage() {
    console.log('Enter was pressed and sendMessage called');
    let input = document.getElementById('chatInput');
    let messageText = input.value.trim();
    if (messageText) {
        // Add user message
        addMessage('user', messageText);
        input.value = ''; // Clear the input
        // Simulate a bot response
        setTimeout(function() {
            addMessage('bot', "Let me think...");
        }, 1000);
    }
}

function addMessage(sender, text) {
    let messagesContainer = document.getElementById('chatMessages');
    let messageBubble = document.createElement('div');
    messageBubble.classList.add('chat-bubble', sender);
    let avatar = document.createElement('span');
    avatar.classList.add('avatar');
    messageBubble.appendChild(avatar);
    messageBubble.appendChild(document.createTextNode(text));
    messagesContainer.appendChild(messageBubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function openAniList(url) {
    window.open(url, '_blank');
}
function openBatoFromCover(url){
    // Get the data from the clicked element
    
    if (url !== '') {
        window.open(url, '_blank');
    }
}

// Modify the typewriter function to use a global timeout
window.typewriterTimeout = null;
function typeWriter(text, elementId, speed) {
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


document.addEventListener('DOMContentLoaded', function() {
    const mangaEntries = document.querySelectorAll('.grid-item');
    const statusCounts = {
        'COMPLETED': 0,
        'PLANNING': 0,
        'CURRENT': 0,
        'PAUSED': 0,
        'ALL-STATUS': mangaEntries.length // This is a special case for the 'All' filter
    };
    const releaseStatusCounts = {
        'RELEASING': 0,
        'FINISHED': 0
    };

    mangaEntries.forEach(entry => {
        const status = entry.getAttribute('data-user-status');
        if (status in statusCounts) {
            statusCounts[status]++;
        }
        const release_status = entry.getAttribute('data-release-status');
        if (release_status in releaseStatusCounts) {
            releaseStatusCounts[release_status]++;
        }
    });

    // Update the counts in the HTML
    document.getElementById('count-completed').textContent = statusCounts['COMPLETED'];
    document.getElementById('count-planning').textContent = statusCounts['PLANNING'];
    document.getElementById('count-current').textContent = statusCounts['CURRENT'];
    document.getElementById('count-paused').textContent = statusCounts['PAUSED'];
    document.getElementById('count-all-user-stats').textContent = statusCounts['ALL-STATUS'];
    document.getElementById('count-all-release-stats').textContent = statusCounts['ALL-STATUS'];
    document.getElementById('count-releasing').textContent = releaseStatusCounts['RELEASING'];
    document.getElementById('count-finished').textContent = releaseStatusCounts['FINISHED'];
});

// format dates in sidebar info and media info sections 
function formatDates(user_startedat, user_completedat, media_start_date, media_end_date) {
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

        // Check if the URL exists
        if (url !== '') {
            // If the URL exists, ensure the icon is visible
            // You could also add a specific class to manage visibility if preferred
            $(this).show(); // This line assumes you're using display:none to hide by default
        } else {
            // If the URL does not exist, hide the icon
            $(this).hide(); // Ensure the icon is not visible
        }
    });
    
});




function startHeartsFlowingEffect() {
    let containerWidth = $('#side-menu-right').width();
    let containerHeight = $('#side-menu-right').height();
    // Calculate the bottom position of the title container relative to the side-menu-right container
    let titleBottomPosition = $('#sidebar-title-container').position().top + $('#sidebar-title-container').outerHeight();
    let heartsCount = 20; // Number of hearts for the effect

    for (let i = 0; i < heartsCount; i++) {
        // Create a heart element with initial properties
        let heart = $('<i class="fas fa-heart heart"></i>').css({
            position: 'absolute',
            top: titleBottomPosition + 250 + 'px', // Start from the bottom of the title container
            left: Math.random() * containerWidth + 'px', // Random horizontal start position
            opacity: 0, // Start fully transparent
            fontSize: '25px', // Adjust size as needed
            color: 'red' // Heart color
        });

        // Append the heart to the side menu
        $('#side-menu-right').append(heart);

        // Animate the heart towards the bottom
        gsap.fromTo(heart, {
            y: 0,
            opacity: 1
        }, {
            y: containerHeight - titleBottomPosition, // Adjust the end position based on title position
            opacity: 0,
            duration: 2 + Math.random() * 2, // Randomize duration for variation
            ease: 'power1.inOut',
            onComplete: function() {
                $(this.targets()).remove(); // Remove the heart after animation completes
            }
        });
    }
}


function animateHeartBurstWithParticles() {
    let heart = $('#sidebar-favorite-icon');
   

    // Heart animation sequence
    let tl = gsap.timeline();

    tl.to(heart, { scale: 1.5, duration: 0.5, ease: "elastic.out(1, 0.3)" })
      .to(heart, { rotation: 15, yoyo: true, repeat: 3, duration: 0.1, ease: "linear" })
      .to(heart, { rotation: 0, duration: 0.1 })
      .to(heart, { scale: 2, duration: 0.1, ease: "power1.in" })
      // Only call createParticles here, remove onComplete from the timeline itself
      .add(createParticles, "-=0.1") // Add particles at the end of scaling up
      .to(heart, { scale: 1, duration: 0.3, ease: "elastic.out(1, 0.3)" });

    function createParticles() {
        let colors = ['red', 'pink', 'white', 'green', 'orange', 'blue']; // Array of colors for particles
        for (let i = 0; i < 60; i++) { // Increase number of particles
            let color = colors[Math.floor(Math.random() * colors.length)]; // Random color selection
            let particle = $('<div class="particle"></div>').css({
                position: 'absolute',
                top: heart.position().top + heart.width() / 1, // Center on heart
                left: heart.position().left + heart.height() / 1, // Center on heart
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: color,
            });

            $('#side-menu-right').append(particle);

            // Animate particle
            gsap.to(particle, {
                x: (Math.random() - 0.5) * 600, // Wider spread
                y: (Math.random() - 0.5) * 600, // Wider spread
                opacity: 0,
                duration: 1 + Math.random(), // Random duration
                ease: "power1.out",
                onComplete: function() {
                    $(this.targets()).remove(); // Remove particle after animation
                }
            });
        }
    }
}


document.addEventListener('DOMContentLoaded', function() {
    let loginForm = document.getElementById('loginForm');
    let loginError = document.getElementById('loginError');

    loginForm.onsubmit = function(event) {
        event.preventDefault();
        let formData = new FormData(loginForm);
        
        fetch(loginUrl, {  // Use the global variable here
            method: 'POST',
            body: formData
        }).then(response => response.json()).then(data => {
            if (data.success) {
                $('#loginModal').modal('hide');
                loginError.style.display = 'none';
                window.location.reload(true); // Or redirect to another page
            } else {
                loginError.textContent = data.message;
                loginError.style.display = 'block';
            }
        }).catch(error => {
            loginError.textContent = 'An error occurred. Please try again.';
            loginError.style.display = 'block';
        });
    };
});


document.addEventListener("DOMContentLoaded", function() {
    let popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    let popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
      return new bootstrap.Popover(popoverTriggerEl);
    });
  });
  

