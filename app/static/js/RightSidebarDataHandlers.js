export function processExternalLinks(externalLinksData) {
    const serviceMap = {
        'mangaupdates.com': { name: 'Manga Updates', class: 'mangaupdates' },
        'tapas.io': { name: 'Tapas', class: 'tapas' },
        'tappytoon.com': { name: 'Tappytoon', class: 'tappytoon' },
        'www.webtoons.com': { name: 'Webtoons', class: 'webtoons' },
        'yenpress.com': { name: 'Yen Press', class: 'yenpress' },
        'sevenseasentertainment.com': { name: 'Seven Seas', class: 'sevenseas' },
        'j-novel.club': { name: 'J-Novel Club', class: 'jnovel' },
    };

    try {
        let externalLinks = JSON.parse(externalLinksData || "[]");
        let linksHtml = document.createElement('div');
        linksHtml.innerHTML = '<h5 class="mb-2">Links</h5>';

        externalLinks.forEach(function(url) {
            Object.keys(serviceMap).forEach(function(key) {
                if (url.includes(key)) {
                    let serviceName = serviceMap[key].name;
                    let linkClass = serviceMap[key].class;
                    let button = document.createElement('a');
                    button.href = url;
                    button.textContent = serviceName;
                    button.className = 'btn ' + linkClass + ' btn-sm m-1';
                    button.target = '_blank';
                    linksHtml.appendChild(button);
                }
            });
        });

        return linksHtml;
    } catch (e) {
        console.error('Parsing error for external-links data:', e);
        return '<h5 class="mb-2">No links available</h5>';
    }
}

export function processGenres(genresData) {
    try {
        let genres = JSON.parse(genresData || "[]");
        let genresHtml = '<h5 class="mb-2">Genres</h5>';
        genres.forEach(function(genre) {
            genresHtml += '<span class="badge bg-secondary me-1">' + genre + '</span>';
        });
        return genresHtml;
    } catch (e) {
        console.error('Parsing error for genres data:', e);
        return '<h5 class="mb-2">No genres available</h5>';
    }
}

// Helper function to capitalize the first letter and lowercase the rest
export function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1).toLowerCase();
}








