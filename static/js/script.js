// JavaScript to show loading animation until the page content is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Hide loading spinner after the DOM is fully loaded
    hideLoading();
});

window.onload = function() {
    // Hide loading spinner once all resources (images, scripts, etc.) are fully loaded
    hideLoading();
};

window.onpageshow = function(event) {
    // If the page is loaded from the cache (like when using the back button), hide the loading spinner
    if (event.persisted) {
        hideLoading();
    }
};

// Show loading animation before unloading the page
window.addEventListener("beforeunload", function () {
    showLoading();
});

// Helper functions to show and hide the loading spinner
function showLoading() {
    document.getElementById("loading").style.visibility = "visible";
    document.getElementById("content").style.visibility = "hidden";
}

function hideLoading() {
    document.getElementById("loading").style.visibility = "hidden";
    document.getElementById("content").style.visibility = "visible";
}
