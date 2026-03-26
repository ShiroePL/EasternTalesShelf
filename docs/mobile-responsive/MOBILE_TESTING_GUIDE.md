# Mobile Responsive Testing Guide

## Quick Start Testing

### Option 1: Chrome DevTools (Recommended for Development)

1. **Open DevTools**
   - Press `F12` or `Ctrl+Shift+I` (Windows/Linux)
   - Press `Cmd+Option+I` (Mac)

2. **Enable Device Toolbar**
   - Click the device icon or press `Ctrl+Shift+M`
   - Select a mobile device from dropdown (e.g., "iPhone 12 Pro")

3. **Test Responsive Breakpoints**
   ```
   375px  - iPhone SE (2 columns)
   390px  - iPhone 12/13 (2 columns)
   428px  - iPhone Pro Max (2 columns)
   768px  - iPad Mini (3 columns, left sidebar visible)
   1024px - iPad Pro (desktop layout)
   1920px - Desktop (full layout)
   ```

4. **Reload Page**
   - Press `F5` to see mobile layout

### Option 2: Real Device Testing

1. **Find your local IP**
   ```powershell
   ipconfig
   ```
   Look for IPv4 Address (e.g., 192.168.1.100)

2. **Access from phone**
   - Connect phone to same WiFi
   - Open browser on phone
   - Navigate to: `http://YOUR_IP:5000`
   - Example: `http://192.168.1.100:5000`

3. **Allow firewall if needed**
   ```powershell
   # Run as Administrator
   netsh advfirewall firewall add rule name="Flask Dev" dir=in action=allow protocol=TCP localport=5000
   ```

## Feature Testing Checklist

### ✅ Layout Tests

#### Mobile (< 768px)
- [ ] Grid shows exactly 2 columns
- [ ] Grid items maintain aspect ratio
- [ ] Main content spans full width
- [ ] Left sidebar hidden by default
- [ ] Right sidebar hidden by default
- [ ] Filter button visible in bottom-left corner
- [ ] No horizontal scrolling

#### Tablet (768px - 992px)
- [ ] Grid shows exactly 3 columns
- [ ] Left sidebar visible (200px)
- [ ] Right sidebar hidden until clicked
- [ ] Filter button hidden
- [ ] No horizontal scrolling

#### Desktop (> 992px)
- [ ] Grid auto-fills (4+ columns)
- [ ] Left sidebar visible (250px)
- [ ] Right sidebar visible when clicked (250px)
- [ ] Filter button hidden
- [ ] Original layout preserved

### ✅ Left Sidebar (Filters) Tests

#### Opening
- [ ] Click filter button → sidebar slides in from left
- [ ] Backdrop appears (dark overlay)
- [ ] Grid is dimmed/disabled
- [ ] Sidebar width is ~85% of screen
- [ ] Animation is smooth (300ms)
- [ ] Body scroll is locked

#### Closing
- [ ] Click backdrop → sidebar closes
- [ ] Swipe left → sidebar closes
- [ ] Animation is smooth
- [ ] Backdrop fades out
- [ ] Body scroll is restored
- [ ] Grid becomes interactive again

#### Functionality
- [ ] Search box works
- [ ] Filter checkboxes toggle
- [ ] Status filters work
- [ ] Country filters work
- [ ] Sort dropdown works
- [ ] Filters apply to grid correctly
- [ ] Counts update properly

### ✅ Right Sidebar (Details) Tests

#### Opening
- [ ] Click manga item → sidebar slides in from right
- [ ] Full screen overlay (100% width)
- [ ] Animation is smooth (300ms)
- [ ] Body scroll is locked
- [ ] Close button visible at top-left
- [ ] Left sidebar closes if open

#### Closing
- [ ] Click close button → sidebar closes
- [ ] Swipe right → sidebar closes
- [ ] Animation is smooth
- [ ] Body scroll is restored

#### Content
- [ ] Cover image loads and displays
- [ ] Title shows correctly
- [ ] Info text readable
- [ ] External links work
- [ ] Description expands/collapses
- [ ] Notes toggle works
- [ ] Side stories dropdown works (if present)
- [ ] All buttons are tappable

### ✅ Filter Button Tests

#### Visibility
- [ ] Visible on mobile (< 768px)
- [ ] Hidden on tablet (768-992px)
- [ ] Hidden on desktop (> 992px)

#### Position
- [ ] Fixed at bottom-left (20px from edges)
- [ ] Stays in place when scrolling
- [ ] Doesn't overlap content
- [ ] Above grid items (z-index correct)

#### Interaction
- [ ] Tap opens left sidebar
- [ ] Hover effect works (desktop testing)
- [ ] Icon is clear (filter icon)
- [ ] Touch target is adequate (56x56px)

### ✅ Touch Gesture Tests (Real Device Only)

#### Left Sidebar
- [ ] Swipe left from anywhere in sidebar → closes
- [ ] Swipe needs to be primarily horizontal
- [ ] Fast swipe (velocity) closes immediately
- [ ] Slow swipe needs 50px distance
- [ ] Vertical scrolling still works

#### Right Sidebar
- [ ] Swipe right from anywhere in sidebar → closes
- [ ] Swipe needs to be primarily horizontal
- [ ] Fast swipe (velocity) closes immediately
- [ ] Slow swipe needs 50px distance
- [ ] Vertical scrolling still works

### ✅ Resize/Orientation Tests

#### Portrait → Landscape
- [ ] Layout adjusts correctly
- [ ] Sidebars close if needed
- [ ] Grid recalculates columns
- [ ] No broken layout
- [ ] Smooth transition

#### Landscape → Portrait
- [ ] Layout adjusts correctly
- [ ] Mobile elements appear
- [ ] Grid shows 2 columns
- [ ] No broken layout

#### Mobile → Desktop (resize browser)
- [ ] Left sidebar appears in fixed position
- [ ] Right sidebar returns to 250px width
- [ ] Filter button disappears
- [ ] Backdrop disappears
- [ ] Body scroll restored
- [ ] Grid columns increase

#### Desktop → Mobile (resize browser)
- [ ] Left sidebar hides
- [ ] Right sidebar closes if open
- [ ] Filter button appears
- [ ] Grid shows 2 columns

### ✅ Grid Item Tests

#### Icons Scaling
- [ ] Bato icon visible and sized correctly
- [ ] AniList icon visible and sized correctly
- [ ] Score icon readable
- [ ] Heart icon (favorites) sized correctly
- [ ] Reread icon sized correctly
- [ ] Side stories icon sized correctly
- [ ] Download button sized correctly

#### Text Scaling
- [ ] Title text readable
- [ ] Title doesn't overflow
- [ ] Stats popup readable
- [ ] Font sizes appropriate

#### Interactions
- [ ] Tap manga → opens right sidebar
- [ ] Tap icons → triggers correct action
- [ ] Hover effects work (desktop)
- [ ] No accidental taps

### ✅ Scroll Behavior Tests

#### Body Scroll Lock
- [ ] Left sidebar open → body locked
- [ ] Right sidebar open → body locked
- [ ] Both closed → body scrollable
- [ ] Switching between sidebars → lock maintained
- [ ] Close all → lock released

#### Sidebar Scrolling
- [ ] Left sidebar scrolls when content overflows
- [ ] Right sidebar scrolls when content overflows
- [ ] Smooth scrolling in sidebars
- [ ] No bounce scroll issues (iOS)

### ✅ Performance Tests

#### Animation Smoothness
- [ ] Sidebar slide-in at 60fps
- [ ] Backdrop fade at 60fps
- [ ] No jank during transitions
- [ ] Resize is debounced (not laggy)

#### Loading
- [ ] Initial load is fast
- [ ] Filter button appears immediately
- [ ] No FOUC (flash of unstyled content)
- [ ] Images lazy load properly

### ✅ Accessibility Tests

#### Keyboard Navigation (Desktop)
- [ ] Tab through elements works
- [ ] Enter opens/closes sidebars
- [ ] Escape closes sidebars
- [ ] Focus visible on all elements

#### Screen Reader (if available)
- [ ] Filter button announces correctly
- [ ] Sidebar state changes announced
- [ ] Form labels read correctly
- [ ] Buttons have proper labels

#### Touch Targets
- [ ] All buttons at least 44x44px
- [ ] Adequate spacing between tap targets
- [ ] No accidental taps

### ✅ Browser Compatibility

Test on multiple browsers:
- [ ] Chrome Mobile
- [ ] Safari iOS
- [ ] Firefox Mobile
- [ ] Samsung Internet
- [ ] Edge Mobile

## Common Issues & Solutions

### Issue: Filter button not appearing
**Check:**
1. Screen width is < 768px
2. JavaScript loaded without errors (check console)
3. CSS imported correctly
4. Element not hidden by other styles

**Solution:**
```javascript
// Open console and check:
window.mobileResponsive.isMobile()  // Should return true on mobile
document.getElementById('mobile-filter-toggle')  // Should exist
```

### Issue: Sidebar not sliding
**Check:**
1. `.active` class being applied
2. CSS transitions not disabled
3. No conflicting styles
4. JavaScript not throwing errors

**Solution:**
```javascript
// Force open for testing:
document.getElementById('side-menu').classList.add('active')
document.getElementById('left-sidebar-backdrop').classList.add('active')
```

### Issue: Backdrop not working
**Check:**
1. Element exists in DOM
2. Z-index is correct (1039)
3. Event listener attached
4. Positioned correctly

**Solution:**
```javascript
// Check in console:
document.getElementById('left-sidebar-backdrop')  // Should exist
// Should see click handler in Elements > Event Listeners
```

### Issue: Swipe gestures not working
**Check:**
1. Testing on real device (not simulator)
2. Touch events supported
3. No other touch handlers conflicting
4. Swipe distance/velocity adequate

**Solution:**
```javascript
// Check touch support:
'ontouchstart' in window  // Should be true
```

### Issue: Body scroll not locking
**Check:**
1. `document.body.style.overflow` is 'hidden'
2. Not overridden by other styles
3. iOS-specific scroll issues

**Solution:**
```css
/* May need iOS-specific fix: */
body.scroll-locked {
    position: fixed;
    width: 100%;
    overflow: hidden;
}
```

### Issue: Layout breaks on orientation change
**Check:**
1. Viewport meta tag present
2. Resize handler working
3. No fixed heights breaking layout

**Solution:**
```javascript
// Trigger manual update:
window.dispatchEvent(new Event('resize'))
```

## Testing Tools

### Browser DevTools
- Chrome DevTools (best for mobile simulation)
- Firefox Responsive Design Mode
- Safari Web Inspector

### Real Device Testing
- BrowserStack (cloud devices)
- Physical devices (recommended)

### Performance
- Chrome Lighthouse (Performance score)
- Chrome DevTools Performance tab
- Frame rate monitoring

### Accessibility
- Chrome DevTools Accessibility tab
- Lighthouse Accessibility audit
- Screen reader testing (VoiceOver, TalkBack)

## Quick Debug Commands

Open browser console and run:

```javascript
// Check mobile state
window.mobileResponsive.isMobile()

// Force open left sidebar
window.mobileResponsive.toggleLeftSidebar()

// Force close all sidebars
window.mobileResponsive.closeLeftSidebar()
window.mobileResponsive.closeRightSidebar()

// Check if elements exist
console.log({
    filterButton: !!document.getElementById('mobile-filter-toggle'),
    backdrop: !!document.getElementById('left-sidebar-backdrop'),
    leftSidebar: !!document.getElementById('side-menu'),
    rightSidebar: !!document.getElementById('side-menu-right')
})

// Check current classes
console.log({
    leftActive: document.getElementById('side-menu').classList.contains('active'),
    rightActive: document.getElementById('side-menu-right').classList.contains('active'),
    backdropActive: document.getElementById('left-sidebar-backdrop').classList.contains('active')
})
```

## Automated Testing (Future)

Consider adding:
```javascript
// Cypress test example
describe('Mobile Layout', () => {
    it('shows 2 columns on mobile', () => {
        cy.viewport('iphone-x')
        cy.get('#manga-grid-container')
            .should('have.css', 'grid-template-columns', 'repeat(2, 1fr)')
    })
    
    it('opens filter sidebar', () => {
        cy.get('#mobile-filter-toggle').click()
        cy.get('#side-menu').should('have.class', 'active')
    })
})
```

## Sign-off Checklist

Before considering mobile implementation complete:

- [ ] All layout tests pass
- [ ] All interaction tests pass
- [ ] Tested on at least 3 real devices
- [ ] Tested on at least 3 browsers
- [ ] Performance is acceptable (60fps)
- [ ] No console errors
- [ ] Accessibility basics covered
- [ ] Documentation complete
- [ ] Team has reviewed

## Next Steps After Testing

1. **Gather user feedback** from mobile users
2. **Monitor analytics** for mobile usage patterns
3. **Track issues** reported by users
4. **Iterate** based on feedback
5. **Consider PWA** features if mobile adoption is high
