# Design Document

## Overview

The left menu sorting feature will add a dropdown-based sorting mechanism to the existing left sidebar (`_left_sidebar.html`). The feature will integrate with the current filtering system in `filters.js` and extend the manga grid display functionality. The sorting will be implemented as a client-side JavaScript feature that reorders the existing manga grid items based on the selected criteria.

## Architecture

The sorting feature will follow the existing architecture patterns:

- **Frontend**: HTML template modifications in `_left_sidebar.html`
- **JavaScript**: Extension of the existing `filters.js` module
- **Styling**: CSS additions to maintain consistency with the current dark theme
- **Integration**: Works alongside existing filtering functionality without conflicts

## Components and Interfaces

### 1. HTML Components

#### Sort Dropdown Component
- Location: `templates/components/_left_sidebar.html`
- Structure: Bootstrap dropdown with sort options
- Positioning: Added after the "Other Options" section, before the menu image

```html
<h5>Sort By</h5>
<div class="dropdown mb-3">
    <button class="btn btn-secondary dropdown-toggle w-100" type="button" id="sortDropdown" data-bs-toggle="dropdown">
        <i class="fas fa-sort"></i> Default Order
    </button>
    <ul class="dropdown-menu dropdown-menu-dark w-100">
        <li><a class="dropdown-item" href="#" data-sort="default">Default Order</a></li>
        <li><a class="dropdown-item" href="#" data-sort="score">Sort by Score</a></li>
    </ul>
</div>
```

### 2. JavaScript Components

#### Sort Manager Module
- Location: Extension of `static/js/filters.js`
- Responsibilities:
  - Handle sort dropdown interactions
  - Implement sorting algorithms
  - Update UI state
  - Integrate with existing filter system

#### Core Functions
```javascript
// New functions to add to filters.js
function initializeSorting()
function applySorting(sortType)
function sortByScore(items)
function updateSortDropdownText(sortType)
```

### 3. Data Flow

1. User clicks sort dropdown → Bootstrap dropdown opens
2. User selects "Sort by Score" → Event listener triggers
3. `applySorting('score')` function called
4. Manga grid items collected and sorted by score attribute
5. DOM reordered with sorted items
6. Dropdown text updated to reflect active sort
7. Existing filters reapplied to maintain filter state

## Data Models

### Manga Grid Item Attributes
The sorting will utilize existing data attributes on `.grid-item` elements:

- `data-score`: User's score for the manga (1-10 or empty)
- `data-title`: Manga title (for secondary sorting)
- `data-user-status`: Current reading status
- Other existing attributes remain unchanged

### Sort State Management
```javascript
window.currentSortType = 'default'; // Global variable to track active sort
```

## Implementation Details

### 1. Score Sorting Algorithm
- Primary sort: Score (descending, 10 → 1)
- Secondary sort: Title (ascending, A → Z) for items with same score
- Unscored items (empty/null scores) placed at the end
- Maintains relative order for items with identical scores and titles

### 2. DOM Manipulation Strategy
- Collect all `.grid-item` elements
- Sort array based on data attributes
- Reorder DOM elements using `appendChild()` method
- Preserve all existing attributes and event listeners

### 3. Integration with Existing Filters
- Sorting applied after filtering
- Filter changes trigger re-sort if sort is active
- Sort state persists through filter operations

## Error Handling

### Invalid Score Values
- Non-numeric scores treated as unscored (placed at end)
- Missing `data-score` attributes handled gracefully
- Malformed data attributes logged but don't break functionality

### DOM Element Issues
- Missing grid container handled with early return
- Empty manga grid displays appropriate message
- Sort dropdown disabled if no sortable items present

### Bootstrap Integration
- Fallback behavior if Bootstrap dropdown fails to initialize
- Manual dropdown toggle implementation as backup
- Graceful degradation for older browsers

## Testing Strategy

### Unit Testing Approach
1. **Sort Function Testing**
   - Test score sorting with various score combinations
   - Test secondary title sorting
   - Test handling of unscored items
   - Test empty grid scenarios

2. **Integration Testing**
   - Test sorting with active filters
   - Test filter changes with active sorting
   - Test multiple sort operations in sequence

3. **UI Testing**
   - Test dropdown interaction
   - Test visual feedback updates
   - Test responsive behavior

### Test Data Scenarios
- Mixed scored/unscored manga
- Identical scores with different titles
- Empty manga grid
- Single manga item
- All manga with same score

## Performance Considerations

### Optimization Strategies
- Sort operations only on user interaction (not automatic)
- Reuse existing DOM elements instead of recreation
- Minimal DOM queries using cached selectors
- Debouncing for rapid sort changes (if needed)

### Scalability
- Current implementation suitable for typical manga collections (100-1000 items)
- DOM manipulation approach efficient for client-side sorting
- No server-side requests required for sorting operations

## Visual Design

### Styling Consistency
- Dropdown matches existing sidebar styling (dark theme)
- Icons consistent with current Font Awesome usage
- Spacing follows existing sidebar section patterns
- Hover states match other interactive elements

### User Experience
- Clear visual indication of active sort in dropdown text
- Smooth transitions for reordered items (if performance allows)
- Intuitive icon usage (sort icon for dropdown button)
- Accessible keyboard navigation support