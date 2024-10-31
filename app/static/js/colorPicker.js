document.addEventListener('DOMContentLoaded', function() {
    // Fetch the saved color settings and apply them on page load
    fetch('/get_color_settings')
        .then(response => response.json())
        .then(data => {
            console.log("Loaded color settings from server:", data); // Debugging
            applyColorSettings(data);

            // Show the body after applying colors
            document.body.style.visibility = 'visible';
        })
        .catch(error => console.error('Error loading color settings:', error));


    const colorPickerButton = document.getElementById('colorPickerButton');
    const colorPickerModal = new bootstrap.Modal(document.getElementById('colorPickerModal'));
    const saveColorSettingsButton = document.getElementById('saveColorSettings');

    colorPickerButton.addEventListener('click', function() {
        colorPickerModal.show();
    });

    saveColorSettingsButton.addEventListener('click', function() {
        // Directly retrieve values from the input fields
        const backgroundColor = document.getElementById('backgroundColor').value || '#24282d';
        const primaryColor = document.getElementById('primaryColor').value || '#007bff';
        const secondaryColor = document.getElementById('secondaryColor').value || '#343a40';
        const textColor = document.getElementById('textColor').value || '#ffffff';
        const borderColor = document.getElementById('borderColor').value || '#3e3e3e';
    
        const colorSettings = {
            backgroundColor,
            primaryColor,
            secondaryColor,
            textColor,
            borderColor
        };
    
        // Immediately apply the new colors to the page using the input values
        applyColorSettings(colorSettings);
    
        // Then proceed to save the color settings to the backend
        fetch('/save_color_settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(colorSettings)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Close the modal only after the settings have been saved successfully
                colorPickerModal.hide();
            } else {
                alert('Failed to save color settings.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while saving color settings.');
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
    
    
    
    
});
