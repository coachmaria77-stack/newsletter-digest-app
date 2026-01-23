// Newsletter Digest App - Frontend JavaScript

var pollInterval = null;

function updateProgress(step, totalSteps, statusText) {
    var container = document.getElementById("progressContainer");
    var bar = document.getElementById("progressBar");
    var text = document.getElementById("progressText");

    if (!container || !bar || !text) return;

    if (step > 0 && step < totalSteps) {
        container.style.display = "block";
        var percent = Math.round((step / totalSteps) * 100);
        bar.style.width = percent + "%";
        text.textContent = statusText + " (" + percent + "%)";
    } else {
        container.style.display = "none";
    }
}

function startPolling() {
    if (pollInterval) return;

    pollInterval = setInterval(function() {
        fetch("/api/status")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.last_run) {
                    var step = data.last_run.step || 0;
                    var totalSteps = data.last_run.total_steps || 10;
                    var status = data.last_run.status;

                    // Update progress bar
                    updateProgress(step, totalSteps, status);

                    // Update status text
                    var statusEl = document.getElementById("statusText");
                    if (statusEl) {
                        statusEl.textContent = status;
                    }

                    // Update counts
                    var nlCount = document.getElementById("statusNewsletterCount");
                    var artCount = document.getElementById("statusArticleCount");
                    if (nlCount) nlCount.textContent = data.last_run.newsletter_count || 0;
                    if (artCount) artCount.textContent = data.last_run.article_count || 0;

                    // Stop polling when done
                    if (status.indexOf("Success") !== -1 || status.indexOf("Error") !== -1 ||
                        status.indexOf("Failed") !== -1 || status.indexOf("No ") === 0) {
                        stopPolling();
                        updateProgress(0, 10, "");
                        showStatus("Digest complete! " + status, "success");
                    }
                }
            })
            .catch(function(error) {
                console.error("Polling error:", error);
            });
    }, 2000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

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
                showStatus("Digest generation started! Watch the progress below.", "info");
                startPolling();
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
                showStatus("Digest generation started! Watch the progress below.", "info");
                startPolling();
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
        showStatus("Refreshing status...", "info");
        fetch("/api/status")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.last_run) {
                    var step = data.last_run.step || 0;
                    var totalSteps = data.last_run.total_steps || 10;
                    var statusValue = data.last_run.status;

                    // Update progress bar
                    updateProgress(step, totalSteps, statusValue);

                    // Update Last Run Status section by ID
                    var timestamp = document.getElementById("statusTimestamp");
                    var status = document.getElementById("statusText");
                    var nlCount = document.getElementById("statusNewsletterCount");
                    var artCount = document.getElementById("statusArticleCount");

                    if (timestamp) timestamp.textContent = data.last_run.timestamp || "Never";
                    if (status) {
                        status.textContent = statusValue;
                    }
                    if (nlCount) nlCount.textContent = data.last_run.newsletter_count || 0;
                    if (artCount) artCount.textContent = data.last_run.article_count || 0;

                    // Start polling if still running
                    if (statusValue.indexOf("...") !== -1) {
                        startPolling();
                    }
                }
                showStatus("Status refreshed!", "success");
            })
            .catch(function(error) {
                showStatus("Error: " + error.message, "error");
            });
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
                digestFrame.srcdoc = '<div style="text-align: center; padding: 40px; font-family: -apple-system, BlinkMacSystemFont, sans-serif;"><img src="https://cataas.com/cat/cute?width=300&height=200" style="border-radius: 12px; margin-bottom: 20px; max-width: 300px;"><h2 style="color: #667eea;">No digest yet!</h2><p style="color: #666;">Click Generate Digest Now above to create your first digest.</p></div>';
                loadButton.textContent = "Refresh Digest";
                loadButton.disabled = false;
            });
    }

    document.getElementById("loadDigest").addEventListener("click", loadDigest);

    setTimeout(loadDigest, 100);

    // Auto-refresh removed - was causing page to jump while reading

    // Newsletter Management
    function loadNewsletters() {
        var listEl = document.getElementById("newsletterList");
        if (!listEl) return;

        fetch("/api/newsletters")
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.newsletters && data.newsletters.length > 0) {
                    var html = "";
                    data.newsletters.forEach(function(nl) {
                        html += '<div class="newsletter-item" data-email="' + nl.email + '">';
                        html += '<div class="newsletter-info">';
                        html += '<span class="newsletter-name">' + (nl.name || nl.email) + '</span>';
                        html += '<span class="newsletter-email">' + nl.email + '</span>';
                        html += '</div>';
                        html += '<button class="btn btn-danger btn-small remove-newsletter">Remove</button>';
                        html += '</div>';
                    });
                    listEl.innerHTML = html;

                    // Add event listeners to remove buttons
                    var removeButtons = listEl.querySelectorAll(".remove-newsletter");
                    removeButtons.forEach(function(btn) {
                        btn.addEventListener("click", function() {
                            var item = this.closest(".newsletter-item");
                            var email = item.getAttribute("data-email");
                            removeNewsletter(email);
                        });
                    });
                } else {
                    listEl.innerHTML = '<p class="empty-message">No newsletters configured. Add one above!</p>';
                }
            })
            .catch(function(error) {
                console.error("Error loading newsletters:", error);
                listEl.innerHTML = '<p class="empty-message">Error loading newsletters</p>';
            });
    }

    function removeNewsletter(email) {
        if (!confirm("Remove " + email + " from newsletters?")) {
            return;
        }

        fetch("/api/newsletters", {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ email: email })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (data.success) {
                showStatus("Removed: " + email, "success");
                loadNewsletters();
            } else {
                showStatus("Error: " + data.message, "error");
            }
        })
        .catch(function(error) {
            showStatus("Error: " + error.message, "error");
        });
    }

    var addBtn = document.getElementById("addNewsletter");
    if (addBtn) {
        addBtn.addEventListener("click", function() {
            var emailInput = document.getElementById("newsletterEmail");
            var nameInput = document.getElementById("newsletterName");
            var email = emailInput.value.trim();
            var name = nameInput.value.trim();

            if (!email) {
                showStatus("Please enter an email address", "error");
                return;
            }

            fetch("/api/newsletters", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ email: email, name: name })
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.success) {
                    showStatus("Added: " + email, "success");
                    emailInput.value = "";
                    nameInput.value = "";
                    loadNewsletters();
                } else {
                    showStatus("Error: " + data.message, "error");
                }
            })
            .catch(function(error) {
                showStatus("Error: " + error.message, "error");
            });
        });
    }

    // Load newsletters on page load
    loadNewsletters();
});
