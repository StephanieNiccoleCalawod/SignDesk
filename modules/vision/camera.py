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

    # Resolution presets: config value → (width, height)
    _RESOLUTION_MAP = {
        "480p":  (640, 480),
        "720p":  (1280, 720),
        "1080p": (1920, 1080),
    }

    # Camera source presets: config value → OpenCV device index
    _SOURCE_MAP = {
        "builtin":  0,
        "external": 1,
    }

    def __init__(self, camera_index: int = 0, target_width: int = 640, target_height: int = 480):
        # Read settings from config; fall back to constructor defaults
        from core.config import config
        source = config.get("webcam.camera_source", "builtin")
        self._camera_index = self._SOURCE_MAP.get(source, camera_index)

        resolution = config.get("webcam.resolution", "480p")
        w, h = self._RESOLUTION_MAP.get(resolution, (target_width, target_height))
        self._target_width = w
        self._target_height = h

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
        from core.config import config
        if not config.webcam_enabled:
            return False, "Webcam access is disabled. Please enable camera to continue gesture detection."

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
