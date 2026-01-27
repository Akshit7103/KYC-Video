"""
Audio Processor Module
Extracts and processes audio from video files
"""

import os
import subprocess
import wave
import numpy as np


class AudioProcessor:
    """Handles audio extraction and processing from video"""

    def __init__(self, video_path):
        self.video_path = video_path
        self.audio_path = None

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

    def extract_audio(self, output_path=None, format='wav', sample_rate=16000):
        """
        Extract audio from video using ffmpeg

        Args:
            output_path: Path for output audio file (auto-generated if None)
            format: Audio format (wav recommended for processing)
            sample_rate: Audio sample rate (16000 Hz recommended for speech)

        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(self.video_path))[0]
            output_dir = os.path.dirname(self.video_path)
            output_path = os.path.join(output_dir, f"{base_name}_audio.{format}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', self.video_path,
            '-vn',  # No video
            '-acodec', 'pcm_s16le' if format == 'wav' else 'libmp3lame',
            '-ar', str(sample_rate),  # Sample rate
            '-ac', '1',  # Mono channel (better for speech recognition)
            '-y',  # Overwrite output
            output_path
        ]

        print(f"Extracting audio from video...")
        print(f"  Output: {output_path}")
        print(f"  Sample rate: {sample_rate} Hz")

        try:
            # Run ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            self.audio_path = output_path
            print(f"Audio extracted successfully: {output_path}")

            # Get audio info
            info = self.get_audio_info(output_path)
            if info:
                print(f"  Duration: {info['duration']:.2f} seconds")
                print(f"  Channels: {info['channels']}")

            return output_path

        except subprocess.CalledProcessError as e:
            print(f"Error extracting audio: {e.stderr}")
            raise RuntimeError(f"Failed to extract audio: {e.stderr}")
        except FileNotFoundError:
            print("ffmpeg not found. Please install ffmpeg.")
            raise RuntimeError("ffmpeg is required but not installed")

    def get_audio_info(self, audio_path=None):
        """
        Get audio file information

        Args:
            audio_path: Path to audio file (uses extracted audio if None)

        Returns:
            Dictionary with audio metadata
        """
        path = audio_path or self.audio_path

        if not path or not os.path.exists(path):
            return None

        try:
            with wave.open(path, 'rb') as wav:
                return {
                    'channels': wav.getnchannels(),
                    'sample_width': wav.getsampwidth(),
                    'frame_rate': wav.getframerate(),
                    'n_frames': wav.getnframes(),
                    'duration': wav.getnframes() / wav.getframerate()
                }
        except Exception as e:
            print(f"Could not read audio info: {e}")
            return None

    def detect_speech_segments(self, audio_path=None, threshold=0.02, min_duration=0.5):
        """
        Detect segments of audio that contain speech (based on energy)

        Args:
            audio_path: Path to audio file
            threshold: Energy threshold for speech detection
            min_duration: Minimum duration of speech segment in seconds

        Returns:
            List of (start_time, end_time) tuples for speech segments
        """
        path = audio_path or self.audio_path

        if not path or not os.path.exists(path):
            raise ValueError("No audio file available")

        try:
            with wave.open(path, 'rb') as wav:
                sample_rate = wav.getframerate()
                n_frames = wav.getnframes()
                audio_data = wav.readframes(n_frames)

                # Convert to numpy array
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
                audio_array = audio_array / 32768.0  # Normalize to -1 to 1

                # Calculate energy in windows
                window_size = int(sample_rate * 0.1)  # 100ms windows
                hop_size = int(sample_rate * 0.05)   # 50ms hop

                segments = []
                in_speech = False
                speech_start = 0

                for i in range(0, len(audio_array) - window_size, hop_size):
                    window = audio_array[i:i + window_size]
                    energy = np.sqrt(np.mean(window ** 2))

                    current_time = i / sample_rate

                    if energy > threshold and not in_speech:
                        in_speech = True
                        speech_start = current_time
                    elif energy <= threshold and in_speech:
                        in_speech = False
                        duration = current_time - speech_start
                        if duration >= min_duration:
                            segments.append((speech_start, current_time))

                # Handle case where speech continues to end
                if in_speech:
                    end_time = len(audio_array) / sample_rate
                    if end_time - speech_start >= min_duration:
                        segments.append((speech_start, end_time))

                print(f"Detected {len(segments)} speech segments")
                return segments

        except Exception as e:
            print(f"Error detecting speech segments: {e}")
            return []

    def split_audio(self, segments, output_dir):
        """
        Split audio into segments

        Args:
            segments: List of (start_time, end_time) tuples
            output_dir: Directory to save audio segments

        Returns:
            List of segment file paths
        """
        os.makedirs(output_dir, exist_ok=True)

        segment_paths = []

        for i, (start, end) in enumerate(segments):
            output_path = os.path.join(output_dir, f"segment_{i:03d}_{start:.2f}_{end:.2f}.wav")

            cmd = [
                'ffmpeg',
                '-i', self.audio_path,
                '-ss', str(start),
                '-t', str(end - start),
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-y',
                output_path
            ]

            try:
                subprocess.run(cmd, capture_output=True, check=True)
                segment_paths.append({
                    'path': output_path,
                    'start': start,
                    'end': end,
                    'duration': end - start
                })
            except subprocess.CalledProcessError as e:
                print(f"Error splitting segment {i}: {e}")

        print(f"Created {len(segment_paths)} audio segments")
        return segment_paths
