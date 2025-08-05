# Implementation Plan

- [x] 1. Add sort dropdown HTML to left sidebar





  - Modify `templates/components/_left_sidebar.html` to include the sort dropdown section
  - Add Bootstrap dropdown with "Sort by Score" option and default state
  - Position the dropdown after "Other Options" section and before the menu image
  - _Requirements: 1.1, 1.2_

- [x] 2. Implement core sorting functionality in JavaScript





  - Extend `static/js/filters.js` with sorting functions
  - Create `initializeSorting()` function to set up event listeners and initial state
  - Implement `applySorting(sortType)` function to handle sort operations
  - Add global variable `window.currentSortType` to track active sort state
  - _Requirements: 2.2, 2.3_

- [x] 3. Implement score-based sorting algorithm





  - Create `sortByScore(items)` function that sorts manga items by score in descending order
  - Handle secondary sorting by title for items with identical scores
  - Implement logic to place unscored items at the end of the list
  - Add error handling for invalid or missing score data attributes
  - _Requirements: 2.2, 2.3, 2.4_

- [x] 4. Add DOM manipulation for reordering manga grid





  - Implement DOM reordering logic using `appendChild()` method
  - Ensure all existing data attributes and event listeners are preserved
  - Add function to collect and sort `.grid-item` elements from the manga grid
  - _Requirements: 2.2, 2.3_

- [x] 5. Implement dropdown UI state management





  - Create `updateSortDropdownText(sortType)` function to update dropdown button text
  - Add event listeners for dropdown item clicks
  - Implement visual feedback to show active sort option in dropdown
  - _Requirements: 3.1, 3.2_

- [x] 6. Integrate sorting with existing filter system





  - Modify `filterEntries()` function to reapply sorting after filtering
  - Ensure sorting state persists when filters are changed
  - Add sorting initialization to the existing DOMContentLoaded event listener
  - Test integration with all existing filter types (status, country, favorites, etc.)
  - _Requirements: 2.2, 2.3_

- [x] 7. Add CSS styling for sort dropdown





  - Add CSS rules to ensure dropdown matches existing sidebar dark theme
  - Style dropdown items with proper hover states and active indicators
  - Ensure responsive behavior and proper spacing within sidebar layout
  - _Requirements: 3.1, 3.2_

- [ ] 8. Test sorting functionality with various data scenarios
  - Create test cases for mixed scored/unscored manga collections
  - Test sorting behavior with identical scores
  - Verify sorting works correctly with empty manga grid
  - Test integration with existing filtering functionality
  - _Requirements: 2.2, 2.3, 2.4_