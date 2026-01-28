// Recording Assistant JavaScript - Simplified

let timerInterval = null;
let seconds = 0;
let isRecording = false;

// Recording variables
let mediaRecorder = null;
let recordedChunks = [];
let stream = null;
let videoBlob = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    checkBrowserSupport();
    initializeWebcam();
    setupEventListeners();
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
        const overlay = document.getElementById('camera-status');

        video.srcObject = stream;
        video.play();

        // Hide overlay when camera is ready
        overlay.style.display = 'none';

        console.log('Webcam initialized');
    } catch (error) {
        console.error('Error accessing webcam:', error);
        alert('Could not access webcam. Please allow camera and microphone permissions and refresh the page.');
    }
}

// Setup event listeners
function setupEventListeners() {
    const startBtn = document.getElementById('start-recording-btn');
    const stopBtn = document.getElementById('stop-recording-btn');

    if (startBtn) {
        startBtn.addEventListener('click', startRecording);
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', stopRecording);
    }
}

// Start recording
async function startRecording() {
    if (!stream) {
        alert('Please allow webcam access first and refresh the page.');
        return;
    }

    try {
        recordedChunks = [];

        // Create media recorder
        const options = { mimeType: 'video/webm;codecs=vp9' };

        // Check if the mimeType is supported, fallback if needed
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options.mimeType = 'video/webm';
        }

        mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = () => {
            videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
            console.log('Recording stopped. Blob size:', videoBlob.size);

            // Auto-download the video
            downloadVideo();
        };

        mediaRecorder.start();
        isRecording = true;

        // Update UI
        const startBtn = document.getElementById('start-recording-btn');
        const stopBtn = document.getElementById('stop-recording-btn');

        startBtn.style.display = 'none';
        stopBtn.style.display = 'inline-flex';

        // Start timer
        seconds = 0;
        timerInterval = setInterval(updateTimer, 1000);

        console.log('Recording started');
    } catch (error) {
        console.error('Error starting recording:', error);
        alert('Could not start recording: ' + error.message);
    }
}

// Stop recording
function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;

        clearInterval(timerInterval);

        // Update UI
        const startBtn = document.getElementById('start-recording-btn');
        const stopBtn = document.getElementById('stop-recording-btn');

        startBtn.style.display = 'inline-flex';
        stopBtn.style.display = 'none';

        console.log('Recording stopped');
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
    alert('Recording saved as: ' + filename);

    // Reset for next recording
    videoBlob = null;
    recordedChunks = [];
    seconds = 0;
    updateTimerDisplay();
}

// Timer functions
function updateTimer() {
    seconds++;
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        timerElement.textContent =
            `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
}
