"""
Video Processor Module
Extracts frames and handles video-related operations
"""

import cv2
import os
import numpy as np
from datetime import timedelta


class VideoProcessor:
    """Handles video frame extraction and processing"""

    def __init__(self, video_path):
        self.video_path = video_path
        self.cap = None
        self.fps = 0
        self.total_frames = 0
        self.duration = 0
        self.width = 0
        self.height = 0

        self._load_video()

    def _load_video(self):
        """Load video and extract metadata"""
        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video not found: {self.video_path}")

        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {self.video_path}")

        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"Video loaded: {self.video_path}")
        print(f"  Resolution: {self.width}x{self.height}")
        print(f"  FPS: {self.fps:.2f}")
        print(f"  Duration: {self.duration:.2f} seconds")
        print(f"  Total frames: {self.total_frames}")

    def get_metadata(self):
        """Return video metadata"""
        return {
            'path': self.video_path,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'duration': self.duration,
            'duration_formatted': str(timedelta(seconds=int(self.duration))),
            'width': self.width,
            'height': self.height,
            'resolution': f"{self.width}x{self.height}"
        }

    def extract_frames(self, output_dir, frame_rate=1):
        """
        Extract frames from video at specified rate

        Args:
            output_dir: Directory to save frames
            frame_rate: Frames per second to extract (default: 1 FPS)

        Returns:
            List of extracted frame paths with timestamps
        """
        os.makedirs(output_dir, exist_ok=True)

        frame_interval = int(self.fps / frame_rate) if frame_rate <= self.fps else 1

        frames = []
        frame_count = 0
        saved_count = 0

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset to start

        print(f"Extracting frames at {frame_rate} FPS (every {frame_interval} frames)...")

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                timestamp = frame_count / self.fps
                frame_filename = f"frame_{saved_count:05d}_{timestamp:.2f}s.jpg"
                frame_path = os.path.join(output_dir, frame_filename)

                cv2.imwrite(frame_path, frame)

                frames.append({
                    'path': frame_path,
                    'frame_number': frame_count,
                    'timestamp': timestamp,
                    'timestamp_formatted': str(timedelta(seconds=int(timestamp)))
                })

                saved_count += 1

            frame_count += 1

        print(f"Extracted {saved_count} frames to {output_dir}")
        return frames

    def extract_frame_at_timestamp(self, timestamp):
        """
        Extract a single frame at specific timestamp

        Args:
            timestamp: Time in seconds

        Returns:
            Frame as numpy array
        """
        frame_number = int(timestamp * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()

        if ret:
            return frame
        return None

    def extract_frames_in_range(self, start_time, end_time, output_dir, frame_rate=1):
        """
        Extract frames within a time range

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            output_dir: Directory to save frames
            frame_rate: Frames per second to extract

        Returns:
            List of extracted frame info
        """
        os.makedirs(output_dir, exist_ok=True)

        start_frame = int(start_time * self.fps)
        end_frame = int(end_time * self.fps)
        frame_interval = int(self.fps / frame_rate) if frame_rate <= self.fps else 1

        frames = []
        saved_count = 0

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        for frame_num in range(start_frame, min(end_frame, self.total_frames)):
            ret, frame = self.cap.read()
            if not ret:
                break

            if (frame_num - start_frame) % frame_interval == 0:
                timestamp = frame_num / self.fps
                frame_filename = f"frame_{saved_count:05d}_{timestamp:.2f}s.jpg"
                frame_path = os.path.join(output_dir, frame_filename)

                cv2.imwrite(frame_path, frame)

                frames.append({
                    'path': frame_path,
                    'frame_number': frame_num,
                    'timestamp': timestamp
                })

                saved_count += 1

        return frames

    def detect_scene_changes(self, threshold=30):
        """
        Detect significant scene changes (useful for detecting document display)

        Args:
            threshold: Difference threshold for scene change detection

        Returns:
            List of timestamps where scene changes occur
        """
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        scene_changes = []
        prev_frame = None
        frame_count = 0

        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_frame is not None:
                diff = cv2.absdiff(prev_frame, gray)
                mean_diff = np.mean(diff)

                if mean_diff > threshold:
                    timestamp = frame_count / self.fps
                    scene_changes.append({
                        'timestamp': timestamp,
                        'frame_number': frame_count,
                        'difference': mean_diff
                    })

            prev_frame = gray
            frame_count += 1

        print(f"Detected {len(scene_changes)} scene changes")
        return scene_changes

    def close(self):
        """Release video capture resources"""
        if self.cap:
            self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
