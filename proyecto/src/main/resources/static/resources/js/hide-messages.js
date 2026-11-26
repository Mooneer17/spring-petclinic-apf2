// Function to hide the success and error messages after 3 seconds
// (APF3: moved from an inline script so the Content-Security-Policy can use script-src 'self')
function hideMessages() {
  setTimeout(function () {
    document.getElementById("success-message").style.display = "none";
    document.getElementById("error-message").style.display = "none";
  }, 3000); // 3000 milliseconds (3 seconds)
}

// Call the function to hide messages
hideMessages();
