// Loader listening for enter press on chatInput
document.addEventListener('DOMContentLoaded', function() {
    // Add debugging to check global variables on load
    console.log('DEBUG: Page loaded, debugging globals:');
    console.log('DEBUG: window.currentAnilistId =', window.currentAnilistId);
    console.log('DEBUG: window.currentSeriesName =', window.currentSeriesName);
    
    // Code for chatInput
    let chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    } else {
        console.error('chatInput element not found!');
    }

    // Code for syncButton
    let syncButton = document.getElementById('syncButton');

    if (syncButton) {
        syncButton.addEventListener('click', window.requireAdmin(function() {
            fetch('/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (response.ok && response.headers.get("content-type")?.includes("application/json")) {
                    return response.json();
                }
                throw new Error('Server responded with a non-JSON response.');
            })
            .then(data => {
                console.log('Success:', data);
                alert('Sync successful!');
                window.location.reload(); // Reload the page
            })
            .catch((error) => {
                console.error('Error:', error);
                alert('An error occurred: ' + error.message);
            });
        }));
    } else {
        console.error('Sync button element not found!');
    }

    document.getElementById('addBatoLinkButton').addEventListener('click', window.requireAdmin(function() {
        console.log('DEBUG: Add Bato Link button clicked');
        console.log('DEBUG: Global variables at click time:', {
            windowCurrentAnilistId: window.currentAnilistId,
            windowCurrentSeriesName: window.currentSeriesName
        });
        
        if (window.currentAnilistId) {
            console.log('DEBUG: Using window.currentAnilistId:', window.currentAnilistId);
            let link = prompt("Please enter a Bato.to or MangaUpdates link for this entry:", "http://");
            if (link !== null && link !== "") {
                fetch('/add_bato', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        anilistId: window.currentAnilistId,
                        batoLink: link,
                        seriesname: window.currentSeriesName
                    })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Success:', data);
                    alert(data.message || 'Bato link added successfully!');
                    
                    // Update the specific grid item with the new bato link
                    updateGridItemBatoLink(window.currentAnilistId, link);
                    
                    // Update the Bato link in the right sidebar if it's currently shown
                    if (link.includes('bato.to')) {
                        $('#link-bato').attr('href', link).show();
                        adjustButtonSpacing();
                    }
                })
                .catch((error) => {
                    console.error('Error:', error);
                    alert('An error occurred: ' + error.message);
                });
            } else if (link === "") {
                alert('No link entered. Please enter a valid Bato link.');
            }
        } else {
            console.log('DEBUG: No entry is focused currently - window.currentAnilistId is falsy');
            console.log('DEBUG: window object properties related to currentAnilistId:', 
                Object.keys(window).filter(key => key.toLowerCase().includes('current') || key.toLowerCase().includes('anilist')));
            alert('No entry is focused currently.');
        }
    }));
    
    // Note: Status counts are now handled by LeftSidebarStats.js using GraphQL
    // This enhances performance and keeps counts in sync with the data
    
    // Add WebSocket listener for MangaUpdates data updates
    if (window.socket) {
        window.socket.on('mangaupdates_data_update', function(data) {
            if (data.anilist_id === currentAnilistId) {
                // Update the MangaUpdates info in the right sidebar
                updateMangaUpdatesInfo(data.data);
            }
            
            // Also update the data attributes on the grid item
            const gridItem = document.querySelector(`.grid-item[data-anilist-id="${data.anilist_id}"]`);
            if (gridItem) {
                gridItem.dataset.mangaupdatesStatus = data.data.status;
                gridItem.dataset.mangaupdatesLicensed = data.data.licensed;
                gridItem.dataset.mangaupdatesCompleted = data.data.completed;
                gridItem.dataset.mangaupdatesLastUpdated = data.data.last_updated;
            }
        });
    }
}); // end of DOMContentLoaded listener

// FUNCTIONS CANNOT BE IN DOM. 

function openAniList(url) {
    window.open(url, '_blank');
}
function openBatoFromCover(url){
    // Get the data from the clicked element
    
    if (url !== '') {
        window.open(url, '_blank');
    }
}

// Add this function to update the MangaUpdates info section
function updateMangaUpdatesInfo(data) {
    const container = document.getElementById('mangaupdates-content');
    if (container) {
        container.innerHTML = `
            <p>Status: ${data.status || 'N/A'}</p>
            <p>Licensed: ${data.licensed ? 'Yes' : 'No'}</p>
            <p>Completed: ${data.completed ? 'Yes' : 'No'}</p>
            <p>Last Updated: ${data.last_updated ? new Date(data.last_updated).toLocaleDateString() : 'N/A'}</p>
        `;
    }
}

// Function to update a specific grid item's bato link without refreshing the whole grid
function updateGridItemBatoLink(anilistId, newBatoLink) {
    console.log('DEBUG: Updating grid item bato link for ID:', anilistId, 'with link:', newBatoLink);
    
    // Find the specific grid item
    const gridItem = document.querySelector(`.grid-item[data-anilist-id="${anilistId}"]`);
    
    if (!gridItem) {
        console.log('DEBUG: Grid item not found for anilist ID:', anilistId);
        return;
    }
    
    // Update the data attribute
    gridItem.setAttribute('data-bato-link', newBatoLink);
    
    // Find the bato icon within this grid item
    const batoIcon = gridItem.querySelector('.bato-icon');
    
    if (batoIcon) {
        // Show the bato icon since we now have a link
        if (newBatoLink && newBatoLink !== 'None' && newBatoLink !== '') {
            batoIcon.style.display = ''; // Show the icon
            console.log('DEBUG: Bato icon shown for anilist ID:', anilistId);
            
            // Update the click handler for the bato icon
            batoIcon.onclick = function(e) {
                e.stopPropagation();
                window.open(newBatoLink, '_blank');
            };
        } else {
            batoIcon.style.display = 'none'; // Hide the icon
            console.log('DEBUG: Bato icon hidden for anilist ID:', anilistId);
        }
    } else {
        console.log('DEBUG: Bato icon not found in grid item for anilist ID:', anilistId);
    }
}