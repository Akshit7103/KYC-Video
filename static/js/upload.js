// Upload Interface JavaScript

document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadVideos();
});

function setupEventListeners() {
    // Video file input
    document.getElementById('video-file').addEventListener('change', handleVideoSelect);

    // Upload form
    document.getElementById('upload-form').addEventListener('submit', handleUpload);
}

function handleVideoSelect(event) {
    const file = event.target.files[0];
    if (file) {
        const fileInfo = document.getElementById('video-info');
        const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
        fileInfo.innerHTML = `
            <p><strong>File:</strong> ${file.name}</p>
            <p><strong>Size:</strong> ${sizeMB} MB</p>
            <p><strong>Type:</strong> ${file.type}</p>
        `;
        fileInfo.style.display = 'block';
    }
}

async function handleUpload(event) {
    event.preventDefault();

    const form = document.getElementById('upload-form');
    const formData = new FormData(form);

    // Get video file
    const videoFile = document.getElementById('video-file').files[0];
    if (!videoFile) {
        alert('Please select a video file');
        return;
    }

    // Show progress
    const progressDiv = document.getElementById('upload-progress');
    const progressFill = document.getElementById('upload-progress-fill');
    const statusText = document.getElementById('upload-status');

    progressDiv.style.display = 'block';
    progressFill.style.width = '0%';
    statusText.textContent = 'Uploading...';

    try {
        // Create XMLHttpRequest to track progress
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressFill.style.width = percentComplete + '%';
                statusText.textContent = `Uploading... ${percentComplete.toFixed(1)}%`;
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                progressFill.style.width = '100%';
                statusText.textContent = 'Upload complete!';
                statusText.style.color = '#28a745';

                // Show success message
                setTimeout(() => {
                    alert(`Upload successful!\nVideo: ${result.video_file}\nDocuments: ${result.documents.join(', ') || 'None'}`);

                    // Reset form
                    form.reset();
                    document.getElementById('video-info').innerHTML = '';
                    progressDiv.style.display = 'none';
                    statusText.style.color = '#666';

                    // Reload videos list
                    loadVideos();
                }, 1000);
            } else {
                throw new Error('Upload failed');
            }
        });

        xhr.addEventListener('error', function() {
            statusText.textContent = 'Upload failed';
            statusText.style.color = '#dc3545';
            alert('Upload failed. Please try again.');
        });

        xhr.open('POST', '/api/upload-video');
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        statusText.textContent = 'Upload failed';
        statusText.style.color = '#dc3545';
        alert('Error uploading files. Check console for details.');
    }
}

async function loadVideos() {
    const container = document.getElementById('videos-list');
    container.innerHTML = '<p class="loading">Loading videos...</p>';

    try {
        const response = await fetch('/api/list-videos');
        const videos = await response.json();

        if (videos.error) {
            container.innerHTML = `<p class="message message-error">Error: ${videos.error}</p>`;
            return;
        }

        if (videos.length === 0) {
            container.innerHTML = '<p>No videos uploaded yet. Upload your first video above!</p>';
            return;
        }

        // Display videos
        container.innerHTML = '';
        videos.forEach(video => {
            const videoItem = document.createElement('div');
            videoItem.className = 'video-item';

            const uploadDate = new Date(video.uploaded).toLocaleString();
            const sizeMB = (video.size / (1024 * 1024)).toFixed(2);

            let metadataInfo = '';
            if (video.has_metadata && video.metadata) {
                const meta = video.metadata;
                metadataInfo = `
                    <p><strong>Case Type:</strong> ${meta.case_type || 'N/A'}</p>
                    <p><strong>Customer:</strong> ${meta.customer_details?.name || 'N/A'}</p>
                    <p><strong>Duration:</strong> ${meta.duration_seconds ? formatTime(meta.duration_seconds) : 'N/A'}</p>
                    <p><strong>Expected Decision:</strong> <span class="result-${meta.expected_ai_decision?.toLowerCase() || 'unknown'}">${meta.expected_ai_decision || 'N/A'}</span></p>
                    <p><strong>Consent Given:</strong> ${meta.consent_given ? '✓ Yes' : '✗ No'}</p>
                `;
            } else {
                metadataInfo = '<p class="message message-error">⚠️ No metadata file found</p>';
            }

            videoItem.innerHTML = `
                <h4>${video.filename}</h4>
                <p><strong>Size:</strong> ${sizeMB} MB</p>
                <p><strong>Uploaded:</strong> ${uploadDate}</p>
                ${metadataInfo}
            `;

            container.appendChild(videoItem);
        });

    } catch (error) {
        console.error('Error loading videos:', error);
        container.innerHTML = '<p class="message message-error">Error loading videos. Check console for details.</p>';
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
}
