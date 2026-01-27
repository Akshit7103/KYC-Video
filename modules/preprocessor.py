"""
Preprocessor Module
Main orchestrator for video preprocessing - extracts frames, audio, and detects faces
"""

import os
import cv2
import json
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.video_processor import VideoProcessor
from processors.audio_processor import AudioProcessor


class Preprocessor:
    """
    Main preprocessing pipeline for Video KYC analysis.
    Extracts frames, audio, and detects faces in preparation for analysis modules.
    """

    def __init__(self, video_path, output_base_dir='outputs/analysis'):
        """
        Initialize preprocessor with video path

        Args:
            video_path: Path to the video file
            output_base_dir: Base directory for all outputs
        """
        self.video_path = video_path
        self.video_name = os.path.splitext(os.path.basename(video_path))[0]

        # Create timestamped output directory
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = os.path.join(output_base_dir, f"{self.video_name}_{timestamp}")

        # Sub-directories
        self.frames_dir = os.path.join(self.output_dir, 'frames')
        self.faces_dir = os.path.join(self.output_dir, 'faces')
        self.audio_dir = os.path.join(self.output_dir, 'audio')

        # Create directories
        for dir_path in [self.output_dir, self.frames_dir, self.faces_dir, self.audio_dir]:
            os.makedirs(dir_path, exist_ok=True)

        # Initialize processors
        self.video_processor = VideoProcessor(video_path)
        self.audio_processor = AudioProcessor(video_path)

        # Load face detector
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

        # Results storage
        self.results = {
            'video_path': video_path,
            'video_metadata': None,
            'output_directory': self.output_dir,
            'frames': [],
            'faces_detected': [],
            'audio_path': None,
            'processing_time': None
        }

        print(f"\n{'='*60}")
        print("PREPROCESSOR INITIALIZED")
        print(f"{'='*60}")
        print(f"Video: {video_path}")
        print(f"Output: {self.output_dir}")

    def process(self, frame_rate=1, extract_audio=True, detect_faces=True):
        """
        Run full preprocessing pipeline

        Args:
            frame_rate: Frames per second to extract (default: 1)
            extract_audio: Whether to extract audio
            detect_faces: Whether to detect faces in frames

        Returns:
            Dictionary with all preprocessing results
        """
        start_time = datetime.now()

        print(f"\n{'='*60}")
        print("STARTING PREPROCESSING PIPELINE")
        print(f"{'='*60}")

        # Step 1: Get video metadata
        print("\n[Step 1/4] Extracting video metadata...")
        self.results['video_metadata'] = self.video_processor.get_metadata()

        # Step 2: Extract frames
        print(f"\n[Step 2/4] Extracting frames at {frame_rate} FPS...")
        self.results['frames'] = self.video_processor.extract_frames(
            self.frames_dir,
            frame_rate=frame_rate
        )

        # Step 3: Extract audio
        if extract_audio:
            print("\n[Step 3/4] Extracting audio...")
            audio_output = os.path.join(self.audio_dir, f"{self.video_name}.wav")
            try:
                self.results['audio_path'] = self.audio_processor.extract_audio(audio_output)
            except Exception as e:
                print(f"Warning: Audio extraction failed: {e}")
                self.results['audio_path'] = None
        else:
            print("\n[Step 3/4] Skipping audio extraction...")

        # Step 4: Detect faces in frames
        if detect_faces:
            print("\n[Step 4/4] Detecting faces in frames...")
            self.results['faces_detected'] = self._detect_faces_in_frames()
        else:
            print("\n[Step 4/4] Skipping face detection...")

        # Calculate processing time
        end_time = datetime.now()
        self.results['processing_time'] = (end_time - start_time).total_seconds()

        # Save results
        self._save_results()

        # Print summary
        self._print_summary()

        return self.results

    def _detect_faces_in_frames(self):
        """
        Detect faces in all extracted frames

        Returns:
            List of face detection results per frame
        """
        face_results = []
        total_faces = 0

        for i, frame_info in enumerate(self.results['frames']):
            frame_path = frame_info['path']
            frame = cv2.imread(frame_path)

            if frame is None:
                continue

            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(50, 50)
            )

            frame_faces = []

            for j, (x, y, w, h) in enumerate(faces):
                # Extract face region with some padding
                padding = int(0.2 * min(w, h))
                y1 = max(0, y - padding)
                y2 = min(frame.shape[0], y + h + padding)
                x1 = max(0, x - padding)
                x2 = min(frame.shape[1], x + w + padding)

                face_img = frame[y1:y2, x1:x2]

                # Save face image
                face_filename = f"face_frame{i:05d}_face{j}.jpg"
                face_path = os.path.join(self.faces_dir, face_filename)
                cv2.imwrite(face_path, face_img)

                face_info = {
                    'face_id': j,
                    'path': face_path,
                    'bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)},
                    'confidence': None  # Haar doesn't provide confidence
                }

                frame_faces.append(face_info)
                total_faces += 1

            face_results.append({
                'frame_path': frame_path,
                'frame_number': frame_info['frame_number'],
                'timestamp': frame_info['timestamp'],
                'faces_count': len(faces),
                'faces': frame_faces
            })

            # Progress indicator
            if (i + 1) % 10 == 0 or i == len(self.results['frames']) - 1:
                print(f"  Processed {i + 1}/{len(self.results['frames'])} frames, found {total_faces} faces so far")

        print(f"  Total faces detected: {total_faces}")
        return face_results

    def detect_faces_dnn(self, frame):
        """
        Detect faces using DNN (more accurate but slower)
        Alternative to Haar cascade

        Args:
            frame: Input image

        Returns:
            List of face bounding boxes
        """
        # This requires downloading the DNN model files
        # For now, we use Haar cascade as fallback
        return self.face_cascade.detectMultiScale(
            cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(50, 50)
        )

    def get_frames_with_faces(self, min_faces=1):
        """
        Get frames that have at least min_faces detected

        Args:
            min_faces: Minimum number of faces required

        Returns:
            List of frame info dictionaries
        """
        return [
            f for f in self.results['faces_detected']
            if f['faces_count'] >= min_faces
        ]

    def get_best_face_frames(self, n=5):
        """
        Get the N frames with the largest/clearest faces
        (useful for face matching)

        Args:
            n: Number of frames to return

        Returns:
            List of frame info with largest faces
        """
        frames_with_faces = self.get_frames_with_faces(min_faces=1)

        # Sort by largest face (area = w * h)
        def get_largest_face_area(frame_info):
            if not frame_info['faces']:
                return 0
            return max(f['bbox']['w'] * f['bbox']['h'] for f in frame_info['faces'])

        sorted_frames = sorted(frames_with_faces, key=get_largest_face_area, reverse=True)

        return sorted_frames[:n]

    def _save_results(self):
        """Save preprocessing results to JSON"""
        results_path = os.path.join(self.output_dir, 'preprocessing_results.json')

        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {results_path}")

    def _print_summary(self):
        """Print preprocessing summary"""
        print(f"\n{'='*60}")
        print("PREPROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Video Duration: {self.results['video_metadata']['duration_formatted']}")
        print(f"Frames Extracted: {len(self.results['frames'])}")

        frames_with_faces = self.get_frames_with_faces()
        print(f"Frames with Faces: {len(frames_with_faces)}")

        total_faces = sum(f['faces_count'] for f in self.results['faces_detected'])
        print(f"Total Face Detections: {total_faces}")

        print(f"Audio Extracted: {'Yes' if self.results['audio_path'] else 'No'}")
        print(f"Processing Time: {self.results['processing_time']:.2f} seconds")
        print(f"Output Directory: {self.output_dir}")
        print(f"{'='*60}\n")

    def close(self):
        """Clean up resources"""
        self.video_processor.close()


def preprocess_video(video_path, output_dir='outputs/analysis', frame_rate=1):
    """
    Convenience function to preprocess a video

    Args:
        video_path: Path to video file
        output_dir: Base output directory
        frame_rate: Frames per second to extract

    Returns:
        Preprocessing results dictionary
    """
    preprocessor = Preprocessor(video_path, output_dir)
    results = preprocessor.process(frame_rate=frame_rate)
    preprocessor.close()
    return results


if __name__ == '__main__':
    # Test with a sample video
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = 'data/videos/sample.mp4'

    if os.path.exists(video_path):
        results = preprocess_video(video_path)
        print(f"\nPreprocessing complete. Results saved to: {results['output_directory']}")
    else:
        print(f"Video not found: {video_path}")
        print("Usage: python preprocessor.py <video_path>")
