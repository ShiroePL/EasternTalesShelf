/**
 * Mobile Responsive Functionality
 * Handles mobile-specific interactions for sidebars and navigation
 */

(function() {
    'use strict';
    
    let isMobile = window.innerWidth <= 768;
    let leftSidebarOpen = false;
    
    /**
     * Initialize mobile functionality
     */
    function initMobile() {
        updateMobileState();
        createMobileElements();
        attachEventListeners();
        
        // Update on window resize
        window.addEventListener('resize', debounce(handleResize, 250));
    }
    
    /**
     * Update mobile state based on window width
     */
    function updateMobileState() {
        isMobile = window.innerWidth <= 768;
    }
    
    /**
     * Create mobile-specific DOM elements
     */
    function createMobileElements() {
        // Create mobile filter toggle button if it doesn't exist
        if (!document.getElementById('mobile-filter-toggle')) {
            const filterButton = document.createElement('button');
            filterButton.id = 'mobile-filter-toggle';
            filterButton.innerHTML = '<i class="fas fa-filter"></i>';
            filterButton.setAttribute('aria-label', 'Toggle Filters');
            filterButton.setAttribute('title', 'Show Filters');
            document.body.appendChild(filterButton);
        }
        
        // Create backdrop for left sidebar if it doesn't exist
        if (!document.getElementById('left-sidebar-backdrop')) {
            const backdrop = document.createElement('div');
            backdrop.id = 'left-sidebar-backdrop';
            backdrop.setAttribute('aria-label', 'Close Filters');
            document.body.appendChild(backdrop);
        }
    }
    
    /**
     * Attach event listeners
     */
    function attachEventListeners() {
        // Mobile filter toggle button
        const filterButton = document.getElementById('mobile-filter-toggle');
        if (filterButton) {
            filterButton.addEventListener('click', toggleLeftSidebar);
        }
        
        // Left sidebar backdrop
        const backdrop = document.getElementById('left-sidebar-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', closeLeftSidebar);
        }
        
        // Close button on right sidebar - enhance for mobile
        const closeButton = document.getElementById('close-menu-icon');
        if (closeButton) {
            closeButton.addEventListener('click', closeRightSidebar);
        }
        
        // Prevent body scroll when sidebars are open on mobile
        const leftSidebar = document.getElementById('side-menu');
        const rightSidebar = document.getElementById('side-menu-right');
        
        if (leftSidebar) {
            observeSidebarState(leftSidebar, 'active', handleLeftSidebarStateChange);
        }
        
        if (rightSidebar) {
            observeSidebarState(rightSidebar, 'active', handleRightSidebarStateChange);
        }
    }
    
    /**
     * Toggle left sidebar (filters)
     */
    function toggleLeftSidebar() {
        const sidebar = document.getElementById('side-menu');
        const backdrop = document.getElementById('left-sidebar-backdrop');
        
        if (!sidebar || !backdrop) return;
        
        leftSidebarOpen = !leftSidebarOpen;
        
        if (leftSidebarOpen) {
            sidebar.classList.add('active');
            backdrop.classList.add('active');
            
            if (isMobile) {
                document.body.style.overflow = 'hidden';
            }
        } else {
            closeLeftSidebar();
        }
    }
    
    /**
     * Close left sidebar
     */
    function closeLeftSidebar() {
        const sidebar = document.getElementById('side-menu');
        const backdrop = document.getElementById('left-sidebar-backdrop');
        
        if (!sidebar || !backdrop) return;
        
        leftSidebarOpen = false;
        sidebar.classList.remove('active');
        backdrop.classList.remove('active');
        
        if (isMobile) {
            // Only restore scroll if right sidebar is also closed
            const rightSidebar = document.getElementById('side-menu-right');
            if (!rightSidebar || !rightSidebar.classList.contains('active')) {
                document.body.style.overflow = '';
            }
        }
    }
    
    /**
     * Close right sidebar
     */
    function closeRightSidebar() {
        const sidebar = document.getElementById('side-menu-right');
        
        if (!sidebar) return;
        
        sidebar.classList.remove('active');
        sidebar.classList.add('sidebar-hidden');
        sidebar.classList.remove('sidebar-visible');
        
        if (isMobile) {
            // Only restore scroll if left sidebar is also closed
            if (!leftSidebarOpen) {
                document.body.style.overflow = '';
            }
        }
    }
    
    /**
     * Handle left sidebar state changes
     */
    function handleLeftSidebarStateChange(isActive) {
        if (isMobile) {
            if (isActive) {
                document.body.style.overflow = 'hidden';
            } else {
                const rightSidebar = document.getElementById('side-menu-right');
                if (!rightSidebar || !rightSidebar.classList.contains('active')) {
                    document.body.style.overflow = '';
                }
            }
        }
    }
    
    /**
     * Handle right sidebar state changes
     */
    function handleRightSidebarStateChange(isActive) {
        if (isMobile) {
            if (isActive) {
                document.body.style.overflow = 'hidden';
                // Close left sidebar if open
                closeLeftSidebar();
            } else {
                if (!leftSidebarOpen) {
                    document.body.style.overflow = '';
                }
            }
        }
    }
    
    /**
     * Observe sidebar class changes
     */
    function observeSidebarState(element, className, callback) {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    const isActive = element.classList.contains(className);
                    callback(isActive);
                }
            });
        });
        
        observer.observe(element, {
            attributes: true,
            attributeFilter: ['class']
        });
    }
    
    /**
     * Handle window resize
     */
    function handleResize() {
        const wasMobile = isMobile;
        updateMobileState();
        
        // If switching from mobile to desktop, clean up mobile states
        if (wasMobile && !isMobile) {
            closeLeftSidebar();
            document.body.style.overflow = '';
        }
        
        // If switching from desktop to mobile and right sidebar is open, ensure proper mobile behavior
        if (!wasMobile && isMobile) {
            const rightSidebar = document.getElementById('side-menu-right');
            if (rightSidebar && rightSidebar.classList.contains('active')) {
                document.body.style.overflow = 'hidden';
            }
        }
    }
    
    /**
     * Debounce utility function
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    /**
     * Add swipe gesture support for closing sidebars
     */
    function initSwipeGestures() {
        let touchStartX = 0;
        let touchEndX = 0;
        let touchStartY = 0;
        let touchEndY = 0;
        
        const leftSidebar = document.getElementById('side-menu');
        const rightSidebar = document.getElementById('side-menu-right');
        
        function handleSwipe(element, closeCallback) {
            const swipeThreshold = 50;
            const velocityThreshold = 0.3;
            
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            const deltaTime = Date.now() - element._swipeStartTime;
            const velocity = Math.abs(deltaX) / deltaTime;
            
            // Only trigger swipe if horizontal movement is greater than vertical
            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                if (element === leftSidebar) {
                    // Swipe left to close left sidebar
                    if (deltaX < -swipeThreshold || velocity > velocityThreshold) {
                        closeCallback();
                    }
                } else if (element === rightSidebar) {
                    // Swipe right to close right sidebar
                    if (deltaX > swipeThreshold || velocity > velocityThreshold) {
                        closeCallback();
                    }
                }
            }
        }
        
        if (leftSidebar) {
            leftSidebar.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
                touchStartY = e.changedTouches[0].screenY;
                leftSidebar._swipeStartTime = Date.now();
            });
            
            leftSidebar.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                touchEndY = e.changedTouches[0].screenY;
                handleSwipe(leftSidebar, closeLeftSidebar);
            });
        }
        
        if (rightSidebar) {
            rightSidebar.addEventListener('touchstart', (e) => {
                touchStartX = e.changedTouches[0].screenX;
                touchStartY = e.changedTouches[0].screenY;
                rightSidebar._swipeStartTime = Date.now();
            });
            
            rightSidebar.addEventListener('touchend', (e) => {
                touchEndX = e.changedTouches[0].screenX;
                touchEndY = e.changedTouches[0].screenY;
                handleSwipe(rightSidebar, closeRightSidebar);
            });
        }
    }
    
    /**
     * Expose functions globally if needed
     */
    window.mobileResponsive = {
        toggleLeftSidebar,
        closeLeftSidebar,
        closeRightSidebar,
        isMobile: () => isMobile
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initMobile();
            initSwipeGestures();
        });
    } else {
        initMobile();
        initSwipeGestures();
    }
    
})();
