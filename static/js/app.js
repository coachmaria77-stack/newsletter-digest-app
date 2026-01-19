// Newsletter Digest App - Frontend JavaScript

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('actionStatus');
    statusDiv.textContent = message;
    statusDiv.className = `action-status show ${type}`;

    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.classList.remove('show');
        }, 5000);
    }
}

function disableButtons(disabled = true) {
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.disabled = disabled;
    });
}

// Test email connection
document.getElementById('testConnection').addEventListener('click', async () => {
    disableButtons(true);
    showStatus('Testing email connection...', 'info');

    try {
        const response = await fetch('/api/test-connection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            showStatus('✓ ' + data.message, 'success');
        } else {
            showStatus('✗ ' + data.message, 'error');
        }
    } catch (error) {
        showStatus('✗ Error: ' + error.message, 'error');
    } finally {
        disableButtons(false);
    }
});

// Trigger digest now (1 day)
document.getElementById('triggerNow').addEventListener('click', async () => {
    if (!confirm('Generate and send digest for the last 24 hours?')) {
        return;
    }

    disableButtons(true);
    showStatus('Generating digest... This may take a few minutes.', 'info');

    try {
        const response = await fetch('/api/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days_back: 1 })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('✓ Digest generation started! Check your email in a few minutes.', 'success');
            // Refresh status after a delay
            setTimeout(() => {
                location.reload();
            }, 3000);
        } else {
            showStatus('✗ ' + data.message, 'error');
        }
    } catch (error) {
        showStatus('✗ Error: ' + error.message, 'error');
    } finally {
        disableButtons(false);
    }
});

// Trigger digest for last week
document.getElementById('triggerWeek').addEventListener('click', async () => {
    if (!confirm('Generate and send digest for the last 7 days? This may take longer.')) {
        return;
    }

    disableButtons(true);
    showStatus('Generating digest for last 7 days... This may take several minutes.', 'info');

    try {
        const response = await fetch('/api/trigger', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ days_back: 7 })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('✓ Digest generation started! Check your email in a few minutes.', 'success');
            // Refresh status after a delay
            setTimeout(() => {
                location.reload();
            }, 3000);
        } else {
            showStatus('✗ ' + data.message, 'error');
        }
    } catch (error) {
        showStatus('✗ Error: ' + error.message, 'error');
    } finally {
        disableButtons(false);
    }
});

// Refresh status
document.getElementById('refreshStatus').addEventListener('click', () => {
    location.reload();
});

// Auto-refresh status every 30 seconds
setInterval(async () => {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update last run info if changed
        if (data.last_run && data.last_run.timestamp) {
            const currentTimestamp = document.querySelector('.status-item .value')?.textContent;
            if (currentTimestamp !== data.last_run.timestamp) {
                location.reload();
            }
        }
    } catch (error) {
        console.error('Error refreshing status:', error);
    }
}, 30000);
