// Loader listening for enter press on chatInput
document.addEventListener('DOMContentLoaded', function() {
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
        if (currentAnilistId) {
            let link = prompt("Please enter a Bato.to or MangaUpdates link for this entry:", "http://");
            if (link !== null && link !== "") {
                fetch('/add_bato', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        anilistId: currentAnilistId,
                        batoLink: link,
                        seriesname: currentSeriesName
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
                    
                    // Update the Bato link in the UI immediately
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