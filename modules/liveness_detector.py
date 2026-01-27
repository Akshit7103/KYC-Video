"""
Liveness Detector Module
Detects if video is genuine (live person) or fake (replay/screen/deepfake)
RBI Mandatory: Must verify person is physically present
"""

import os
import cv2
import numpy as np
import json
from collections import defaultdict


class LivenessDetector:
    """
    Liveness detection for Video KYC verification.
    Detects replay attacks, screen recordings, and deepfakes.
    """

    def __init__(self):
        """Initialize liveness detector"""
        print("Initializing Liveness Detector...")

        # Load face and eye detectors
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )

        # Liveness check thresholds
        self.thresholds = {
            'blink_ear_threshold': 0.25,  # Eye aspect ratio for blink
            'motion_threshold': 5.0,       # Minimum motion for liveness
            'texture_threshold': 50,       # Texture variance threshold
            'moire_threshold': 0.5,        # Moiré pattern detection (relaxed to reduce false positives)
        }

        print("  Liveness detector initialized")

    def detect_blinks(self, frames, timestamps=None):
        """
        Detect eye blinks in video frames

        Args:
            frames: List of frame paths or numpy arrays
            timestamps: Optional list of timestamps

        Returns:
            Dictionary with blink detection results
        """
        print("Analyzing blink patterns...")

        blink_events = []
        eye_states = []  # Track eyes open/closed

        for i, frame_input in enumerate(frames):
            # Load frame
            if isinstance(frame_input, str):
                frame = cv2.imread(frame_input)
            else:
                frame = frame_input

            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))

            if len(faces) == 0:
                eye_states.append({'frame': i, 'eyes_detected': False})
                continue

            # Get largest face
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi_gray = gray[y:y+h, x:x+w]

            # Detect eyes in face region (relaxed parameters for better detection)
            eyes = self.eye_cascade.detectMultiScale(face_roi_gray, 1.05, 2, minSize=(20, 20))

            # More lenient eye detection - even 1 eye visible is "open"
            eyes_count = len(eyes)
            eyes_open = eyes_count >= 1

            eye_states.append({
                'frame': i,
                'timestamp': timestamps[i] if timestamps else i,
                'eyes_detected': True,
                'eyes_count': eyes_count,
                'eyes_open': eyes_open
            })

            # Detect blink - look for significant drops in eye count
            if len(eye_states) >= 2:
                prev_state = eye_states[-2]
                curr_state = eye_states[-1]

                prev_count = prev_state.get('eyes_count', 0)
                curr_count = curr_state.get('eyes_count', 0)

                # Blink detected if: eyes go from visible to not visible, or count drops significantly
                if prev_count >= 1 and curr_count == 0:
                    blink_events.append({
                        'frame': i,
                        'timestamp': timestamps[i] if timestamps else i,
                        'type': 'blink_start'
                    })
                elif prev_count == 0 and curr_count >= 1:
                    blink_events.append({
                        'frame': i,
                        'timestamp': timestamps[i] if timestamps else i,
                        'type': 'blink_end'
                    })
                # Also detect partial blinks (eye count drops from 2 to 1)
                elif prev_count == 2 and curr_count == 1:
                    blink_events.append({
                        'frame': i,
                        'timestamp': timestamps[i] if timestamps else i,
                        'type': 'blink_partial'
                    })

        # Calculate blink rate (include partial blinks)
        full_blinks = len([e for e in blink_events if e['type'] == 'blink_start'])
        blink_ends = len([e for e in blink_events if e['type'] == 'blink_end'])
        partial_blinks = len([e for e in blink_events if e['type'] == 'blink_partial'])

        # If we have blink_end events without corresponding starts, count them as blinks
        # (this can happen if video starts with eyes closed or detection is inconsistent)
        if blink_ends > full_blinks:
            full_blinks = blink_ends

        total_blinks = full_blinks + (partial_blinks // 2)  # Count 2 partial blinks as 1 full

        duration = timestamps[-1] if timestamps else len(frames)
        blink_rate = (total_blinks / duration * 60) if duration > 0 else 0  # blinks per minute

        result = {
            'total_blinks': total_blinks,
            'full_blinks': full_blinks,
            'partial_blinks': partial_blinks,
            'blink_rate_per_minute': blink_rate,
            'blink_events': blink_events,
            'frames_analyzed': len(frames),
            'natural_blink_pattern': 5 <= blink_rate <= 40,  # Relaxed range: 5-40 bpm
            'liveness_indicator': total_blinks >= 2  # At least 2 blinks indicates liveness (lowered from 3)
        }

        print(f"  Detected {total_blinks} blinks ({blink_rate:.1f} per minute)")
        print(f"  Natural pattern: {'Yes' if result['natural_blink_pattern'] else 'No'}")

        return result

    def detect_head_movement(self, frames, timestamps=None):
        """
        Detect head movements (turn left/right, up/down)

        Args:
            frames: List of frame paths or numpy arrays
            timestamps: Optional timestamps

        Returns:
            Dictionary with head movement analysis
        """
        print("Analyzing head movements...")

        face_positions = []
        movements = []

        for i, frame_input in enumerate(frames):
            if isinstance(frame_input, str):
                frame = cv2.imread(frame_input)
            else:
                frame = frame_input

            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))

            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                center_x = x + w // 2
                center_y = y + h // 2

                face_positions.append({
                    'frame': i,
                    'timestamp': timestamps[i] if timestamps else i,
                    'center_x': center_x,
                    'center_y': center_y,
                    'width': w,
                    'height': h
                })

                # Detect movement from previous frame
                if len(face_positions) >= 2:
                    prev = face_positions[-2]
                    curr = face_positions[-1]

                    dx = curr['center_x'] - prev['center_x']
                    dy = curr['center_y'] - prev['center_y']

                    if abs(dx) > 10:  # Horizontal movement
                        direction = 'right' if dx > 0 else 'left'
                        movements.append({
                            'frame': i,
                            'timestamp': timestamps[i] if timestamps else i,
                            'direction': direction,
                            'magnitude': abs(dx)
                        })

                    if abs(dy) > 10:  # Vertical movement
                        direction = 'down' if dy > 0 else 'up'
                        movements.append({
                            'frame': i,
                            'timestamp': timestamps[i] if timestamps else i,
                            'direction': direction,
                            'magnitude': abs(dy)
                        })

        # Analyze movement patterns
        left_moves = sum(1 for m in movements if m['direction'] == 'left')
        right_moves = sum(1 for m in movements if m['direction'] == 'right')
        up_moves = sum(1 for m in movements if m['direction'] == 'up')
        down_moves = sum(1 for m in movements if m['direction'] == 'down')

        total_movement = sum(m['magnitude'] for m in movements)

        result = {
            'total_movements': len(movements),
            'left_movements': left_moves,
            'right_movements': right_moves,
            'up_movements': up_moves,
            'down_movements': down_moves,
            'total_magnitude': total_movement,
            'has_horizontal_movement': left_moves > 0 or right_moves > 0,
            'has_vertical_movement': up_moves > 0 or down_moves > 0,
            'liveness_indicator': len(movements) >= 5  # Some natural movement
        }

        print(f"  Detected {len(movements)} movements")
        print(f"  Horizontal: L={left_moves}, R={right_moves}")
        print(f"  Vertical: U={up_moves}, D={down_moves}")

        return result

    def detect_screen_replay(self, frames):
        """
        Detect if video is a screen replay (moiré patterns, unnatural lighting)

        Args:
            frames: List of frame paths or numpy arrays

        Returns:
            Dictionary with screen detection results
        """
        print("Analyzing for screen replay attacks...")

        moire_scores = []
        edge_artifacts = []
        lighting_uniformity = []

        for i, frame_input in enumerate(frames):
            if isinstance(frame_input, str):
                frame = cv2.imread(frame_input)
            else:
                frame = frame_input

            if frame is None:
                continue

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. Detect moiré patterns (high-frequency artifacts)
            # Apply FFT to detect periodic patterns
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.abs(f_shift)

            # High frequency energy ratio (screens have characteristic patterns)
            h, w = magnitude.shape
            center_h, center_w = h // 2, w // 2
            mask_size = min(h, w) // 4

            # Low frequency region
            low_freq = magnitude[center_h-mask_size:center_h+mask_size,
                                center_w-mask_size:center_w+mask_size]
            # High frequency is everything else
            high_freq_energy = np.sum(magnitude) - np.sum(low_freq)
            total_energy = np.sum(magnitude)

            moire_score = high_freq_energy / total_energy if total_energy > 0 else 0
            moire_scores.append(moire_score)

            # 2. Detect edge artifacts (screen bezels)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            edge_artifacts.append(edge_density)

            # 3. Check lighting uniformity (screens have uniform backlight)
            h_blocks, w_blocks = 3, 3
            block_h, block_w = gray.shape[0] // h_blocks, gray.shape[1] // w_blocks
            block_means = []

            for bi in range(h_blocks):
                for bj in range(w_blocks):
                    block = gray[bi*block_h:(bi+1)*block_h, bj*block_w:(bj+1)*block_w]
                    block_means.append(np.mean(block))

            lighting_var = np.std(block_means)
            lighting_uniformity.append(lighting_var)

        # Analyze results
        avg_moire = np.mean(moire_scores) if moire_scores else 0
        avg_edges = np.mean(edge_artifacts) if edge_artifacts else 0
        avg_lighting_var = np.mean(lighting_uniformity) if lighting_uniformity else 0

        # Screen replay indicators - require multiple factors to reduce false positives
        # Only flag as screen replay if BOTH moire and lighting are suspicious,
        # OR if moire is extremely high (>0.7)
        is_screen_replay = (
            (avg_moire > self.thresholds['moire_threshold'] and avg_lighting_var < 10) or
            avg_moire > 0.7  # Extremely high moire = definite screen
        )

        result = {
            'average_moire_score': float(avg_moire),
            'average_edge_density': float(avg_edges),
            'average_lighting_variance': float(avg_lighting_var),
            'screen_replay_detected': is_screen_replay,
            'confidence': 'HIGH' if not is_screen_replay else 'LOW',
            'liveness_indicator': not is_screen_replay,
            'analysis': {
                'moire_check': 'PASS' if avg_moire <= self.thresholds['moire_threshold'] else 'FAIL',
                'lighting_check': 'PASS' if avg_lighting_var >= 10 else 'SUSPICIOUS'
            }
        }

        print(f"  Moiré score: {avg_moire:.4f} ({'SUSPICIOUS' if avg_moire > 0.3 else 'OK'})")
        print(f"  Lighting variance: {avg_lighting_var:.2f} ({'OK' if avg_lighting_var >= 10 else 'SUSPICIOUS'})")
        print(f"  Screen replay detected: {'Yes' if is_screen_replay else 'No'}")

        return result

    def detect_texture_analysis(self, frames):
        """
        Analyze skin texture to detect printed photos or deepfakes

        Args:
            frames: List of frame paths

        Returns:
            Texture analysis results
        """
        print("Analyzing facial texture...")

        texture_scores = []

        for frame_input in frames:
            if isinstance(frame_input, str):
                frame = cv2.imread(frame_input)
            else:
                frame = frame_input

            if frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect face
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))

            if len(faces) == 0:
                continue

            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = gray[y:y+h, x:x+w]

            # Calculate Local Binary Pattern (LBP) texture
            # Simplified version - calculate variance
            texture_variance = np.var(face_roi)

            # Calculate gradient magnitude (real skin has micro-textures)
            sobelx = cv2.Sobel(face_roi, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(face_roi, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
            avg_gradient = np.mean(gradient_magnitude)

            texture_scores.append({
                'variance': texture_variance,
                'gradient': avg_gradient
            })

        if not texture_scores:
            return {
                'texture_check': 'INCONCLUSIVE',
                'liveness_indicator': None,
                'error': 'No faces detected for texture analysis'
            }

        avg_variance = np.mean([t['variance'] for t in texture_scores])
        avg_gradient = np.mean([t['gradient'] for t in texture_scores])

        # Real faces have more texture variation than printed/screen photos
        is_real_texture = avg_variance > self.thresholds['texture_threshold']

        result = {
            'average_variance': float(avg_variance),
            'average_gradient': float(avg_gradient),
            'texture_check': 'PASS' if is_real_texture else 'SUSPICIOUS',
            'liveness_indicator': is_real_texture
        }

        print(f"  Texture variance: {avg_variance:.2f}")
        print(f"  Gradient magnitude: {avg_gradient:.2f}")
        print(f"  Real texture: {'Yes' if is_real_texture else 'Suspicious'}")

        return result

    def analyze_liveness(self, frames_dir, timestamps=None):
        """
        Comprehensive liveness analysis

        Args:
            frames_dir: Directory containing extracted frames
            timestamps: Optional list of timestamps

        Returns:
            Complete liveness analysis results
        """
        print(f"\n{'='*60}")
        print("LIVENESS ANALYSIS")
        print(f"{'='*60}")

        # Load frames
        frame_files = sorted([
            os.path.join(frames_dir, f)
            for f in os.listdir(frames_dir)
            if f.endswith(('.jpg', '.jpeg', '.png'))
        ])

        if not frame_files:
            return {
                'error': 'No frames found',
                'liveness_score': 0,
                'is_live': False
            }

        print(f"Analyzing {len(frame_files)} frames...")

        # Run all checks
        blink_results = self.detect_blinks(frame_files, timestamps)
        movement_results = self.detect_head_movement(frame_files, timestamps)
        screen_results = self.detect_screen_replay(frame_files)
        texture_results = self.detect_texture_analysis(frame_files)

        # Calculate liveness score
        scores = {
            'blink_score': 25 if blink_results['liveness_indicator'] else 0,
            'movement_score': 25 if movement_results['liveness_indicator'] else 0,
            'screen_score': 30 if screen_results['liveness_indicator'] else 0,
            'texture_score': 20 if texture_results.get('liveness_indicator', False) else 0
        }

        total_score = sum(scores.values())

        result = {
            'liveness_score': total_score,
            'is_live': total_score >= 60,
            'confidence': 'HIGH' if total_score >= 80 else 'MEDIUM' if total_score >= 60 else 'LOW',
            'passed': total_score >= 60,
            'component_scores': scores,
            'detailed_results': {
                'blink_analysis': blink_results,
                'movement_analysis': movement_results,
                'screen_replay_analysis': screen_results,
                'texture_analysis': texture_results
            }
        }

        print(f"\n{'='*60}")
        print("LIVENESS RESULT")
        print(f"{'='*60}")
        print(f"Score: {total_score}/100")
        print(f"  - Blink detection: {scores['blink_score']}/25")
        print(f"  - Head movement: {scores['movement_score']}/25")
        print(f"  - Screen replay check: {scores['screen_score']}/30")
        print(f"  - Texture analysis: {scores['texture_score']}/20")
        print(f"Is Live: {'YES' if result['is_live'] else 'NO'}")
        print(f"Confidence: {result['confidence']}")
        print(f"{'='*60}\n")

        return result

    def check_script_compliance(self, liveness_results, transcript):
        """
        Check if liveness actions match script instructions

        Args:
            liveness_results: Results from analyze_liveness
            transcript: Transcript with segments

        Returns:
            Dictionary with compliance check results
        """
        print(f"\nChecking liveness instruction compliance...")

        segments = transcript.get('segments', [])
        blink_analysis = liveness_results.get('detailed_results', {}).get('blink_analysis', {})
        movement_analysis = liveness_results.get('detailed_results', {}).get('movement_analysis', {})

        # Find liveness instruction timestamps in transcript
        blink_instruction_time = None
        turn_instruction_time = None
        smile_instruction_time = None

        for seg in segments:
            text_lower = seg.get('text', '').lower()
            timestamp = seg.get('start', 0)

            if 'blink' in text_lower:
                blink_instruction_time = timestamp
            if 'turn' in text_lower and ('face' in text_lower or 'head' in text_lower):
                turn_instruction_time = timestamp
            if 'smile' in text_lower:
                smile_instruction_time = timestamp

        # Check if actions happened after instructions
        compliance = {
            'blink_instruction_found': blink_instruction_time is not None,
            'blink_instruction_time': blink_instruction_time,
            'blink_action_detected': blink_analysis.get('total_blinks', 0) > 0,
            'turn_instruction_found': turn_instruction_time is not None,
            'turn_instruction_time': turn_instruction_time,
            'turn_action_detected': (
                movement_analysis.get('left_movements', 0) > 0 and
                movement_analysis.get('right_movements', 0) > 0
            ),
            'smile_instruction_found': smile_instruction_time is not None,
            'smile_instruction_time': smile_instruction_time
        }

        # Check timing correlation (action within 5 seconds after instruction)
        if blink_instruction_time and blink_analysis.get('blink_events'):
            blinks_after = [
                b for b in blink_analysis['blink_events']
                if b.get('timestamp', 0) > blink_instruction_time and
                   b.get('timestamp', 0) < blink_instruction_time + 5
            ]
            compliance['blink_followed_instruction'] = len(blinks_after) > 0
        else:
            compliance['blink_followed_instruction'] = False

        # Check if turns happened (left and right)
        compliance['both_turns_detected'] = (
            movement_analysis.get('left_movements', 0) > 0 and
            movement_analysis.get('right_movements', 0) > 0
        )

        # Overall compliance score
        checks_passed = sum([
            compliance['blink_action_detected'],
            compliance['turn_action_detected'],
            compliance['both_turns_detected']
        ])
        compliance['compliance_score'] = (checks_passed / 3) * 100

        print(f"  Blink instruction: {'Found' if compliance['blink_instruction_found'] else 'Not found'}")
        print(f"  Blink detected: {'Yes' if compliance['blink_action_detected'] else 'No'}")
        print(f"  Turn instruction: {'Found' if compliance['turn_instruction_found'] else 'Not found'}")
        print(f"  Both turns detected: {'Yes' if compliance['both_turns_detected'] else 'No'}")
        print(f"  Script compliance: {compliance['compliance_score']:.0f}%")

        return compliance

    def save_results(self, results, output_path):
        """Save liveness results to JSON"""
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

        print(f"Liveness results saved to: {output_path}")


def check_liveness(frames_dir, output_dir=None):
    """
    Convenience function to check liveness

    Args:
        frames_dir: Directory containing video frames
        output_dir: Optional directory to save results

    Returns:
        Liveness analysis results
    """
    detector = LivenessDetector()
    results = detector.analyze_liveness(frames_dir)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(output_dir, f'liveness_results_{timestamp}.json')
        detector.save_results(results, output_path)

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) >= 2:
        frames_dir = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else 'outputs/liveness'

        if os.path.exists(frames_dir):
            results = check_liveness(frames_dir, output_dir)
        else:
            print(f"Frames directory not found: {frames_dir}")
    else:
        print("Usage: python liveness_detector.py <frames_dir> [output_dir]")
