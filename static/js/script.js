// JavaScript to show loading animation until the page content is fully loaded
document.addEventListener("DOMContentLoaded", function() {
    // Show the loading animation
    var loading = document.getElementById("loading");
    var content = document.getElementById("content");

    // Once the page is fully loaded
    window.addEventListener("load", function () {
        // Hide the loading animation
        loading.style.display = "none";
        
        // Show the main content
        content.style.display = "block";
    });
});
