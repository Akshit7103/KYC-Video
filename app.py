"""
Video KYC Recording Assistant & AI Checker
Flask application for recording guidance and video analysis
"""

from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
import threading
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'data/videos'
app.config['DOCUMENTS_FOLDER'] = 'data/documents'
app.config['ANALYSIS_FOLDER'] = 'outputs/analysis'

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOCUMENTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['ANALYSIS_FOLDER'], exist_ok=True)
os.makedirs('outputs/reports', exist_ok=True)
os.makedirs('outputs/status', exist_ok=True)

# Store analysis status (file-based to survive restarts)
STATUS_DIR = 'outputs/status'


def save_status(analysis_id, status_data):
    """Save analysis status to file"""
    status_file = os.path.join(STATUS_DIR, f"{analysis_id}.json")
    with open(status_file, 'w') as f:
        json.dump(status_data, f, indent=2)


def load_status(analysis_id):
    """Load analysis status from file"""
    status_file = os.path.join(STATUS_DIR, f"{analysis_id}.json")
    if os.path.exists(status_file):
        with open(status_file, 'r') as f:
            return json.load(f)
    return None


def get_all_status():
    """Get all analysis statuses"""
    statuses = {}
    for filename in os.listdir(STATUS_DIR):
        if filename.endswith('.json'):
            analysis_id = filename[:-5]
            statuses[analysis_id] = load_status(analysis_id)
    return statuses


@app.route('/')
def index():
    """Landing page with options"""
    return render_template('index.html')


@app.route('/recording-assistant')
def recording_assistant():
    """Interactive script display for recording assistance"""
    return render_template('recording_assistant.html')


@app.route('/api/get-script')
def get_script():
    """API endpoint to get KYC script"""
    try:
        with open('data/scripts/rbi_kyc_script.json', 'r', encoding='utf-8') as f:
            script_data = json.load(f)
        return jsonify(script_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-case-templates')
def get_case_templates():
    """Get recording case templates"""
    cases = [
        {
            'id': 'case1',
            'name': 'Case 1: Genuine - Approval',
            'description': 'Everything goes smoothly, customer cooperates fully',
            'expected_outcome': 'PASS',
            'duration': '5-7 minutes',
            'customer_behavior': 'Cooperative, answers all questions clearly, shows documents properly',
            'special_instructions': 'Follow script exactly, customer should be natural and professional'
        },
        {
            'id': 'case2',
            'name': 'Case 2: Genuine with Minor Issues',
            'description': 'Minor hesitation or technical issues but overall cooperative',
            'expected_outcome': 'PASS (with minor flags)',
            'duration': '6-8 minutes',
            'customer_behavior': 'Mostly cooperative, slight hesitation on 1-2 questions, minor tech issues',
            'special_instructions': 'Include slight camera adjustment or brief pause mid-call'
        },
        {
            'id': 'case3',
            'name': 'Case 3: Suspicious Behavior',
            'description': 'Customer shows red flags but doesn\'t fail outright',
            'expected_outcome': 'FLAG for manual review',
            'duration': '7-10 minutes',
            'customer_behavior': 'Defensive, asks "why do you need this?", interrupts agent, evasive',
            'special_instructions': 'Customer should be subtly suspicious, not over-the-top'
        },
        {
            'id': 'case4',
            'name': 'Case 4: Fake Video / Replay',
            'description': 'Pre-recorded video played back on screen',
            'expected_outcome': 'REJECT (Liveness failed)',
            'duration': '5-7 minutes',
            'customer_behavior': 'Video responses don\'t match questions, screen patterns visible',
            'special_instructions': 'Record genuine video first, then replay it on another screen and film that'
        },
        {
            'id': 'case5',
            'name': 'Case 5: Non-Compliant Documents',
            'description': 'Unmasked Aadhaar or refuses to show documents',
            'expected_outcome': 'REJECT (Document verification failed)',
            'duration': '3-5 minutes',
            'customer_behavior': 'Shows unmasked Aadhaar (not redacted) OR refuses to show PAN',
            'special_instructions': 'Show Aadhaar without masking number OR refuse to show documents'
        },
        {
            'id': 'case6',
            'name': 'Case 6: Not Attending Independently',
            'description': 'Customer not in India OR someone is assisting them',
            'expected_outcome': 'REJECT (Critical compliance failure)',
            'duration': '1-3 minutes',
            'customer_behavior': 'Says they are not in India OR someone is helping/prompting them',
            'special_instructions': 'Customer answers "No" to India presence or independence questions'
        }
    ]
    return jsonify(cases)


@app.route('/api/save-metadata', methods=['POST'])
def save_metadata():
    """Save video metadata after recording"""
    try:
        metadata = request.json
        filename = metadata.get('video_filename', '').replace('.mp4', '.json')

        if not filename:
            return jsonify({'error': 'No filename provided'}), 400

        filepath = os.path.join('data/videos', filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'file': filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/save-captures', methods=['POST'])
def save_captures():
    """Save captured document images (PAN/Aadhaar)"""
    try:
        import base64

        data = request.json
        images = data.get('images', [])
        timestamp = data.get('timestamp', datetime.now().timestamp())

        # Ensure captures folder exists
        captures_folder = 'data/captures'
        os.makedirs(captures_folder, exist_ok=True)

        saved_files = []

        for img in images:
            img_type = img.get('type', 'unknown')
            img_timestamp = img.get('timestamp', timestamp)
            img_data = img.get('data', '')

            if not img_data:
                continue

            # Remove data URL prefix (data:image/png;base64,)
            if ',' in img_data:
                img_data = img_data.split(',')[1]

            # Decode base64
            img_bytes = base64.b64decode(img_data)

            # Create filename
            filename = f"{img_type}_{img_timestamp}.png"
            filepath = os.path.join(captures_folder, filename)

            # Save image
            with open(filepath, 'wb') as f:
                f.write(img_bytes)

            saved_files.append(filename)
            print(f"Saved captured image: {filename}")

        return jsonify({'success': True, 'files': saved_files})
    except Exception as e:
        print(f"Error saving captures: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/upload')
def upload_page():
    """Video upload page"""
    return render_template('upload.html')


@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Handle video file upload"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        video = request.files['video']
        if video.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save video
        filename = video.filename
        video.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Handle document uploads if provided
        documents = []
        for key in request.files:
            if key.startswith('document_'):
                doc = request.files[key]
                if doc.filename:
                    doc_path = os.path.join(app.config['DOCUMENTS_FOLDER'], doc.filename)
                    doc.save(doc_path)
                    documents.append(doc.filename)

        return jsonify({
            'success': True,
            'video_file': filename,
            'documents': documents
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/convert-to-mp4', methods=['POST'])
def convert_to_mp4():
    """Convert uploaded WebM video to MP4"""
    try:
        import subprocess

        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        video = request.files['video']
        if video.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Save the WebM file temporarily
        webm_filename = video.filename
        webm_path = os.path.join(app.config['UPLOAD_FOLDER'], webm_filename)
        video.save(webm_path)

        # Create MP4 filename
        mp4_filename = webm_filename.replace('.webm', '.mp4')
        mp4_path = os.path.join(app.config['UPLOAD_FOLDER'], mp4_filename)

        # Convert using FFmpeg
        try:
            subprocess.run([
                'ffmpeg', '-i', webm_path,
                '-c:v', 'libx264',  # H.264 video codec
                '-preset', 'fast',   # Fast encoding
                '-crf', '23',        # Quality (lower = better, 23 is good)
                '-c:a', 'aac',       # AAC audio codec
                '-b:a', '128k',      # Audio bitrate
                '-movflags', '+faststart',  # Enable streaming
                '-y',                # Overwrite output file
                mp4_path
            ], check=True, capture_output=True)

            # Remove the WebM file after successful conversion
            os.remove(webm_path)

            return jsonify({
                'success': True,
                'filename': mp4_filename,
                'message': 'Video converted to MP4 successfully'
            })

        except subprocess.CalledProcessError as e:
            # If FFmpeg fails, keep the WebM file
            return jsonify({
                'success': False,
                'error': 'FFmpeg conversion failed. Please ensure FFmpeg is installed.',
                'details': e.stderr.decode() if e.stderr else str(e)
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download-converted/<filename>')
def download_converted(filename):
    """Download converted MP4 file"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404


@app.route('/analyze')
def analyze_page():
    """Video analysis interface"""
    return render_template('analyze.html')


@app.route('/api/list-videos')
def list_videos():
    """List all uploaded videos"""
    try:
        videos = []
        video_extensions = ('.mp4', '.webm', '.avi', '.mov')

        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.lower().endswith(video_extensions):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                base_name = os.path.splitext(filename)[0]
                metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{base_name}.json")

                video_info = {
                    'filename': filename,
                    'size': os.path.getsize(filepath),
                    'size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2),
                    'uploaded': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat(),
                    'has_metadata': os.path.exists(metadata_path)
                }

                # Load metadata if exists
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        video_info['metadata'] = json.load(f)

                videos.append(video_info)

        # Sort by upload time (newest first)
        videos.sort(key=lambda x: x['uploaded'], reverse=True)

        return jsonify(videos)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/list-documents')
def list_documents():
    """List all uploaded document images"""
    try:
        documents = []
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif')

        if os.path.exists(app.config['DOCUMENTS_FOLDER']):
            for filename in os.listdir(app.config['DOCUMENTS_FOLDER']):
                if filename.lower().endswith(image_extensions):
                    filepath = os.path.join(app.config['DOCUMENTS_FOLDER'], filename)
                    documents.append({
                        'filename': filename,
                        'size': os.path.getsize(filepath),
                        'uploaded': datetime.fromtimestamp(os.path.getctime(filepath)).isoformat()
                    })

        documents.sort(key=lambda x: x['uploaded'], reverse=True)
        return jsonify(documents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze-video', methods=['POST'])
def analyze_video():
    """Start video analysis in background"""
    try:
        data = request.json
        video_filename = data.get('video_filename')
        reference_image = data.get('reference_image')
        whisper_model = data.get('whisper_model', 'base')

        if not video_filename:
            return jsonify({'error': 'No video filename provided'}), 400

        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)

        if not os.path.exists(video_path):
            return jsonify({'error': f'Video not found: {video_filename}'}), 404

        # Create analysis ID
        analysis_id = f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.path.splitext(video_filename)[0]}"

        # Initialize status and save to file
        status_data = {
            'status': 'starting',
            'progress': 0,
            'stage': 'Initializing...',
            'video_filename': video_filename,
            'started_at': datetime.now().isoformat()
        }
        save_status(analysis_id, status_data)

        # Reference image path
        reference_path = None
        if reference_image:
            reference_path = os.path.join(app.config['DOCUMENTS_FOLDER'], reference_image)
            if not os.path.exists(reference_path):
                reference_path = None

        # Start analysis in background thread
        thread = threading.Thread(
            target=run_analysis_background,
            args=(analysis_id, video_path, reference_path, whisper_model)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'message': 'Analysis started'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/analysis-status/<analysis_id>')
def get_analysis_status(analysis_id):
    """Get status of running analysis"""
    status_data = load_status(analysis_id)
    if not status_data:
        return jsonify({'error': 'Analysis not found'}), 404

    return jsonify(status_data)


@app.route('/api/analysis-result/<analysis_id>')
def get_analysis_result(analysis_id):
    """Get completed analysis result"""
    status_data = load_status(analysis_id)
    if not status_data:
        return jsonify({'error': 'Analysis not found'}), 404

    if status_data['status'] != 'completed':
        return jsonify({'error': 'Analysis not completed yet'}), 400

    # Load result from file
    result_path = status_data.get('result_path')
    if result_path and os.path.exists(result_path):
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        return jsonify(result)
    else:
        return jsonify({'error': 'Result file not found'}), 404


@app.route('/results/<analysis_id>')
def view_results(analysis_id):
    """View analysis results page"""
    status_data = load_status(analysis_id)
    if not status_data:
        return "Analysis not found", 404

    if status_data['status'] != 'completed':
        return "Analysis not completed yet", 400

    return render_template('results.html', analysis_id=analysis_id)


@app.route('/api/get-results/<analysis_id>')
def get_results(analysis_id):
    """Get analysis results as JSON"""
    try:
        # Load status to get the result path
        status_data = load_status(analysis_id)
        if not status_data:
            return jsonify({'error': 'Analysis not found'}), 404

        if status_data['status'] != 'completed':
            return jsonify({'error': 'Analysis not completed yet'}), 400

        # Get the result path from status
        result_path = status_data.get('result_path')
        if not result_path or not os.path.exists(result_path):
            return jsonify({'error': 'Results file not found'}), 404

        # Read the JSON report
        with open(result_path, 'r', encoding='utf-8') as f:
            results = json.load(f)

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download-report/<analysis_id>')
def download_report(analysis_id):
    """Download the full JSON report"""
    try:
        # Load status to get the result path
        status_data = load_status(analysis_id)
        if not status_data:
            return jsonify({'error': 'Analysis not found'}), 404

        if status_data['status'] != 'completed':
            return jsonify({'error': 'Analysis not completed yet'}), 400

        # Get the result path from status
        result_path = status_data.get('result_path')
        if not result_path or not os.path.exists(result_path):
            return jsonify({'error': 'Results file not found'}), 404

        # Get directory and filename
        directory = os.path.dirname(result_path)
        filename = os.path.basename(result_path)

        return send_from_directory(directory, filename, as_attachment=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def run_analysis_background(analysis_id, video_path, reference_path, whisper_model):
    """Run video analysis in background thread"""
    try:
        # Load current status
        status_data = load_status(analysis_id)

        # Update status
        status_data['status'] = 'running'
        status_data['progress'] = 10
        status_data['stage'] = 'Loading analysis modules...'
        save_status(analysis_id, status_data)

        # Import analyzer (lazy load to avoid startup delay)
        from modules.video_analyzer import VideoAnalyzer

        status_data['progress'] = 20
        status_data['stage'] = 'Initializing analyzer...'
        save_status(analysis_id, status_data)

        # Create analyzer
        analyzer = VideoAnalyzer(output_base_dir=app.config['ANALYSIS_FOLDER'])

        status_data['progress'] = 30
        status_data['stage'] = 'Starting analysis pipeline...'
        save_status(analysis_id, status_data)

        # Progress callback - saves to file each time
        def update_progress(progress, stage):
            status_data['progress'] = progress
            status_data['stage'] = stage
            save_status(analysis_id, status_data)
            print(f"[{analysis_id}] {progress}% - {stage}")

        # Run analysis with progress callback
        results = analyzer.analyze(
            video_path=video_path,
            reference_face_path=reference_path,
            whisper_model=whisper_model,
            progress_callback=update_progress
        )

        status_data['progress'] = 100
        status_data['status'] = 'completed'
        status_data['stage'] = 'Analysis complete!'
        status_data['completed_at'] = datetime.now().isoformat()

        # Store result paths
        status_data['result_path'] = results.get('report_paths', {}).get('json')
        status_data['html_path'] = results.get('report_paths', {}).get('html')
        status_data['output_directory'] = results.get('output_directory')

        # Store summary
        decision = results.get('decision', {})
        status_data['summary'] = {
            'decision': decision.get('decision', 'UNKNOWN'),
            'score': decision.get('final_score', 0),
            'reason': decision.get('decision_reason', ''),
            'processing_time': results.get('total_time_seconds', 0)
        }

        # Save final status
        save_status(analysis_id, status_data)

    except Exception as e:
        # Load status and update with error
        status_data = load_status(analysis_id) or {}
        status_data['status'] = 'error'
        status_data['error'] = str(e)
        status_data['stage'] = f'Error: {str(e)}'
        save_status(analysis_id, status_data)

        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()


@app.route('/outputs/analysis/<path:filename>')
def serve_analysis_output(filename):
    """Serve analysis output files (HTML reports, images, etc.)"""
    return send_from_directory(app.config['ANALYSIS_FOLDER'], filename)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  VIDEO KYC RECORDING ASSISTANT")
    print("="*60)
    print("\nStarting Flask application...")
    print("\nAccess the application at: http://localhost:5000")
    print("\nAvailable routes:")
    print("  - /                    : Home page")
    print("  - /recording-assistant : Script guidance for recording")
    print("  - /upload             : Upload recorded videos")
    print("  - /analyze            : Analyze videos with AI")
    print("\n" + "="*60 + "\n")

    # IMPORTANT: Disable auto-reload to prevent analysis interruption
    # Auto-reload kills background analysis threads when it detects file changes
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
