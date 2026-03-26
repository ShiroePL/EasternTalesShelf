# Custom Dropdown Style Guide

This document provides the complete implementation details for the custom dropdown component used in TrackToon. Use this guide to replicate the same visual style and behavior in other projects.

## Overview

The custom dropdown is a fully styled, accessible select component with smooth animations, glassmorphism effects, and hover states. It features:

- ✨ Glassmorphism design with backdrop blur
- 🎨 Smooth transitions and animations
- ✓ Active state indicators
- 🎯 Click-outside-to-close functionality
- 📱 Responsive design
- 🌈 Theme-aware using CSS variables

---

## HTML Structure

```html
<div class="custom-backup-dropdown" id="yourDropdownId">
    <div class="custom-dropdown-selected" data-value="daily">
        <span class="dropdown-text">Daily</span>
        <span class="dropdown-arrow">▼</span>
    </div>
    <div class="custom-dropdown-options">
        <div class="custom-dropdown-option" data-value="disabled">Disabled</div>
        <div class="custom-dropdown-option" data-value="testing">Every 2 minutes (Testing)</div>
        <div class="custom-dropdown-option active" data-value="daily">Daily</div>
        <div class="custom-dropdown-option" data-value="weekly">Weekly</div>
        <div class="custom-dropdown-option" data-value="monthly">Monthly</div>
    </div>
</div>
```

### HTML Structure Notes:

1. **Root Container** (`.custom-backup-dropdown`):
   - Main wrapper with unique ID for JavaScript targeting
   - Contains both the selected display and options list

2. **Selected Display** (`.custom-dropdown-selected`):
   - Shows currently selected value
   - Has `data-value` attribute matching the active option
   - Contains text span and arrow indicator
   - Gets `.active` class when dropdown is open

3. **Options Container** (`.custom-dropdown-options`):
   - Hidden by default (opacity: 0, visibility: hidden)
   - Shows when `.show` class is added
   - Positioned absolutely below the selected element

4. **Individual Options** (`.custom-dropdown-option`):
   - Each has `data-value` attribute for identification
   - Active option has `.active` class and displays checkmark
   - Text content is what displays in the selected area when chosen

---

## CSS Styling

### Required CSS Variables

```css
:root {
  /* Primary brand colors */
  --primary-color: #2fafaf;
  --primary-hover: #26a0a0;
  
  /* Text colors */
  --text-color: #e4e6ea;
  
  /* Other variables used */
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.15);
}
```

### Complete CSS

```css
/* Main dropdown container */
.custom-backup-dropdown {
  position: relative;
  width: 100%;
  z-index: 10;
}

/* Ensure parent containers don't clip the dropdown */
.custom-backup-dropdown-parent {
  overflow: visible !important;
}

/* Selected/visible part of dropdown */
.custom-dropdown-selected {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

/* Hover state */
.custom-dropdown-selected:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(47, 175, 175, 0.4);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateY(-1px);
}

/* Active state (when dropdown is open) */
.custom-dropdown-selected.active {
  background: rgba(255, 255, 255, 0.15);
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(47, 175, 175, 0.2), 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: translateY(-1px);
}

/* Text inside selected */
.dropdown-text {
  flex: 1;
  text-align: left;
}

/* Arrow indicator */
.dropdown-arrow {
  font-size: 10px;
  color: var(--primary-color);
  transition: transform 0.3s ease;
  margin-left: 8px;
}

/* Rotate arrow when open */
.custom-dropdown-selected.active .dropdown-arrow {
  transform: rotate(180deg);
}

/* Options container (dropdown menu) */
.custom-dropdown-options {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(30, 41, 59, 0.95);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  opacity: 0;
  visibility: hidden;
  transform: translateY(-10px);
  transition: all 0.3s ease;
  z-index: 9999;
  margin-top: 4px;
  overflow: visible;
}

/* Show options when dropdown is open */
.custom-dropdown-options.show {
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

/* Individual option */
.custom-dropdown-option {
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  border-radius: 6px;
  margin: 2px 4px;
}

/* Option hover state */
.custom-dropdown-option:hover {
  background: rgba(47, 175, 175, 0.2);
  color: var(--primary-color);
  transform: translateX(2px);
}

/* Active option (currently selected) */
.custom-dropdown-option.active {
  background: rgba(47, 175, 175, 0.15);
  color: var(--primary-color);
  font-weight: 500;
}

/* Checkmark for active option */
.custom-dropdown-option.active::before {
  content: '✓';
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--primary-color);
  font-size: 11px;
}
```

---

## JavaScript Implementation

### Initialization Function

```javascript
/**
 * Initialize custom backup dropdowns
 * Call this after DOM is loaded
 */
function initializeCustomBackupDropdowns() {
  const dropdowns = document.querySelectorAll('.custom-backup-dropdown');
  
  dropdowns.forEach(dropdown => {
    const selected = dropdown.querySelector('.custom-dropdown-selected');
    const options = dropdown.querySelector('.custom-dropdown-options');
    const optionElements = dropdown.querySelectorAll('.custom-dropdown-option');
    
    if (!selected || !options || !optionElements.length) return;
    
    // Add click handler to toggle dropdown
    selected.addEventListener('click', (e) => {
      e.stopPropagation();
      
      // Close other dropdowns first
      document.querySelectorAll('.custom-backup-dropdown').forEach(otherDropdown => {
        if (otherDropdown !== dropdown) {
          const otherSelected = otherDropdown.querySelector('.custom-dropdown-selected');
          const otherOptions = otherDropdown.querySelector('.custom-dropdown-options');
          if (otherSelected && otherOptions) {
            otherSelected.classList.remove('active');
            otherOptions.classList.remove('show');
          }
        }
      });
      
      // Toggle current dropdown
      const isActive = selected.classList.contains('active');
      if (isActive) {
        selected.classList.remove('active');
        options.classList.remove('show');
      } else {
        selected.classList.add('active');
        options.classList.add('show');
      }
    });
    
    // Add option click handlers
    optionElements.forEach(option => {
      option.addEventListener('click', (e) => {
        e.stopPropagation();
        
        // Remove active class from all options
        optionElements.forEach(opt => opt.classList.remove('active'));
        
        // Add active class to clicked option
        option.classList.add('active');
        
        // Update selected display
        const textElement = selected.querySelector('.dropdown-text');
        if (textElement) {
          textElement.textContent = option.textContent;
        }
        
        // Update data-value attribute
        const value = option.getAttribute('data-value');
        selected.setAttribute('data-value', value);
        
        // Close dropdown
        selected.classList.remove('active');
        options.classList.remove('show');
        
        // Trigger change event for existing functionality
        const changeEvent = new CustomEvent('customDropdownChange', {
          detail: {
            value: value,
            text: option.textContent,
            dropdown: dropdown
          }
        });
        dropdown.dispatchEvent(changeEvent);
      });
    });
  });
  
  // Close dropdowns when clicking outside
  document.addEventListener('click', () => {
    document.querySelectorAll('.custom-backup-dropdown').forEach(dropdown => {
      const selected = dropdown.querySelector('.custom-dropdown-selected');
      const options = dropdown.querySelector('.custom-dropdown-options');
      if (selected && options) {
        selected.classList.remove('active');
        options.classList.remove('show');
      }
    });
  });
}
```

### Helper Functions

```javascript
/**
 * Set value for custom dropdown programmatically
 * @param {HTMLElement} dropdown - The dropdown container element
 * @param {string} value - The data-value to set as selected
 */
function setCustomDropdownValue(dropdown, value) {
  const selected = dropdown.querySelector('.custom-dropdown-selected');
  const options = dropdown.querySelectorAll('.custom-dropdown-option');
  const textElement = selected?.querySelector('.dropdown-text');
  
  if (!selected || !options.length || !textElement) return;
  
  // Remove active class from all options
  options.forEach(option => option.classList.remove('active'));
  
  // Find and activate the matching option
  const matchingOption = Array.from(options).find(option => 
    option.getAttribute('data-value') === value
  );
  
  if (matchingOption) {
    matchingOption.classList.add('active');
    textElement.textContent = matchingOption.textContent;
    selected.setAttribute('data-value', value);
  }
}

/**
 * Get current value from custom dropdown
 * @param {HTMLElement} dropdown - The dropdown container element
 * @returns {string} The current data-value
 */
function getCustomDropdownValue(dropdown) {
  const selected = dropdown.querySelector('.custom-dropdown-selected');
  return selected?.getAttribute('data-value') || '';
}
```

### Event Handling

```javascript
// Listen for dropdown changes
const myDropdown = document.getElementById('yourDropdownId');

if (myDropdown) {
  myDropdown.addEventListener('customDropdownChange', (e) => {
    const { value, text, dropdown } = e.detail;
    console.log(`Dropdown changed to: ${text} (${value})`);
    
    // Your custom logic here
    // For example, save to storage, trigger API call, etc.
  });
}
```

---

## Usage Example

### Complete Implementation

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    /* Include all CSS from above */
  </style>
</head>
<body>
  <!-- Dropdown HTML -->
  <div class="custom-backup-dropdown" id="frequencySelect">
    <div class="custom-dropdown-selected" data-value="daily">
      <span class="dropdown-text">Daily</span>
      <span class="dropdown-arrow">▼</span>
    </div>
    <div class="custom-dropdown-options">
      <div class="custom-dropdown-option" data-value="disabled">Disabled</div>
      <div class="custom-dropdown-option active" data-value="daily">Daily</div>
      <div class="custom-dropdown-option" data-value="weekly">Weekly</div>
    </div>
  </div>

  <script>
    // Include all JavaScript from above
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', () => {
      initializeCustomBackupDropdowns();
      
      // Example: Set value programmatically
      const dropdown = document.getElementById('frequencySelect');
      setCustomDropdownValue(dropdown, 'weekly');
      
      // Example: Listen for changes
      dropdown.addEventListener('customDropdownChange', (e) => {
        console.log('Selected:', e.detail.value);
      });
    });
  </script>
</body>
</html>
```

---

## Key Features Explained

### 1. **Glassmorphism Effect**
```css
background: rgba(255, 255, 255, 0.08);
backdrop-filter: blur(10px);
```
Creates a frosted glass appearance with semi-transparent background and blur effect.

### 2. **Smooth Animations**
```css
transition: all 0.3s ease;
transform: translateY(-1px);
```
All state changes (hover, active, show/hide) are animated smoothly.

### 3. **Focus Ring on Active**
```css
box-shadow: 0 0 0 3px rgba(47, 175, 175, 0.2), 0 4px 12px rgba(0, 0, 0, 0.2);
```
Creates an outer glow when dropdown is opened, improving visual feedback.

### 4. **Arrow Rotation**
```css
.custom-dropdown-selected.active .dropdown-arrow {
  transform: rotate(180deg);
}
```
Arrow flips when dropdown opens, providing clear visual indication.

### 5. **Click-Outside-to-Close**
```javascript
document.addEventListener('click', () => {
  // Close all dropdowns
});
```
Automatically closes dropdown when clicking anywhere outside.

### 6. **Custom Event System**
```javascript
new CustomEvent('customDropdownChange', { detail: { value, text, dropdown } })
```
Allows easy integration with existing code through event listeners.

---

## Customization Tips

### Change Colors
Replace these values in CSS:
```css
--primary-color: #2fafaf;  /* Change to your brand color */
rgba(47, 175, 175, 0.2)    /* Update all instances with your color */
```

### Adjust Sizing
```css
padding: 10px 12px;   /* Adjust dropdown height */
font-size: 13px;      /* Adjust text size */
border-radius: 8px;   /* Adjust corner roundness */
```

### Modify Animations
```css
transition: all 0.3s ease;     /* Change speed */
transform: translateY(-10px);  /* Change slide distance */
```

### Dark/Light Theme Support
Add theme-specific CSS variables:
```css
[data-theme="light"] {
  --dropdown-bg: rgba(0, 0, 0, 0.08);
  --dropdown-border: rgba(0, 0, 0, 0.15);
}

[data-theme="dark"] {
  --dropdown-bg: rgba(255, 255, 255, 0.08);
  --dropdown-border: rgba(255, 255, 255, 0.15);
}
```

---

## Browser Compatibility

- ✅ Chrome/Edge 88+
- ✅ Firefox 94+
- ✅ Safari 15.4+
- ⚠️ Older browsers may not support `backdrop-filter` (graceful degradation)

### Fallback for older browsers:
```css
.custom-dropdown-selected {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  
  /* Fallback without blur */
  @supports not (backdrop-filter: blur(10px)) {
    background: rgba(255, 255, 255, 0.15);
  }
}
```

---

## Accessibility Considerations

To make this dropdown more accessible, consider adding:

```html
<div class="custom-backup-dropdown" 
     id="frequencySelect" 
     role="combobox" 
     aria-expanded="false"
     aria-haspopup="listbox">
  <div class="custom-dropdown-selected" 
       data-value="daily"
       tabindex="0"
       aria-label="Backup frequency selector">
    <span class="dropdown-text">Daily</span>
    <span class="dropdown-arrow">▼</span>
  </div>
  <div class="custom-dropdown-options" role="listbox">
    <div class="custom-dropdown-option" 
         data-value="daily" 
         role="option" 
         aria-selected="true">Daily</div>
    <!-- More options... -->
  </div>
</div>
```

And keyboard support in JavaScript:
```javascript
selected.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    selected.click();
  }
});
```

---

## Troubleshooting

### Dropdown gets clipped by parent
Ensure parent containers have `overflow: visible`:
```css
.parent-container {
  overflow: visible !important;
}
```

### Z-index issues
The dropdown uses `z-index: 9999`. Adjust if needed:
```css
.custom-dropdown-options {
  z-index: 9999; /* Increase if still behind other elements */
}
```

### Backdrop blur not working
Some browsers require vendor prefixes:
```css
backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
```

---

## License

This component is part of the TrackToon project. Feel free to use and adapt for your own projects.
