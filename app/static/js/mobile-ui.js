/**
 * Mobile UI Enhancements
 * Handles auto-hiding navbar and bottom navigation interactions
 */

document.addEventListener('DOMContentLoaded', function() {
    initAutoHidingNavbar();
    initMobileBottomNav();
});

/**
 * Initialize auto-hiding navbar on scroll
 */
function initAutoHidingNavbar() {
    let lastScrollTop = 0;
    const navbar = document.querySelector('.navbar');
    const scrollThreshold = 10; // Minimum scroll amount to trigger change
    
    if (!navbar) return;
    
    window.addEventListener('scroll', function() {
        // Only apply on mobile/tablet devices
        if (window.innerWidth > 992) {
            navbar.style.transform = 'translateY(0)';
            return;
        }
        
        let scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Make sure we're scrolling more than the threshold
        if (Math.abs(lastScrollTop - scrollTop) <= scrollThreshold) return;
        
        if (scrollTop > lastScrollTop && scrollTop > 60) {
            // Scrolling DOWN - Hide navbar
            navbar.style.transform = 'translateY(-100%)';
        } else {
            // Scrolling UP - Show navbar
            navbar.style.transform = 'translateY(0)';
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop; // For Mobile or negative scrolling
    }, { passive: true });
}

/**
 * Initialize mobile bottom navigation interactions
 */
function initMobileBottomNav() {
    const filterBtn = document.getElementById('mobile-nav-filters');
    const detailsBtn = document.getElementById('mobile-nav-details');
    
    const leftSidebar = document.getElementById('side-menu');
    const rightSidebar = document.getElementById('side-menu-right');
    const leftBackdrop = document.getElementById('left-sidebar-backdrop');
    
    if (!filterBtn || !detailsBtn) return;
    
    // Toggle Left Sidebar (Filters)
    filterBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        
        // Close right sidebar if open
        if (rightSidebar && rightSidebar.classList.contains('active')) {
            rightSidebar.classList.remove('active');
            detailsBtn.classList.remove('active');
        }
        
        // Toggle left sidebar
        if (leftSidebar) {
            leftSidebar.classList.toggle('active');
            this.classList.toggle('active');
            
            // Toggle backdrop
            if (leftBackdrop) {
                leftBackdrop.classList.toggle('active');
            }
        }
    });
    
    // Toggle Right Sidebar (Details)
    detailsBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        
        // Close left sidebar if open
        if (leftSidebar && leftSidebar.classList.contains('active')) {
            leftSidebar.classList.remove('active');
            filterBtn.classList.remove('active');
            
            if (leftBackdrop) {
                leftBackdrop.classList.remove('active');
            }
        }
        
        // Toggle right sidebar
        if (rightSidebar) {
            // If we're opening it and no manga is selected, we might want to show a message
            // But for now just toggle it
            
            // Check if right sidebar is currently hidden via class (from RightSidebarMain.js logic)
            if (rightSidebar.classList.contains('sidebar-hidden')) {
                rightSidebar.classList.remove('sidebar-hidden');
                rightSidebar.classList.add('sidebar-visible');
            }
            
            rightSidebar.classList.toggle('active');
            this.classList.toggle('active');
        }
    });
    
    // Close sidebars when clicking outside (on backdrop)
    if (leftBackdrop) {
        leftBackdrop.addEventListener('click', function() {
            if (leftSidebar) leftSidebar.classList.remove('active');
            if (filterBtn) filterBtn.classList.remove('active');
            this.classList.remove('active');
        });
    }
    
    // Close right sidebar when clicking close button (if it exists)
    const closeRightBtn = document.getElementById('close-menu-icon');
    if (closeRightBtn) {
        closeRightBtn.addEventListener('click', function() {
            if (rightSidebar) rightSidebar.classList.remove('active');
            if (detailsBtn) detailsBtn.classList.remove('active');
        });
    }
    
    // Listen for clicks on grid items to automatically activate the details button
    document.addEventListener('click', function(e) {
        const gridItem = e.target.closest('.grid-item');
        if (gridItem) {
            // A grid item was clicked, so details are being shown
            // Highlight the details button
            if (detailsBtn) detailsBtn.classList.add('active');
            if (filterBtn) filterBtn.classList.remove('active');
            
            // On mobile, we might want to auto-open the right sidebar
            if (window.innerWidth <= 992 && rightSidebar) {
                rightSidebar.classList.add('active');
            }
        }
    });
}
