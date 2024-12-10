document.addEventListener('DOMContentLoaded', function() {
    // Fetch the saved color settings and apply them on page load
    setTimeout(() => {
        fetchAndApplySettings();
    }, 100)
    

    function fetchAndApplySettings() {
        fetch('/get_color_settings')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Unauthorized');
                }
                return response.json();
            })
            .then(data => {
                console.log("Loaded color settings from server:", data);
                applyColorSettings(data);
                updateColorCircles(data);
                document.body.style.visibility = 'visible';
            })
            .catch(error => {
                console.error('Error loading color settings:', error);
                applyDefaultColorSettings();
                updateColorCircles();
                document.body.style.visibility = 'visible';
            });
    }
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Color Circles Click Event
    var colorCircles = document.querySelectorAll('.color-circle');
    var individualColorPickerModal = new bootstrap.Modal(document.getElementById('individualColorPickerModal'));

    colorCircles.forEach(function(circle) {
        circle.addEventListener('click', function() {
            var colorSetting = this.getAttribute('data-color-setting');
            if (colorSetting) {
                openColorPickerModal(colorSetting);
            }
        });
    });

    function applyDefaultColorSettings() {
        const defaultSettings = {
            backgroundColor: '#24282d',
            primaryColor: '#007bff',
            secondaryColor: '#343a40',
            textColor: '#ffffff',
            borderColor: '#3e3e3e'
        };
        applyColorSettings(defaultSettings);
        updateColorCircles(defaultSettings);
    }

    function openColorPickerModal(colorSetting) {
        var colorSettingsMap = {
            backgroundColor: 'Background Color',
            primaryColor: 'Primary Color',
            secondaryColor: 'Secondary Color',
            textColor: 'Text Color',
            borderColor: 'Border Color'
        };
    
        // Update the modal label
        var modalTitle = document.getElementById('individualColorPickerModalLabel');
        modalTitle.textContent = 'Select ' + colorSettingsMap[colorSetting];
    
        // Update the color picker label
        var colorPickerLabel = document.getElementById('colorPickerLabel');
        colorPickerLabel.textContent = colorSettingsMap[colorSetting] + ':';
    
        // Convert camelCase to kebab-case for accessing the CSS variable
        var cssVarName = '--' + colorSetting.replace(/([A-Z])/g, "-$1").toLowerCase();
    
        // Set the current color value from CSS variable
        var currentColor = getComputedStyle(document.documentElement).getPropertyValue(cssVarName).trim();
        
        // Set the color picker input to the current color value (if it exists), otherwise default to white
        document.getElementById('individualColorInput').value = currentColor || '#ffffff';
    
        // Store the colorSetting in a data attribute
        document.getElementById('individualColorInput').setAttribute('data-color-setting', colorSetting);
    
        individualColorPickerModal.show();
    }
    

    document.getElementById('saveIndividualColorSettings').addEventListener('click', function() {
        var colorInput = document.getElementById('individualColorInput');
        var colorSetting = colorInput.getAttribute('data-color-setting');
        var selectedColor = colorInput.value;

        // Fetch current color settings to update only the selected one
        fetch('/get_color_settings')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch current color settings');
                }
                return response.json();
            })
            .then(currentSettings => {
                // Update the selected color while keeping other settings intact
                currentSettings[colorSetting] = selectedColor;

                // Apply the updated settings to the page
                applyColorSettings(currentSettings);
                updateColorCircles(currentSettings);

                // Save the updated settings to the backend
                fetch('/save_color_settings', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(currentSettings)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // Close the modal
                        individualColorPickerModal.hide();
                    } else {
                        alert('Failed to save color settings.');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred while saving color settings.');
                });
            })
            .catch(error => {
                console.error('Error fetching current settings:', error);
                alert('An error occurred while fetching current color settings.');
            });
    });

    function applyColorSettings(settings) {
        console.log("Applying color settings:", settings); // Debugging to see what is being applied
        
        // Apply settings to CSS variables and log each for confirmation
        document.documentElement.style.setProperty('--background-color', settings.backgroundColor || settings.background_color || '#24282d');
        console.log("Background color applied:", settings.backgroundColor || settings.background_color || '#24282d');
    
        document.documentElement.style.setProperty('--primary-color', settings.primaryColor || settings.primary_color || '#007bff');
        console.log("Primary color applied:", settings.primaryColor || settings.primary_color || '#007bff');
    
        document.documentElement.style.setProperty('--secondary-color', settings.secondaryColor || settings.secondary_color || '#343a40');
        console.log("Secondary color applied:", settings.secondaryColor || settings.secondary_color || '#343a40');
    
        document.documentElement.style.setProperty('--text-color', settings.textColor || settings.text_color || '#ffffff');
        console.log("Text color applied:", settings.textColor || settings.text_color || '#ffffff');
    
        document.documentElement.style.setProperty('--border-color', settings.borderColor || settings.border_color || '#3e3e3e');
        console.log("Border color applied:", settings.borderColor || settings.border_color || '#3e3e3e');
    }
    

    function updateColorCircles(settings) {
        const colorSettings = ['backgroundColor', 'primaryColor', 'secondaryColor', 'textColor', 'borderColor'];
    
        colorSettings.forEach(setting => {
            const circleElement = document.getElementById(setting + 'Circle');
            if (circleElement) {
                const colorValue = settings && settings[setting] ? settings[setting] : getComputedStyle(document.documentElement).getPropertyValue('--' + setting).trim();
                circleElement.style.backgroundColor = colorValue;
            }
        });
    }
    
    
});
