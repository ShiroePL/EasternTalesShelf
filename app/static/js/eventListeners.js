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
        syncButton.addEventListener('click', function() {
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
        });
    } else {
        console.error('Sync button element not found!');
    }

    document.getElementById('addBatoLinkButton').addEventListener('click', function() {
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
    });
    


    const mangaEntries = document.querySelectorAll('.grid-item');
    const statusCounts = {
        'COMPLETED': 0,
        'PLANNING': 0,
        'CURRENT': 0,
        'PAUSED': 0,
        'ALL-STATUS': mangaEntries.length // This is a special case for the 'All' filter
    };
    const releaseStatusCounts = {
        'RELEASING': 0,
        'FINISHED': 0
    };

    mangaEntries.forEach(entry => {
        const status = entry.getAttribute('data-user-status');
        if (status in statusCounts) {
            statusCounts[status]++;
        }
        const release_status = entry.getAttribute('data-release-status');
        if (release_status in releaseStatusCounts) {
            releaseStatusCounts[release_status]++;
        }
    });

    // Update the counts in the HTML
    document.getElementById('count-completed').textContent = statusCounts['COMPLETED'];
    document.getElementById('count-planning').textContent = statusCounts['PLANNING'];
    document.getElementById('count-current').textContent = statusCounts['CURRENT'];
    document.getElementById('count-paused').textContent = statusCounts['PAUSED'];
    document.getElementById('count-all-user-stats').textContent = statusCounts['ALL-STATUS'];
    document.getElementById('count-all-release-stats').textContent = statusCounts['ALL-STATUS'];
    document.getElementById('count-releasing').textContent = releaseStatusCounts['RELEASING'];
    document.getElementById('count-finished').textContent = releaseStatusCounts['FINISHED'];



    // Event listener for status filter options
    document.querySelectorAll('.status-option').forEach(function(option) {
        option.addEventListener('click', function() {
            // Remove 'selected' class from all options
            document.querySelectorAll('.status-option').forEach(function(opt) {
                opt.classList.remove('selected');
            });

            // Add 'selected' class to the clicked option
            this.classList.add('selected');

            // Update the currentStatusFilter variable with the new value
            currentStatusFilter = this.getAttribute('data-value');

            // Call filterEntries to apply the filters
            filterEntries();
        });
    });

    // Initialize a variable to keep track of the current status filter
    currentReleasingStatusFilter = '';

    // Event listener for status filter options
    document.querySelectorAll('.statusReleasing-option').forEach(function(option) {
        option.addEventListener('click', function() {
            // Remove 'selected' class from all options
            document.querySelectorAll('.statusReleasing-option').forEach(function(opt) {
                opt.classList.remove('selected');
            });

            // Add 'selected' class to the clicked option
            this.classList.add('selected');

            // Update the currentStatusFilter variable with the new value
            currentReleasingStatusFilter = this.getAttribute('data-value');

            // Call filterEntries to apply the filters
            filterEntries();
        });
    });


    // Call filterEntries after all other event listeners are set up
    if (typeof filterEntries === 'function') {
        filterEntries();
    } else {
        console.error('filterEntries function not found');
    }

    let loginForm = document.getElementById('loginForm');
    let loginError = document.getElementById('loginError');

    loginForm.onsubmit = function(event) {
        event.preventDefault();
        let formData = new FormData(loginForm);
        
        fetch(loginUrl, {  // Use the global variable here
            method: 'POST',
            body: formData
        }).then(response => response.json()).then(data => {
            if (data.success) {
                $('#loginModal').modal('hide');
                loginError.style.display = 'none';
                window.location.reload(true); // Or redirect to another page
            } else {
                loginError.textContent = data.message;
                loginError.style.display = 'block';
            }
        }).catch(error => {
            loginError.textContent = 'An error occurred. Please try again.';
            loginError.style.display = 'block';
        });
    };


    let popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    let popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
      return new bootstrap.Popover(popoverTriggerEl);
    });
    
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