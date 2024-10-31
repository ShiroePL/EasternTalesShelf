document.addEventListener('DOMContentLoaded', function() {
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

    // Add event listener for the new icon to close the right side menu with a sliding animation
    $(document).on('click', '#close-menu-icon', function() {
        $('#side-menu-right').removeClass('active');
    });

    // Ensure the event listener for the same title click includes logic to close the right side menu with a sliding animation
    let currentActiveAnilistId = null;

    $(document).on('click', '.grid-item', function() {
        let clickedAnilistId = $(this).data('anilist-id');
        console.log("Clicked AniList ID:", clickedAnilistId);

        let sideMenu = $('#side-menu-right');

        // Log the current classes to verify the state of the sideMenu element
        console.log("Current classes on sideMenu:", sideMenu.attr('class'));

        // Explicit check if 'active' class is present
        if (sideMenu.hasClass('active')) {
            console.log("Right side menu is already active, checking if we clicked the same item...");

            if (currentActiveAnilistId === clickedAnilistId) {
                console.log("Closing right side menu, matching ID:", clickedAnilistId);
                sideMenu.removeClass('active');
                currentActiveAnilistId = null; // Clear the active ID since we closed the menu
            } else {
                console.log("Switching side menu to new ID:", clickedAnilistId);
                currentActiveAnilistId = clickedAnilistId; // Update to the new active ID
            }
        } else {
            console.log("Right side menu is not active. Adding 'active' class now.");
            sideMenu.addClass('active');
            currentActiveAnilistId = clickedAnilistId; // Set active ID
        }

        // Additional debug - Check again after making changes to the class list
        setTimeout(() => {
            console.log("After click action - Current classes on sideMenu:", sideMenu.attr('class'));
        }, 100); // Small delay to ensure the class list is updated and logged after changes
    });



    
});
