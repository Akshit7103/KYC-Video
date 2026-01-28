// Upload Interface JavaScript

let selectedVideo = null;
let selectedDocuments = [];

document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // Browse video button
    const browseVideoBtn = document.getElementById('browse-video-btn');
    const videoInput = document.getElementById('video-input');

    if (browseVideoBtn && videoInput) {
        browseVideoBtn.addEventListener('click', (e) => {
            e.preventDefault();
            videoInput.click();
        });

        videoInput.addEventListener('change', handleVideoSelect);
    }

    // Video dropzone
    const dropzone = document.getElementById('video-dropzone');
    if (dropzone) {
        dropzone.addEventListener('dragover', handleDragOver);
        dropzone.addEventListener('dragleave', handleDragLeave);
        dropzone.addEventListener('drop', handleDrop);
    }

    // Remove video button
    const removeVideoBtn = document.getElementById('remove-video-btn');
    if (removeVideoBtn) {
        removeVideoBtn.addEventListener('click', removeVideo);
    }

    // Add documents button
    const addDocumentsBtn = document.getElementById('add-documents-btn');
    const documentInput = document.getElementById('document-input');

    if (addDocumentsBtn && documentInput) {
        addDocumentsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            documentInput.click();
        });

        documentInput.addEventListener('change', handleDocumentSelect);
    }

    // Upload button
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', handleUpload);
    }
}

function handleVideoSelect(event) {
    const file = event.target.files[0];
    if (file) {
        // Validate file type
        const validTypes = ['video/mp4', 'video/webm', 'video/avi', 'video/x-msvideo', 'video/quicktime'];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|webm|avi|mov)$/i)) {
            alert('Please select a valid video file (MP4, WebM, AVI, MOV)');
            return;
        }

        // Validate file size (500MB)
        if (file.size > 500 * 1024 * 1024) {
            alert('File size must be less than 500MB');
            return;
        }

        selectedVideo = file;
        showVideoPreview(file);
        updateUploadButton();
    }
}

function showVideoPreview(file) {
    const dropzoneContent = document.querySelector('.dropzone-content');
    const videoPreview = document.getElementById('video-preview');
    const videoFilename = document.getElementById('video-filename');
    const videoSize = document.getElementById('video-size');

    if (dropzoneContent && videoPreview) {
        dropzoneContent.style.display = 'none';
        videoPreview.style.display = 'flex';

        if (videoFilename) {
            videoFilename.textContent = file.name;
        }

        if (videoSize) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            videoSize.textContent = sizeMB + ' MB';
        }
    }
}

function removeVideo() {
    selectedVideo = null;

    const dropzoneContent = document.querySelector('.dropzone-content');
    const videoPreview = document.getElementById('video-preview');
    const videoInput = document.getElementById('video-input');

    if (dropzoneContent && videoPreview) {
        dropzoneContent.style.display = 'block';
        videoPreview.style.display = 'none';
    }

    if (videoInput) {
        videoInput.value = '';
    }

    updateUploadButton();
}

function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];

        // Validate file type
        const validTypes = ['video/mp4', 'video/webm', 'video/avi', 'video/x-msvideo', 'video/quicktime'];
        if (!validTypes.includes(file.type) && !file.name.match(/\.(mp4|webm|avi|mov)$/i)) {
            alert('Please drop a valid video file (MP4, WebM, AVI, MOV)');
            return;
        }

        // Validate file size (500MB)
        if (file.size > 500 * 1024 * 1024) {
            alert('File size must be less than 500MB');
            return;
        }

        selectedVideo = file;
        showVideoPreview(file);
        updateUploadButton();
    }
}

function handleDocumentSelect(event) {
    const files = Array.from(event.target.files);

    files.forEach(file => {
        // Validate file type
        const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        if (!validTypes.includes(file.type)) {
            alert(`Invalid file type: ${file.name}. Please select images only (JPG, PNG, GIF)`);
            return;
        }

        selectedDocuments.push(file);
        addDocumentToList(file);
    });

    // Reset input
    event.target.value = '';
}

function addDocumentToList(file) {
    const documentList = document.getElementById('document-list');
    if (!documentList) return;

    const docItem = document.createElement('div');
    docItem.className = 'document-item';
    docItem.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
        <span>${file.name}</span>
        <button class="btn-remove-doc" data-filename="${file.name}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        </button>
    `;

    // Add remove button listener
    const removeBtn = docItem.querySelector('.btn-remove-doc');
    removeBtn.addEventListener('click', () => {
        selectedDocuments = selectedDocuments.filter(f => f.name !== file.name);
        docItem.remove();
    });

    documentList.appendChild(docItem);
}

function updateUploadButton() {
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.disabled = !selectedVideo;
    }
}

async function handleUpload() {
    if (!selectedVideo) {
        alert('Please select a video file');
        return;
    }

    const uploadBtn = document.getElementById('upload-btn');
    const progressSection = document.getElementById('upload-progress-section');
    const progressFill = document.getElementById('upload-progress-fill');
    const progressText = document.getElementById('upload-progress-text');
    const statusText = document.getElementById('upload-status-text');

    // Show progress section
    if (progressSection) {
        progressSection.style.display = 'block';
    }

    // Disable upload button
    if (uploadBtn) {
        uploadBtn.disabled = true;
    }

    try {
        // Create FormData
        const formData = new FormData();
        formData.append('video', selectedVideo);

        // Add documents
        selectedDocuments.forEach((doc, index) => {
            formData.append(`document_${index}`, doc);
        });

        // Create XMLHttpRequest to track progress
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                if (progressFill) {
                    progressFill.style.width = percentComplete + '%';
                }
                if (progressText) {
                    progressText.textContent = percentComplete + '%';
                }
                if (statusText) {
                    statusText.textContent = `Uploading... ${percentComplete}%`;
                }
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);

                if (progressFill) {
                    progressFill.style.width = '100%';
                }
                if (progressText) {
                    progressText.textContent = '100%';
                }
                if (statusText) {
                    statusText.textContent = 'Upload complete!';
                }

                // Show success message
                setTimeout(() => {
                    let message = `Upload successful!\n\nVideo: ${result.video_file}`;
                    if (result.documents && result.documents.length > 0) {
                        message += `\nDocuments: ${result.documents.join(', ')}`;
                    }
                    alert(message);

                    // Reset form
                    resetUploadForm();
                }, 1000);
            } else {
                throw new Error('Upload failed');
            }
        });

        xhr.addEventListener('error', function() {
            if (statusText) {
                statusText.textContent = 'Upload failed';
            }
            alert('Upload failed. Please try again.');

            if (uploadBtn) {
                uploadBtn.disabled = false;
            }
        });

        xhr.open('POST', '/api/upload-video');
        xhr.send(formData);

    } catch (error) {
        console.error('Upload error:', error);
        if (statusText) {
            statusText.textContent = 'Upload failed';
        }
        alert('Error uploading files. Check console for details.');

        if (uploadBtn) {
            uploadBtn.disabled = false;
        }
    }
}

function resetUploadForm() {
    // Reset video
    selectedVideo = null;
    removeVideo();

    // Reset documents
    selectedDocuments = [];
    const documentList = document.getElementById('document-list');
    if (documentList) {
        documentList.innerHTML = '';
    }

    // Hide progress
    const progressSection = document.getElementById('upload-progress-section');
    if (progressSection) {
        progressSection.style.display = 'none';
    }

    // Reset upload button
    updateUploadButton();
}
