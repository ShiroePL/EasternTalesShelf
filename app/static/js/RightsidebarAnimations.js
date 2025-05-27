let timeouts = {};
let globalTimeout;

export function initializeAnimations() {
    // Clear any existing timeouts
    Object.values(timeouts).forEach(clearTimeout);
    timeouts = {};
}

export function startAnimationSequence() {
    timeouts.cover = setTimeout(() => $('#sidebar-cover').fadeIn(1500), 100);
    timeouts.info = setTimeout(() => $('#sidebar-info').fadeIn(700), 600);
    timeouts.link = setTimeout(() => $('#sidebar-links').fadeIn(650), 800);
    timeouts.description = setTimeout(() => $('#sidebar-description').fadeIn(800), 900);
    timeouts.notes = setTimeout(() => $('#sidebar-notes').fadeIn(800), 900);
    timeouts.readmore = setTimeout(() => $('#sidebar-toggle').fadeIn(650), 1100);
    timeouts.externalLinks = setTimeout(() => $('#sidebar-external-links').fadeIn(750), 1300);
    timeouts.genres = setTimeout(() => $('#sidebar-genres').fadeIn(750), 1550);

    // Show the sidebar with Bootstrap styling
    $('#side-menu-right').addClass('active');

    // Handle 'Show Notes' visibility
    handleShowNotesVisibility();
    handleMangaUpdatesVisibility();
}

function handleMangaUpdatesVisibility() {
    const mangaUpdatesInfoElement = $('#mangaupdates-info');

    // Clear existing timeout if it exists
    if (timeouts?.mangaupdates_info) {
        clearTimeout(timeouts.mangaupdates_info);
    }

    // Check if the content is empty
    if ($('#mangaupdates-content').html().trim() === "") {
        mangaUpdatesInfoElement.hide();
    } else {
        timeouts.mangaupdates_info = setTimeout(() => {
            mangaUpdatesInfoElement.fadeIn(650);
        }, 730);
    }
}

function handleShowNotesVisibility() {
    let notesText = $('#sidebar-notes').text().trim();
    
    if (timeouts?.shownotes) {
        clearTimeout(timeouts.shownotes);
    }

    if (notesText === "None") {
        $('#sidebar-shownotes').hide();
    } else {
        timeouts.shownotes = setTimeout(() => {
            $('#sidebar-shownotes').fadeIn(650);
        }, 1100);
    }
}

export function closeRightSideMenu() {
    $('#side-menu-right').removeClass('active');
}

export function animateHeartBurstWithParticles() {
    let heart = $('#sidebar-favorite-icon');
   

    // Heart animation sequence
    let tl = gsap.timeline();

    tl.to(heart, { scale: 1.5, duration: 0.5, ease: "elastic.out(1, 0.3)" })
      .to(heart, { rotation: 15, yoyo: true, repeat: 3, duration: 0.1, ease: "linear" })
      .to(heart, { rotation: 0, duration: 0.1 })
      .to(heart, { scale: 2, duration: 0.1, ease: "power1.in" })
      // Only call createParticles here, remove onComplete from the timeline itself
      .add(createParticles, "-=0.05") // Add particles at the end of scaling up
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
                x: (Math.random() - 0.5) * 500, // Wider spread
                y: (Math.random() - 0.5) * 500, // Wider spread
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

export function startHeartsFlowingEffect() {
    let containerWidth = $('#side-menu-right').width();
    let containerHeight = $('#side-menu-right').height();
    // Calculate the bottom position of the title container relative to the side-menu-right container
    let titleBottomPosition = $('#sidebar-title-container').position().top + $('#sidebar-title-container').outerHeight();
    
    // Create or find the bottom marker element
    let bottomMarker = $('#hearts-bottom-marker');
    if (bottomMarker.length === 0) {
        // Create a marker element at the bottom of the rightside menu
        bottomMarker = $('<div id="hearts-bottom-marker"></div>').css({
            position: 'absolute',
            bottom: '10px', // 10px from the bottom of the rightside menu
            width: '1px',
            height: '1px',
            visibility: 'hidden',
            pointerEvents: 'none', // Don't interfere with interactions
            zIndex: -1 // Behind everything
        });
        $('#side-menu-right').append(bottomMarker);
    }
    
    // Calculate the fall distance using the marker
    let markerPosition = bottomMarker.position().top;
    let maxFallDistance = markerPosition - titleBottomPosition - 250; // Distance to the marker
    
    let heartsCount = 20; // Number of hearts for the effect

    for (let i = 0; i < heartsCount; i++) {
        // Create a heart element with initial properties
        let heart = $('<i class="fas fa-heart heart"></i>').css({
            position: 'absolute',
            top: titleBottomPosition + 250 + 'px', // Start from the bottom of the title container
            left: Math.random() * containerWidth + 'px', // Random horizontal start position
            opacity: 0, // Start fully transparent
            fontSize: '25px', // Adjust size as needed
            color: 'red', // Heart color
            zIndex: 1000, // Ensure they're on top
            pointerEvents: 'none', // Don't interfere with interactions
            width: '25px', // Fixed width
            height: '25px', // Fixed height
            overflow: 'hidden' // Prevent any overflow
        });

        // Append the heart to the side menu
        $('#side-menu-right').append(heart);

        // Animate the heart towards the bottom marker
        gsap.fromTo(heart, {
            y: 0,
            opacity: 1
        }, {
            y: Math.max(maxFallDistance, 200), // Ensure hearts fall a reasonable distance
            opacity: 0,
            duration: 2 + Math.random() * 2, // Randomize duration for variation
            ease: 'power1.inOut',
            onComplete: function() {
                $(this.targets()).remove(); // Remove the heart after animation completes
            }
        });
    }
}

export function animateRereadIcon(selector) {
    $(selector).addClass('scale-up');
    setTimeout(function() {
        $(selector).removeClass('scale-up');
    }, 500); // Adjust timing if needed
}