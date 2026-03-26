# Mobile Layout Visual Reference

## Desktop Layout (> 992px)
```
┌─────────────────────────────────────────────────────────────────┐
│                         NAVBAR (Full Width)                      │
├──────────┬────────────────────────────────────────┬──────────────┤
│          │                                        │              │
│  LEFT    │         MANGA GRID                     │    RIGHT     │
│ SIDEBAR  │   ┌────┐ ┌────┐ ┌────┐ ┌────┐        │   SIDEBAR    │
│          │   │ 1  │ │ 2  │ │ 3  │ │ 4  │        │              │
│ Filters  │   └────┘ └────┘ └────┘ └────┘        │   Details    │
│ Sorting  │   ┌────┐ ┌────┐ ┌────┐ ┌────┐        │   (hidden    │
│ Search   │   │ 5  │ │ 6  │ │ 7  │ │ 8  │        │    until     │
│          │   └────┘ └────┘ └────┘ └────┘        │   clicked)   │
│ 250px    │   (Auto-fill columns)                 │    250px     │
│          │                                        │              │
└──────────┴────────────────────────────────────────┴──────────────┘
```

## Tablet Layout (768px - 992px)
```
┌─────────────────────────────────────────────────────────┐
│                NAVBAR (Full Width)                       │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  LEFT    │         MANGA GRID (3 columns)               │
│ SIDEBAR  │   ┌────┐ ┌────┐ ┌────┐                      │
│          │   │ 1  │ │ 2  │ │ 3  │                      │
│ 200px    │   └────┘ └────┘ └────┘                      │
│          │   ┌────┐ ┌────┐ ┌────┐                      │
│          │   │ 4  │ │ 5  │ │ 6  │                      │
│          │   └────┘ └────┘ └────┘                      │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘

When clicking manga → Right sidebar slides in as overlay
```

## Mobile Layout (< 768px)
```
┌──────────────────────────────┐
│      NAVBAR (Full Width)     │
├──────────────────────────────┤
│                              │
│     MANGA GRID (2 cols)      │
│   ┌──────┐   ┌──────┐        │
│   │  1   │   │  2   │        │
│   └──────┘   └──────┘        │
│   ┌──────┐   ┌──────┐        │
│   │  3   │   │  4   │        │
│   └──────┘   └──────┘        │
│   ┌──────┐   ┌──────┐        │
│   │  5   │   │  6   │        │
│   └──────┘   └──────┘        │
│                              │
│                    ┌────┐    │
│                    │ 🔍 │◄── Filter Button
│                    └────┘    │
└──────────────────────────────┘
```

## Mobile - Filter Open
```
┌──────────────────────────────┐
│      NAVBAR (Full Width)     │
├─────────┬────────────────────┤
│         │░░░░░░░░░░░░░░░░░░░░│ ← Backdrop (tap to close)
│ LEFT    │░░░MANGA GRID░░░░░░░│
│ SIDEBAR │░░░(Dimmed)░░░░░░░░░│
│         │░░░░░░░░░░░░░░░░░░░░│
│ Search  │░░░░░░░░░░░░░░░░░░░░│
│ Filters │░░░░░░░░░░░░░░░░░░░░│
│ Sort    │░░░░░░░░░░░░░░░░░░░░│
│         │░░░░░░░░░░░░░░░░░░░░│
│ (Swipe  │░░░░░░░░░░░░░░░░░░░░│
│  left   │░░░░░░░░░░░░░░░░░░░░│
│  close) │░░░░░░░░░░░░░░░░░░░░│
│         │░░░░░░░░░░░░░░░░░░░░│
│ 85%     │       15%          │
└─────────┴────────────────────┘
```

## Mobile - Details Open
```
┌──────────────────────────────┐
│  ← Close                     │ ← Close button
│                              │
│   RIGHT SIDEBAR (Full)       │
│                              │
│   ┌────────────────────┐     │
│   │   Cover Image      │     │
│   └────────────────────┘     │
│                              │
│   Title: Manga Name          │
│   Score: 8.5                 │
│   Status: Reading            │
│   Chapters: 45/100           │
│                              │
│   [AniList] [Bato] [MAL]     │
│                              │
│   Description...             │
│                              │
│   (Swipe right to close)     │
│                              │
│   Full Screen Overlay        │
└──────────────────────────────┘
```

## Interaction Flow

### Opening Filters (Mobile)
1. User taps filter button (🔍)
2. Left sidebar slides in from left (300ms)
3. Backdrop fades in behind sidebar
4. Grid dims (pointer-events: none)
5. Body scroll locked

### Closing Filters (Mobile)
Options:
- Tap backdrop
- Swipe left on sidebar
- Filter selection auto-closes (optional)

### Opening Details (Mobile)
1. User taps manga grid item
2. Right sidebar slides in from right (300ms)
3. Full screen overlay
4. Body scroll locked
5. Close button prominent at top-left

### Closing Details (Mobile)
Options:
- Tap close button (←)
- Swipe right on sidebar
- Back button (browser)

## CSS Transition Details

```css
/* Left Sidebar */
transition: left 0.3s ease-in-out;
left: -100%;  /* Hidden */
left: 0;      /* Shown */

/* Right Sidebar */
transition: right 0.3s ease-in-out;
right: -100%; /* Hidden */
right: 0;     /* Shown */

/* Backdrop */
transition: opacity 0.3s ease-in-out;
opacity: 0;   /* Hidden */
opacity: 1;   /* Shown */
```

## Touch Gestures

### Swipe Thresholds
- **Distance**: 50px minimum swipe distance
- **Velocity**: 0.3 velocity threshold for quick swipes
- **Direction**: Must be primarily horizontal (deltaX > deltaY)

### Gesture Recognition
```
Left Sidebar:  Swipe Left  → Close
Right Sidebar: Swipe Right → Close
```

## Z-Index Layers

```
Layer Stack (bottom to top):
━━━━━━━━━━━━━━━━━━━━━━━━━━━
z-index: 1     - Main grid
z-index: 10    - Desktop sidebars
z-index: 1030  - Filter button
z-index: 1039  - Left sidebar backdrop
z-index: 1040  - Left sidebar
z-index: 1050  - Right sidebar
z-index: 1051  - Right close button
```

## Accessibility Features

- **Keyboard Navigation**: Tab order maintained
- **ARIA Labels**: aria-label on buttons
- **Focus Management**: Focus trap in open sidebars
- **Screen Readers**: Announce sidebar state changes
- **Touch Targets**: Minimum 44x44px (WCAG 2.1)
- **Color Contrast**: Maintains WCAG AA standards

## Performance Metrics

| Action | Target Time | Method |
|--------|-------------|--------|
| Sidebar Open | 300ms | CSS transform |
| Sidebar Close | 300ms | CSS transform |
| Backdrop Fade | 300ms | CSS opacity |
| Resize Handler | 250ms debounce | JavaScript |
| Swipe Detection | Immediate | Touch events |

## Browser Support

✅ Chrome Mobile 80+
✅ Safari iOS 12+
✅ Firefox Mobile 68+
✅ Samsung Internet 12+
✅ Edge Mobile 80+

## Common Viewport Sizes

| Device | Width | Columns | Sidebar |
|--------|-------|---------|---------|
| iPhone SE | 375px | 2 | Overlay |
| iPhone 12/13 | 390px | 2 | Overlay |
| iPhone Pro Max | 428px | 2 | Overlay |
| iPad Mini | 768px | 3 | Visible |
| iPad Pro | 1024px | Auto | Visible |
| Desktop HD | 1920px | Auto | Visible |
