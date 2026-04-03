"""
camera.py - Webcam Capture Manager
Handles OpenCV webcam access, frame reading, and lifecycle.
Maps to: SD001 (Real-time gesture detection)
"""

import cv2
import time


class CameraManager:
    """
    Manages the webcam feed using OpenCV VideoCapture.

    Acceptance Criteria:
    - SD001-AC1: System requests webcam permission on launch
    - SD001-AC2: Live webcam feed is displayed in the main interface
    - SD001-AC3: Application shows an error message if webcam is unavailable
    - SD001-AC4: Feed refreshes in real time at ≥24 FPS
    """

    def __init__(self, camera_index: int = 0, target_width: int = 640, target_height: int = 480):
        self._camera_index = camera_index
        self._target_width = target_width
        self._target_height = target_height
        self._cap = None
        self._is_running = False
        self._last_frame_time = 0
        self._fps = 0

    def start(self) -> tuple[bool, str]:
        """
        Opens the webcam. Returns (success, message).
        Error prompts per business requirements:
        - "Webcam device not detected. Please connect a webcam."
        - "Webcam permission denied. Please enable camera access."
        """
        try:
            self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)

            if self._cap is None or not self._cap.isOpened():
                return False, "Webcam device not detected. Please connect a webcam."

            # Configure for ≥24 FPS (SD001-AC4)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._target_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._target_height)
            self._cap.set(cv2.CAP_PROP_FPS, 30)

            self._is_running = True
            self._last_frame_time = time.time()
            return True, "Webcam started successfully."

        except PermissionError:
            return False, "Webcam permission denied. Please enable camera access."
        except Exception as e:
            return False, f"Webcam device not detected. Please connect a webcam."

    def read_frame(self):
        """
        Reads a single frame from the webcam.
        Returns (success, frame, fps).
        """
        if not self._is_running or self._cap is None:
            return False, None, 0

        ret, frame = self._cap.read()

        if not ret or frame is None:
            return False, None, 0

        # Flip horizontally for mirror-view (more natural for user)
        frame = cv2.flip(frame, 1)

        # Calculate FPS
        current_time = time.time()
        elapsed = current_time - self._last_frame_time
        if elapsed > 0:
            self._fps = 1.0 / elapsed
        self._last_frame_time = current_time

        return True, frame, self._fps

    def stop(self):
        """Releases the webcam."""
        self._is_running = False
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def is_opened(self) -> bool:
        """Returns True if the webcam is active."""
        return self._is_running and self._cap is not None and self._cap.isOpened()

    @property
    def fps(self) -> float:
        return self._fps

    def __del__(self):
        self.stop()
