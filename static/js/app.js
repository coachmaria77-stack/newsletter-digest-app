/ Newsletter Digest App - Frontend JavaScript

function showStatus(message, type) {
    if (!type) type = "info";
    var statusDiv = document.getElementById("actionStatus");
    if (!statusDiv) {
        console.error("actionStatus element not found");
        return;
    }
    statusDiv.textContent = message;
    statusDiv.className = "action-status show " + type;

    if (type === "success") {
        setTimeout(function() {
            statusDiv.classList.remove("show");
        }, 5000);
    }
}

function disableButtons(disabled) {
    if (disabled === undefined) disabled = true;
    var buttons = document.querySelectorAll(".btn");
    buttons.forEach(function(btn) {
        btn.disabled = disabled;
    });
}

window.addEventListener("DOMContentLoaded", function() {
    document.getElementById("testConnection").addEventListener("click", function() {
        disableButtons(true);
        showStatus("Testing email connection...", "info");

        fetch("/api/test-connection", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                showStatus("Success: " + data.message, "success");
            } else {
                showStatus("Error: " + data.message, "error");
            }
        })
        .catch(function(error) {
            showStatus("Error: " + error.message, "error");
        })
        .finally(function() {
            disableButtons(false);
        });
    });

    document.getElementById("triggerNow").addEventListener("click", function() {
        if (!confirm("Generate and send digest for the last 24 hours?")) {
            return;
        }

        disableButtons(true);
        showStatus("Generating digest... This may take a few minutes.", "info");

        fetch("/api/trigger", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ days_back: 1 })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                showStatus("Digest generation started! Check your email in a few minutes.", "success");
            } else {
                showStatus("Error: " + data.message, "error");
            }
        })
        .catch(function(error) {
            showStatus("Error: " + error.message, "error");
        })
        .finally(function() {
            disableButtons(false);
        });
    });

    document.getElementById("triggerWeek").addEventListener("click", function() {
        if (!confirm("Generate and send digest for the last 7 days? This may take longer.")) {
            return;
        }

        disableButtons(true);
        showStatus("Generating digest for last 7 days... This may take several minutes.", "info");

        fetch("/api/trigger", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ days_back: 7 })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                showStatus("Digest generation started! Check your email in a few minutes.", "success");
            } else {
                showStatus("Error: " + data.message, "error");
            }
        })
        .catch(function(error) {
            showStatus("Error: " + error.message, "error");
        })
        .finally(function() {
            disableButtons(false);
        });
    });

    document.getElementById("refreshStatus").addEventListener("click", function() {
        location.reload();
    });

    function loadDigest() {
        var digestFrame = document.getElementById("digestFrame");
        var loadButton = document.getElementById("loadDigest");
        var digestContent = document.getElementById("digestContent");

        if (!digestFrame || !loadButton) {
            console.error("Digest elements not found");
            return;
        }

        if (digestContent) {
            digestContent.style.display = "block";
        }

        loadButton.textContent = "Loading...";
        loadButton.disabled = true;

        fetch("/view-digest")
            .then(function(response) { return response.text(); })
            .then(function(html) {
                var blob = new Blob([html], { type: "text/html" });
                digestFrame.src = URL.createObjectURL(blob);
                loadButton.textContent = "Refresh Digest";
                loadButton.disabled = false;
            })
            .catch(function(error) {
                console.error("Error loading digest:", error);
                digestFrame.srcdoc = "<div><h2>No digest available yet</h2><p>Generate a digest first.</p></div>";
                loadButton.textContent = "Refresh Digest";
                loadButton.disabled = false;
            });
    }

    document.getElementById("loadDigest").addEventListener("click", loadDigest);

    setTimeout(loadDigest, 100);

    setInterval(function() {
        fetch("/api/status")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.last_run && data.last_run.timestamp) {
                    var el = document.querySelector(".status-item .value");
                    if (el && el.textContent !== data.last_run.timestamp) {
                        loadDigest();
                    }
                }
            })
            .catch(function(error) {
                console.error("Error refreshing status:", error);
            });
    }, 30000);
});
