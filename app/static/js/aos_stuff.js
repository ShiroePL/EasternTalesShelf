// this prevents AOS to move down page each reloding.
if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }


// Consolidated load event listener
window.addEventListener('load', function() {

    // Initialize or refresh AOS based on cumulative height logic
    let items = document.querySelectorAll('.grid-item');
    let cumulativeHeight = 0;
    items.forEach(function(item) {
        if (item.style.display !== 'none') {
            cumulativeHeight += item.offsetHeight + 10; // Adjust if necessary
        }
    });

    let windowHeight = window.innerHeight;
    if (cumulativeHeight > windowHeight) {
        setTimeout(function(){
            AOS.init({
                offset: 120,
                duration: 1000,
            });
        }, 100); // Adjust the timeout as needed
    }

    // AOS refresh logic
    AOS.refresh();

    // Set border color based on data-status
    items.forEach(function(item) {
        let status = item.getAttribute('data-user-status');
        if(status) {
            status = status.toUpperCase();
            let statusClass = 'border-' + status.toLowerCase();
            item.classList.add(statusClass);
        }
    });
});

// Consolidated resize event listener
window.addEventListener('resize', () => {
    AOS.refresh();
});


document.addEventListener('aos:in', ({ detail }) => {
    console.log('animated in', detail);
    // You could trigger a layout update here, if necessary
    // For example, if you're using a layout library or need to manually update the footer position
  });
  
document.addEventListener('aos:out', ({ detail }) => {
console.log('animated out', detail);
// Handle the animation out event
});