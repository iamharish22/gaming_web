// JavaScript to dynamically add loading animation to the DOM
window.addEventListener("load", function () {
    // Create the loading div and spinner
    var loadingDiv = document.createElement("div");
    loadingDiv.id = "loading";
    loadingDiv.innerHTML = '<div class="spinner"></div>';

    // Append the loading div to the body
    document.body.prepend(loadingDiv);

    // Once the page is loaded, hide the loading animation
    loadingDiv.style.display = "none";

    // Show the main content
    var content = document.getElementById("content");
    if (content) {
        content.style.display = "block";
    }
});
