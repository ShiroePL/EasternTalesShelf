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
        currentActiveAnilistId = null;
    });

    // Ensure the event listener for the same title click includes logic to close the right side menu with a sliding animation
    let currentActiveAnilistId = null;

    $(document).on('click', '.grid-item', function() {
        let clickedAnilistId = $(this).data('anilist-id');
        
        let sideMenu = $('#side-menu-right');

        // Explicit check if 'active' class is present
        if (sideMenu.hasClass('active')) {

            if (currentActiveAnilistId === clickedAnilistId) {
                sideMenu.removeClass('active');
                currentActiveAnilistId = null; // Clear the active ID since we closed the menu
            } else {
                currentActiveAnilistId = clickedAnilistId; // Update to the new active ID
            }
        } else {
            
            sideMenu.addClass('active');
            currentActiveAnilistId = clickedAnilistId; // Set active ID
        }
        
    });
});
