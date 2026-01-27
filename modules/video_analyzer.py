"""
Video Analyzer - Main Analysis Pipeline
Orchestrates all modules to analyze a Video KYC recording
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.preprocessor import Preprocessor
from modules.transcript_generator import TranscriptGenerator
from modules.liveness_detector import LivenessDetector
from modules.face_matcher import FaceMatcher
from modules.script_checker import ScriptChecker
from modules.behavior_analyzer import BehaviorAnalyzer
from engine.decision_engine import DecisionEngine
from engine.report_generator import ReportGenerator


class VideoAnalyzer:
    """
    Main Video KYC Analyzer Pipeline.
    Orchestrates all modules to analyze a video and produce a decision.
    """

    def __init__(self, output_base_dir='outputs/analysis'):
        """
        Initialize the video analyzer

        Args:
            output_base_dir: Base directory for all output files
        """
        self.output_base_dir = output_base_dir

        print("\n" + "="*70)
        print("  VIDEO KYC AI ANALYZER")
        print("  Initializing analysis pipeline...")
        print("="*70 + "\n")

        # Initialize all modules
        self.preprocessor = None  # Initialized per video
        self.transcript_generator = None
        self.liveness_detector = LivenessDetector()
        self.face_matcher = None  # Lazy load (heavy)
        self.script_checker = ScriptChecker()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.decision_engine = DecisionEngine()
        self.report_generator = ReportGenerator()

        print("\nAll modules initialized. Ready to analyze videos.\n")

    def analyze(self, video_path, reference_face_path=None, whisper_model='base', progress_callback=None):
        """
        Run complete analysis pipeline on a video

        Args:
            video_path: Path to the video file to analyze
            reference_face_path: Path to reference face image (Aadhaar/PAN)
            whisper_model: Whisper model size for transcription
            progress_callback: Optional callback(progress, stage) for progress updates

        Returns:
            Complete analysis results with decision
        """
        def update_progress(progress, stage):
            """Helper to call progress callback if provided"""
            if progress_callback:
                progress_callback(progress, stage)
        print("\n" + "="*70)
        print(f"  ANALYZING: {os.path.basename(video_path)}")
        print("="*70)

        start_time = datetime.now()

        # Create output directory for this analysis
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = os.path.join(self.output_base_dir, f"{video_name}_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)

        results = {
            'video_path': video_path,
            'reference_face': reference_face_path,
            'analysis_started': start_time.isoformat(),
            'output_directory': self.output_dir
        }

        try:
            # ============================================
            # STEP 1: PREPROCESSING
            # ============================================
            update_progress(35, 'Extracting frames and audio...')
            print("\n" + "-"*50)
            print("STEP 1: PREPROCESSING")
            print("-"*50)

            self.preprocessor = Preprocessor(video_path, self.output_dir)
            preprocessing_results = self.preprocessor.process(
                frame_rate=10,  # 10 FPS for reliable blink detection (blinks are 100-400ms)
                extract_audio=True,
                detect_faces=True
            )
            results['preprocessing'] = preprocessing_results

            # ============================================
            # STEP 2: TRANSCRIPTION
            # ============================================
            update_progress(40, 'Transcribing audio (this may take 30-40 seconds)...')
            print("\n" + "-"*50)
            print("STEP 2: TRANSCRIPTION (Speech-to-Text)")
            print("-"*50)

            audio_path = preprocessing_results.get('audio_path')
            if audio_path and os.path.exists(audio_path):
                if self.transcript_generator is None:
                    self.transcript_generator = TranscriptGenerator(model_size=whisper_model)

                transcript = self.transcript_generator.transcribe_with_timestamps(audio_path)

                # Identify speakers
                transcript['segments'] = self.transcript_generator.identify_speakers(
                    transcript['segments']
                )

                # Extract Q&A pairs
                transcript['qa_pairs'] = self.transcript_generator.extract_qa_pairs(
                    transcript['segments']
                )

                # Save transcript
                transcript_path = os.path.join(self.output_dir, 'transcript.json')
                self.transcript_generator.save_transcript(transcript, transcript_path)

                transcript_txt_path = os.path.join(self.output_dir, 'transcript.txt')
                self.transcript_generator.save_transcript_text(transcript, transcript_txt_path)

                results['transcript'] = transcript
            else:
                print("  Warning: Audio not available, skipping transcription")
                results['transcript'] = {'full_text': '', 'segments': []}

            # ============================================
            # STEP 3: LIVENESS DETECTION
            # ============================================
            update_progress(60, 'Analyzing liveness (blinks, movements)...')
            print("\n" + "-"*50)
            print("STEP 3: LIVENESS DETECTION")
            print("-"*50)

            frames_dir = preprocessing_results.get('output_directory', '') + '/frames'
            if os.path.exists(frames_dir):
                liveness_results = self.liveness_detector.analyze_liveness(frames_dir)

                # Check script compliance for liveness instructions
                if results.get('transcript'):
                    script_compliance = self.liveness_detector.check_script_compliance(
                        liveness_results,
                        results['transcript']
                    )
                    liveness_results['script_compliance'] = script_compliance

                # Save results
                liveness_path = os.path.join(self.output_dir, 'liveness_results.json')
                self.liveness_detector.save_results(liveness_results, liveness_path)

                results['liveness'] = liveness_results
            else:
                print("  Warning: Frames not available, skipping liveness")
                results['liveness'] = {'liveness_score': 0, 'is_live': False}

            # ============================================
            # STEP 4: FACE MATCHING
            # ============================================
            update_progress(70, 'Matching face with reference...')
            print("\n" + "-"*50)
            print("STEP 4: FACE MATCHING")
            print("-"*50)

            if reference_face_path and os.path.exists(reference_face_path):
                if self.face_matcher is None:
                    self.face_matcher = FaceMatcher()

                # Get face images from preprocessing
                faces_dir = preprocessing_results.get('output_directory', '') + '/faces'
                if os.path.exists(faces_dir):
                    face_files = [
                        os.path.join(faces_dir, f)
                        for f in os.listdir(faces_dir)
                        if f.endswith(('.jpg', '.jpeg', '.png'))
                    ]

                    if face_files:
                        face_results = self.face_matcher.get_face_score(
                            reference_face_path,
                            face_files
                        )

                        # Save results
                        face_path = os.path.join(self.output_dir, 'face_match_results.json')
                        self.face_matcher.save_results(face_results, face_path)

                        results['face_match'] = face_results
                    else:
                        print("  Warning: No faces extracted from video")
                        results['face_match'] = {'score': 0, 'passed': False}
                else:
                    print("  Warning: Faces directory not found")
                    results['face_match'] = {'score': 0, 'passed': False}
            else:
                print("  Warning: No reference face provided, skipping face matching")
                results['face_match'] = {'score': 50, 'passed': True, 'note': 'Not analyzed - no reference'}

            # ============================================
            # STEP 5: SCRIPT COMPLIANCE
            # ============================================
            update_progress(80, 'Checking script compliance...')
            print("\n" + "-"*50)
            print("STEP 5: SCRIPT COMPLIANCE CHECK")
            print("-"*50)

            transcript = results.get('transcript', {})
            if transcript.get('full_text'):
                script_results = self.script_checker.get_compliance_score(transcript)

                # Save results
                script_path = os.path.join(self.output_dir, 'script_compliance.json')
                self.script_checker.save_results(script_results, script_path)

                results['script_compliance'] = script_results
            else:
                print("  Warning: No transcript available, skipping script check")
                results['script_compliance'] = {'score': 0, 'passed': False}

            # ============================================
            # STEP 6: BEHAVIOR ANALYSIS
            # ============================================
            update_progress(85, 'Analyzing behavior patterns...')
            print("\n" + "-"*50)
            print("STEP 6: BEHAVIOR ANALYSIS")
            print("-"*50)

            if transcript.get('segments'):
                behavior_results = self.behavior_analyzer.get_behavior_score(transcript)

                # Save results
                behavior_path = os.path.join(self.output_dir, 'behavior_analysis.json')
                self.behavior_analyzer.save_results(behavior_results, behavior_path)

                results['behavior'] = behavior_results
            else:
                print("  Warning: No transcript segments, skipping behavior analysis")
                results['behavior'] = {'score': 100, 'risk_level': 'UNKNOWN'}

            # ============================================
            # STEP 7: DECISION ENGINE
            # ============================================
            update_progress(90, 'Computing final decision...')
            print("\n" + "-"*50)
            print("STEP 7: DECISION ENGINE")
            print("-"*50)

            decision = self.decision_engine.make_decision(results)

            # Save decision
            decision_path = os.path.join(self.output_dir, 'decision.json')
            self.decision_engine.save_decision(decision, decision_path)

            results['decision'] = decision

            # ============================================
            # STEP 8: GENERATE REPORT
            # ============================================
            update_progress(95, 'Generating reports...')
            print("\n" + "-"*50)
            print("STEP 8: GENERATING REPORT")
            print("-"*50)

            report = self.report_generator.generate_report(
                video_path,
                decision,
                results,
                preprocessing_results
            )

            # Save reports
            json_report_path = os.path.join(self.output_dir, 'final_report.json')
            self.report_generator.save_json_report(report, json_report_path)

            html_report_path = os.path.join(self.output_dir, 'final_report.html')
            self.report_generator.save_html_report(report, html_report_path)

            results['report'] = report
            results['report_paths'] = {
                'json': json_report_path,
                'html': html_report_path
            }

        except Exception as e:
            print(f"\n[FAIL] Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            results['error'] = str(e)
            results['decision'] = {'decision': 'ERROR', 'final_score': 0}

        finally:
            # Cleanup
            if self.preprocessor:
                self.preprocessor.close()

        # Calculate total time
        end_time = datetime.now()
        results['analysis_completed'] = end_time.isoformat()
        results['total_time_seconds'] = (end_time - start_time).total_seconds()

        # Print final summary
        self._print_final_summary(results)

        return results

    def _print_final_summary(self, results):
        """Print final analysis summary"""
        print("\n" + "="*70)
        print("  ANALYSIS COMPLETE")
        print("="*70)

        decision = results.get('decision', {})
        verdict = decision.get('decision', 'UNKNOWN')

        if verdict == 'PASS':
            print("\n  [PASS] RESULT: APPROVED")
        elif verdict == 'FLAG':
            print("\n  WARNING:  RESULT: FLAGGED FOR REVIEW")
        elif verdict == 'REJECT':
            print("\n  [FAIL] RESULT: REJECTED")
        else:
            print(f"\n  [UNKNOWN] RESULT: {verdict}")

        print(f"\n  Final Score: {decision.get('final_score', 0)}/100")
        print(f"  Reason: {decision.get('decision_reason', 'N/A')}")
        print(f"\n  Total Analysis Time: {results.get('total_time_seconds', 0):.2f} seconds")
        print(f"  Output Directory: {results.get('output_directory', 'N/A')}")

        report_paths = results.get('report_paths', {})
        if report_paths.get('html'):
            print(f"\n  [REPORT] Open HTML Report: {report_paths['html']}")

        print("\n" + "="*70 + "\n")


def analyze_video(video_path, reference_face_path=None, output_dir='outputs/analysis', whisper_model='base'):
    """
    Convenience function to analyze a video

    Args:
        video_path: Path to video file
        reference_face_path: Optional path to reference face (Aadhaar/PAN)
        output_dir: Base output directory
        whisper_model: Whisper model size

    Returns:
        Analysis results dictionary
    """
    analyzer = VideoAnalyzer(output_base_dir=output_dir)
    return analyzer.analyze(video_path, reference_face_path, whisper_model)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Video KYC Analyzer')
    parser.add_argument('video', help='Path to video file')
    parser.add_argument('--reference', '-r', help='Path to reference face image (Aadhaar/PAN)')
    parser.add_argument('--output', '-o', default='outputs/analysis', help='Output directory')
    parser.add_argument('--whisper', '-w', default='base', choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Whisper model size')

    args = parser.parse_args()

    if os.path.exists(args.video):
        results = analyze_video(
            args.video,
            reference_face_path=args.reference,
            output_dir=args.output,
            whisper_model=args.whisper
        )

        print(f"\nFinal Decision: {results['decision']['decision']}")
        print(f"Score: {results['decision']['final_score']}/100")
    else:
        print(f"Video not found: {args.video}")
