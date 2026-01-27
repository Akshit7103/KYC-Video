// Recording Assistant JavaScript - Simplified (No Script Display)

let scriptData = null;
let currentSectionIndex = 0;
let currentLineIndex = 0;
let timerInterval = null;
let seconds = 0;
let isRecording = false;

// Recording variables
let mediaRecorder = null;
let recordedChunks = [];
let stream = null;
let videoBlob = null;

// Speech synthesis
let speechSynthesis = window.speechSynthesis;
let currentUtterance = null;
let isAutoPlaying = false;

// Capture mode variables
let capturedImages = [];
let currentCaptureType = null; // 'pan' or 'aadhaar'

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadScript();
    setupEventListeners();
    checkBrowserSupport();
    initializeWebcam();
});

// Check browser support for recording
function checkBrowserSupport() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Your browser does not support webcam recording. Please use Chrome, Firefox, or Edge.');
        return false;
    }
    if (!window.MediaRecorder) {
        alert('Your browser does not support video recording. Please use Chrome, Firefox, or Edge.');
        return false;
    }
    if (!window.speechSynthesis) {
        alert('Your browser does not support text-to-speech. Some features may not work.');
    }
    return true;
}

// Initialize webcam preview
async function initializeWebcam() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 1280, height: 720 },
            audio: true
        });

        const video = document.getElementById('webcam-video');
        video.srcObject = stream;
        video.play();

        document.getElementById('webcam-status-text').textContent = '✓ Camera Ready';
        console.log('Webcam initialized');
    } catch (error) {
        console.error('Error accessing webcam:', error);
        document.getElementById('webcam-status-text').textContent = '✗ Camera Error';
        alert('Could not access webcam. Please allow camera and microphone permissions and refresh the page.');
    }
}

// Load KYC script
async function loadScript() {
    try {
        const response = await fetch('/api/get-script');
        scriptData = await response.json();
        console.log('Script loaded:', scriptData);
    } catch (error) {
        console.error('Error loading script:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    document.getElementById('start-btn').addEventListener('click', startRecording);
    document.getElementById('stop-btn').addEventListener('click', stopRecording);
    document.getElementById('download-btn').addEventListener('click', downloadVideo);
    document.getElementById('metadata-form-element').addEventListener('submit', saveMetadata);
    document.getElementById('next-question-btn').addEventListener('click', handleNextQuestion);

    // Capture mode buttons
    document.getElementById('capture-btn').addEventListener('click', captureImage);
    document.getElementById('retake-btn').addEventListener('click', retakeImage);
    document.getElementById('capture-next-btn').addEventListener('click', handleCaptureNext);
}

// Start recording and automated playback
async function startRecording() {
    if (!stream) {
        alert('Please allow webcam access first and refresh the page.');
        return;
    }

    // Start recording
    try {
        recordedChunks = [];
        capturedImages = [];

        mediaRecorder = new MediaRecorder(stream, {
            mimeType: 'video/webm;codecs=vp9'
        });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
            console.log('Recording stopped. Blob size:', videoBlob.size);

            // Update status
            document.getElementById('webcam-status-text').textContent = '✓ Recording Complete';

            // Enable download button
            document.getElementById('download-btn').disabled = false;

            // Show metadata form
            document.getElementById('metadata-form').style.display = 'block';
            document.getElementById('metadata-form').scrollIntoView({ behavior: 'smooth' });
        };

        mediaRecorder.start();
        isRecording = true;

        // Update UI
        document.getElementById('start-btn').disabled = true;
        document.getElementById('stop-btn').disabled = false;
        document.getElementById('webcam-status-text').textContent = '🔴 Recording...';

        // Start timer
        timerInterval = setInterval(updateTimer, 1000);

        // Enter fullscreen
        enterFullscreen();

        // Start automated question playback
        isAutoPlaying = true;
        currentSectionIndex = 0;
        currentLineIndex = 0;

        playNextLine();

        console.log('Recording started');
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not start recording: ' + error.message);
    }
}

// Collect all lines that should be spoken together (grouped lines)
function collectGroupedLines() {
    const lines = [];
    const section = scriptData.sections[currentSectionIndex];

    let idx = currentLineIndex;
    while (idx < section.script_lines.length) {
        const line = section.script_lines[idx];
        lines.push({ line, index: idx });

        // If this line has group_with_next, continue collecting
        if (line.group_with_next) {
            idx++;
        } else {
            break;
        }
    }

    return lines;
}

// Play next line(s) using text-to-speech
function playNextLine() {
    if (!scriptData || !isAutoPlaying) return;

    const section = scriptData.sections[currentSectionIndex];

    // Check if we've reached the end of this section
    if (currentLineIndex >= section.script_lines.length) {
        // Move to next section
        currentSectionIndex++;
        currentLineIndex = 0;

        if (currentSectionIndex >= scriptData.sections.length) {
            // All sections complete - automatically stop recording
            console.log('All questions completed - stopping recording automatically');
            isAutoPlaying = false;
            hideAllOverlays();
            stopRecording();
            return;
        }

        // Continue to next section
        playNextLine();
        return;
    }

    // Collect grouped lines
    const groupedLines = collectGroupedLines();
    const lastLine = groupedLines[groupedLines.length - 1].line;
    const lastLineIndex = groupedLines[groupedLines.length - 1].index;

    // Update progress bars
    updateProgressBars();

    // Hide all overlays while speaking
    hideAllOverlays();

    // Combine text from grouped lines
    const combinedText = groupedLines.map(item => item.line.text).join('. ');

    // Check if last line in group requires capture mode
    const isCaptureMode = lastLine.capture_mode === true;

    // Check if any line in the group requires document display
    let showDocument = false;
    let documentType = null;
    for (const item of groupedLines) {
        if (item.line.action_required === 'customer_shows_pan') {
            showDocument = true;
            documentType = 'pan';
            currentCaptureType = 'pan';
        } else if (item.line.action_required === 'customer_shows_aadhaar') {
            showDocument = true;
            documentType = 'aadhaar';
            currentCaptureType = 'aadhaar';
        }
    }

    // Set document indicator text
    if (documentType === 'pan') {
        document.getElementById('document-text').textContent = '📇 Show Your PAN Card';
    } else if (documentType === 'aadhaar') {
        document.getElementById('document-text').textContent = '📇 Show Your Aadhaar Card (Masked)';
    }

    // Check if this is the auto-terminate section (closing)
    const isAutoTerminate = section.auto_terminate === true || lastLine.auto_terminate === true;

    console.log(`Speaking: "${combinedText.substring(0, 50)}..."`);

    // Speak the combined text
    speakText(combinedText, () => {
        // Update current line index to after the grouped lines
        currentLineIndex = lastLineIndex;

        // After speaking, show appropriate overlay
        if (isAutoTerminate) {
            // Auto-terminate: just move to next line (which will trigger end)
            currentLineIndex++;
            playNextLine();
        } else if (isCaptureMode) {
            // Show document indicator and capture buttons
            if (showDocument) {
                document.getElementById('document-indicator').style.display = 'block';
            }
            document.getElementById('capture-overlay').style.display = 'flex';
            document.getElementById('capture-btn').style.display = 'inline-block';
            document.getElementById('retake-btn').style.display = 'none';
            document.getElementById('capture-next-btn').style.display = 'none';
            document.getElementById('capture-status').style.display = 'none';
            console.log('Waiting for user to capture image...');
        } else {
            // Show regular Next button
            document.getElementById('video-overlay').style.display = 'flex';
            console.log('Waiting for user to click Next...');
        }
    });
}

// Hide all overlay elements
function hideAllOverlays() {
    document.getElementById('video-overlay').style.display = 'none';
    document.getElementById('capture-overlay').style.display = 'none';
    document.getElementById('document-indicator').style.display = 'none';
    document.getElementById('capture-status').style.display = 'none';
}

// Handle Next button click
function handleNextQuestion() {
    if (!isAutoPlaying) return;

    // Hide overlays
    hideAllOverlays();

    // Move to next line
    currentLineIndex++;
    playNextLine();
}

// Capture image from video
function captureImage() {
    const video = document.getElementById('webcam-video');
    const canvas = document.getElementById('capture-canvas');
    const ctx = canvas.getContext('2d');

    // Set canvas size to match video
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    // Draw current video frame to canvas
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Convert to base64 image
    const imageData = canvas.toDataURL('image/png');

    // Store the captured image
    capturedImages.push({
        type: currentCaptureType,
        timestamp: Date.now(),
        data: imageData
    });

    console.log(`Captured ${currentCaptureType} image`);

    // Update UI
    document.getElementById('capture-status').style.display = 'block';
    document.getElementById('capture-btn').style.display = 'none';
    document.getElementById('retake-btn').style.display = 'inline-block';
    document.getElementById('capture-next-btn').style.display = 'inline-block';
}

// Retake image
function retakeImage() {
    // Remove the last captured image of this type
    const lastIndex = capturedImages.findIndex(img => img.type === currentCaptureType);
    if (lastIndex !== -1) {
        capturedImages.splice(lastIndex, 1);
    }

    console.log(`Retaking ${currentCaptureType} image`);

    // Reset UI
    document.getElementById('capture-status').style.display = 'none';
    document.getElementById('capture-btn').style.display = 'inline-block';
    document.getElementById('retake-btn').style.display = 'none';
    document.getElementById('capture-next-btn').style.display = 'none';
}

// Handle capture mode Next button
function handleCaptureNext() {
    if (!isAutoPlaying) return;

    // Hide overlays
    hideAllOverlays();

    // Move to next line
    currentLineIndex++;
    playNextLine();
}

// Speak text using Web Speech API
function speakText(text, callback) {
    // Stop any ongoing speech
    speechSynthesis.cancel();

    // Replace placeholders with generic values
    text = text.replace(/\[Customer Name\]/g, 'valued customer');
    text = text.replace(/\[Bank Name\]/g, 'our bank');
    text = text.replace(/\[Bank\/NBFC Name\]/g, 'our organization');
    text = text.replace(/\[Read address\]/g, '123 Main Street, Mumbai, Maharashtra, 400001');

    currentUtterance = new SpeechSynthesisUtterance(text);
    currentUtterance.rate = 0.9; // Slightly slower
    currentUtterance.pitch = 1.0;
    currentUtterance.volume = 1.0;

    currentUtterance.onend = () => {
        if (callback) callback();
    };

    currentUtterance.onerror = (event) => {
        console.error('Speech error:', event);
        if (callback) callback();
    };

    speechSynthesis.speak(currentUtterance);
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        isAutoPlaying = false;
        speechSynthesis.cancel();

        mediaRecorder.stop();
        isRecording = false;

        clearInterval(timerInterval);

        document.getElementById('stop-btn').disabled = true;

        // Hide all overlays
        hideAllOverlays();

        // Exit fullscreen
        exitFullscreen();

        // Mark all progress as complete
        for (let i = 1; i <= 8; i++) {
            const progressBar = document.getElementById(`progress-${i}`);
            if (progressBar) {
                progressBar.style.width = '100%';
            }
        }

        console.log('Recording stopped');

        // Save captured images if any
        if (capturedImages.length > 0) {
            saveCapturedImages();
        }
    }
}

// Save captured images to server
async function saveCapturedImages() {
    try {
        const response = await fetch('/api/save-captures', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                images: capturedImages,
                timestamp: Date.now()
            })
        });

        const result = await response.json();
        if (result.success) {
            console.log('Captured images saved:', result.files);
        }
    } catch (error) {
        console.error('Error saving captured images:', error);
    }
}

// Download video
function downloadVideo() {
    if (!videoBlob) {
        alert('No video recorded yet.');
        return;
    }

    const url = URL.createObjectURL(videoBlob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;

    const timestamp = Date.now();
    const filename = `video_kyc_${timestamp}.webm`;

    a.download = filename;
    document.body.appendChild(a);
    a.click();

    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);

    console.log('Video downloaded:', filename);

    // Update filename in metadata form
    document.getElementById('video-filename').value = filename;
}

// Timer functions
function updateTimer() {
    seconds++;
    updateTimerDisplay();
    updateProgressBars();
}

function updateTimerDisplay() {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    document.getElementById('timer').textContent =
        `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateProgressBars() {
    if (!scriptData) return;

    const totalSections = scriptData.sections.length;

    for (let i = 0; i < totalSections; i++) {
        const progressBar = document.getElementById(`progress-${i + 1}`);
        if (progressBar) {
            if (i < currentSectionIndex) {
                progressBar.style.width = '100%';
            } else if (i === currentSectionIndex) {
                const section = scriptData.sections[i];
                const progress = (currentLineIndex / section.script_lines.length) * 100;
                progressBar.style.width = `${progress}%`;
            } else {
                progressBar.style.width = '0%';
            }
        }
    }
}

// Fullscreen functions
function enterFullscreen() {
    const webcamContainer = document.querySelector('.webcam-container');

    if (webcamContainer.requestFullscreen) {
        webcamContainer.requestFullscreen();
    } else if (webcamContainer.webkitRequestFullscreen) {
        webcamContainer.webkitRequestFullscreen();
    } else if (webcamContainer.mozRequestFullScreen) {
        webcamContainer.mozRequestFullScreen();
    } else if (webcamContainer.msRequestFullscreen) {
        webcamContainer.msRequestFullscreen();
    }

    console.log('Entered fullscreen mode');
}

function exitFullscreen() {
    if (document.exitFullscreen) {
        document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
    } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
    } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
    }

    console.log('Exited fullscreen mode');
}

// Save metadata
async function saveMetadata(event) {
    event.preventDefault();

    const metadata = {
        video_filename: document.getElementById('video-filename').value,
        recording_date: new Date().toISOString().split('T')[0],
        duration_seconds: seconds,
        customer_details: {
            name: document.getElementById('customer-name').value || '',
            pan_number: document.getElementById('pan-number').value || '',
            aadhaar_last_4: document.getElementById('aadhaar-last4').value || ''
        },
        documents_shown: {
            pan_card: document.getElementById('doc-pan').checked,
            aadhaar_card: document.getElementById('doc-aadhaar').checked,
            aadhaar_masked: document.getElementById('doc-aadhaar-masked').checked
        },
        captured_images: capturedImages.map(img => ({
            type: img.type,
            timestamp: img.timestamp
        })),
        consent_given: document.querySelector('input[name="consent"]:checked')?.value === 'true',
        script_followed: true,
        notes: document.getElementById('notes').value || ''
    };

    try {
        const response = await fetch('/api/save-metadata', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(metadata)
        });

        const result = await response.json();

        if (result.success) {
            alert('Metadata saved successfully!\n\nFile: ' + result.file + '\n\nYou can now record another video or close this page.');
        } else {
            alert('Error saving metadata: ' + result.error);
        }
    } catch (error) {
        console.error('Error saving metadata:', error);
        alert('Error saving metadata. Check console for details.');
    }
}
