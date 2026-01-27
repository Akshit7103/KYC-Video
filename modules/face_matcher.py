"""
Face Matcher Module
Compares faces from video with reference documents (Aadhaar/PAN)
RBI Mandatory: Must verify face in video matches government ID
"""

import os
import cv2
import numpy as np
import json
from datetime import datetime


class FaceMatcher:
    """
    Face matching module for Video KYC verification.
    Compares faces extracted from video with reference document photos.
    """

    def __init__(self, model_name='VGG-Face', detector_backend='opencv'):
        """
        Initialize face matcher

        Args:
            model_name: Face recognition model
                - 'VGG-Face': Good accuracy, moderate speed
                - 'Facenet': High accuracy
                - 'Facenet512': Highest accuracy
                - 'OpenFace': Fast, lower accuracy
                - 'DeepFace': Facebook's model
                - 'ArcFace': State-of-the-art accuracy
            detector_backend: Face detector
                - 'opencv': Fast, built-in
                - 'ssd': Good balance
                - 'mtcnn': High accuracy
                - 'retinaface': Best accuracy
        """
        self.model_name = model_name
        self.detector_backend = detector_backend
        self.deepface = None
        self.is_initialized = False

        print(f"Initializing Face Matcher...")
        print(f"  Model: {model_name}")
        print(f"  Detector: {detector_backend}")

        self._initialize()

    def _initialize(self):
        """Initialize DeepFace library"""
        try:
            from deepface import DeepFace
            self.deepface = DeepFace

            # Warm up the model by running a dummy comparison
            # This loads the model into memory
            print("  Loading face recognition model (first run may take time)...")

            self.is_initialized = True
            print("  Face matcher initialized successfully")

        except ImportError:
            print("DeepFace not installed. Installing...")
            import subprocess
            subprocess.check_call(['pip', 'install', 'deepface'])
            from deepface import DeepFace
            self.deepface = DeepFace
            self.is_initialized = True

        except Exception as e:
            print(f"Error initializing face matcher: {e}")
            self.is_initialized = False

    def extract_face(self, image_path, save_path=None):
        """
        Extract face from an image

        Args:
            image_path: Path to image
            save_path: Path to save extracted face (optional)

        Returns:
            Dictionary with face info and embedding
        """
        if not self.is_initialized:
            raise RuntimeError("Face matcher not initialized")

        try:
            # Extract face using DeepFace
            faces = self.deepface.extract_faces(
                img_path=image_path,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            if not faces:
                return {
                    'success': False,
                    'error': 'No face detected',
                    'image_path': image_path
                }

            # Get the largest/most confident face
            best_face = max(faces, key=lambda x: x.get('confidence', 0))

            result = {
                'success': True,
                'image_path': image_path,
                'face_region': best_face.get('facial_area', {}),
                'confidence': best_face.get('confidence', 0),
                'face_image': best_face.get('face', None)
            }

            # Save extracted face if path provided
            if save_path and result['face_image'] is not None:
                face_img = (best_face['face'] * 255).astype(np.uint8)
                face_img = cv2.cvtColor(face_img, cv2.COLOR_RGB2BGR)
                cv2.imwrite(save_path, face_img)
                result['saved_path'] = save_path

            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'image_path': image_path
            }

    def compare_faces(self, image1_path, image2_path, threshold=0.6):
        """
        Compare two face images

        Args:
            image1_path: Path to first image (reference - Aadhaar/PAN)
            image2_path: Path to second image (video frame)
            threshold: Matching threshold (lower = stricter)

        Returns:
            Dictionary with comparison results
        """
        if not self.is_initialized:
            raise RuntimeError("Face matcher not initialized")

        try:
            # Verify faces match
            result = self.deepface.verify(
                img1_path=image1_path,
                img2_path=image2_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=False
            )

            # Convert distance to similarity percentage
            distance = result.get('distance', 1.0)
            threshold_used = result.get('threshold', threshold)

            # Different models have different distance metrics
            # VGG-Face uses cosine distance (0-1, lower is better)
            similarity_score = max(0, (1 - distance)) * 100

            comparison_result = {
                'verified': result.get('verified', False),
                'distance': distance,
                'threshold': threshold_used,
                'similarity_score': similarity_score,
                'model': result.get('model', self.model_name),
                'detector': result.get('detector_backend', self.detector_backend),
                'image1': image1_path,
                'image2': image2_path,
                'facial_areas': result.get('facial_areas', {})
            }

            return comparison_result

        except Exception as e:
            return {
                'verified': False,
                'error': str(e),
                'similarity_score': 0,
                'image1': image1_path,
                'image2': image2_path
            }

    def compare_with_reference(self, reference_image_path, video_faces, top_n=5):
        """
        Compare reference document face with multiple video frame faces

        Args:
            reference_image_path: Path to Aadhaar/PAN face image
            video_faces: List of face paths from video frames
            top_n: Number of top matches to return

        Returns:
            Comprehensive matching results
        """
        print(f"\nComparing reference face with {len(video_faces)} video faces...")

        results = []

        for i, face_path in enumerate(video_faces):
            comparison = self.compare_faces(reference_image_path, face_path)

            results.append({
                'frame_face': face_path,
                'verified': comparison.get('verified', False),
                'similarity_score': comparison.get('similarity_score', 0),
                'distance': comparison.get('distance', 1.0),
                'error': comparison.get('error', None)
            })

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Compared {i + 1}/{len(video_faces)} faces")

        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x['similarity_score'], reverse=True)

        # Calculate statistics
        verified_count = sum(1 for r in results if r['verified'])
        avg_similarity = np.mean([r['similarity_score'] for r in results if r['error'] is None])
        max_similarity = max(r['similarity_score'] for r in results) if results else 0

        summary = {
            'reference_image': reference_image_path,
            'total_comparisons': len(results),
            'verified_matches': verified_count,
            'verification_rate': (verified_count / len(results) * 100) if results else 0,
            'average_similarity': avg_similarity,
            'max_similarity': max_similarity,
            'top_matches': results[:top_n],
            'all_results': results,
            'overall_match': verified_count > len(results) * 0.3,  # >30% matches
            'confidence': 'HIGH' if verified_count > len(results) * 0.5 else
                         'MEDIUM' if verified_count > len(results) * 0.3 else 'LOW'
        }

        print(f"\nFace Matching Summary:")
        print(f"  Verified matches: {verified_count}/{len(results)} ({summary['verification_rate']:.1f}%)")
        print(f"  Max similarity: {max_similarity:.1f}%")
        print(f"  Average similarity: {avg_similarity:.1f}%")
        print(f"  Confidence: {summary['confidence']}")

        return summary

    def get_face_score(self, reference_image_path, video_faces):
        """
        Get a single score (0-100) for face matching

        Args:
            reference_image_path: Path to reference (Aadhaar/PAN) face
            video_faces: List of face paths from video

        Returns:
            Score (0-100) and detailed results
        """
        results = self.compare_with_reference(reference_image_path, video_faces)

        # Calculate final score based on multiple factors
        # Weight: max similarity (40%) + average similarity (30%) + verification rate (30%)
        max_sim = results['max_similarity']
        avg_sim = results['average_similarity']
        ver_rate = results['verification_rate']

        final_score = (max_sim * 0.4) + (avg_sim * 0.3) + (ver_rate * 0.3)

        return {
            'score': round(final_score, 2),
            'max_similarity': max_sim,
            'average_similarity': avg_sim,
            'verification_rate': ver_rate,
            'confidence': results['confidence'],
            'passed': final_score >= 60,  # 60% threshold for pass
            'details': results
        }

    def save_results(self, results, output_path):
        """Save matching results to JSON"""
        # Convert numpy types to Python types for JSON serialization
        def convert_types(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(i) for i in obj]
            return obj

        clean_results = convert_types(results)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_results, f, indent=2, ensure_ascii=False)

        print(f"Face matching results saved to: {output_path}")


def match_faces(reference_image, video_faces_dir, output_dir=None):
    """
    Convenience function to match faces

    Args:
        reference_image: Path to Aadhaar/PAN face image
        video_faces_dir: Directory containing extracted video faces
        output_dir: Directory to save results

    Returns:
        Face matching score and results
    """
    matcher = FaceMatcher()

    # Get all face images from directory
    face_extensions = {'.jpg', '.jpeg', '.png'}
    video_faces = [
        os.path.join(video_faces_dir, f)
        for f in os.listdir(video_faces_dir)
        if os.path.splitext(f)[1].lower() in face_extensions
    ]

    if not video_faces:
        print(f"No face images found in {video_faces_dir}")
        return None

    # Get matching score
    result = matcher.get_face_score(reference_image, video_faces)

    # Save results if output_dir provided
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'face_match_results_{timestamp}.json')
        matcher.save_results(result, output_path)

    return result


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 3:
        reference_image = sys.argv[1]
        video_faces_dir = sys.argv[2]
        output_dir = sys.argv[3] if len(sys.argv) > 3 else 'outputs/face_matching'

        if os.path.exists(reference_image) and os.path.exists(video_faces_dir):
            result = match_faces(reference_image, video_faces_dir, output_dir)
            print(f"\n{'='*60}")
            print(f"FACE MATCHING RESULT")
            print(f"{'='*60}")
            print(f"Score: {result['score']}/100")
            print(f"Passed: {'YES' if result['passed'] else 'NO'}")
            print(f"Confidence: {result['confidence']}")
        else:
            print("Reference image or video faces directory not found")
    else:
        print("Usage: python face_matcher.py <reference_image> <video_faces_dir> [output_dir]")
