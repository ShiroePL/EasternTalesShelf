# Requirements Document

## Introduction

This feature adds a sorting/ordering capability to the left menu of the manga application. Users will be able to sort their manga list by different criteria, starting with sorting by score in descending order (highest scores first). The sorting option will be presented as a dropdown list that expands when clicked.

## Requirements

### Requirement 1

**User Story:** As a user, I want to access sorting options from the left menu, so that I can organize my manga list according to my preferences.

#### Acceptance Criteria

1. WHEN the user views the left menu THEN the system SHALL display a "Sort by" or "Order by" option
2. WHEN the user clicks on the sorting option THEN the system SHALL display a dropdown list of available sorting criteria
3. WHEN the user clicks outside the dropdown THEN the system SHALL close the dropdown list

### Requirement 2

**User Story:** As a user, I want to sort my manga list by score, so that I can see my highest-rated manga at the top of the list.

#### Acceptance Criteria

1. WHEN the user opens the sorting dropdown THEN the system SHALL display "Sort by Score" as an available option
2. WHEN the user selects "Sort by Score" THEN the system SHALL reorder the manga list with scores of 10 at the top
3. WHEN sorting by score is applied THEN the system SHALL arrange manga in descending order (10, 9, 8, 7, etc.)
4. WHEN manga have the same score THEN the system SHALL maintain their relative order or apply a secondary sort criterion

### Requirement 3

**User Story:** As a user, I want visual feedback when a sorting option is active, so that I know which sorting method is currently applied.

#### Acceptance Criteria

1. WHEN a sorting option is selected THEN the system SHALL visually indicate the active sorting method in the dropdown
2. WHEN a sorting option is active THEN the system SHALL update the left menu to show the current sort selection