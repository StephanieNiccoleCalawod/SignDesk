"""
camera.py - Webcam Capture Manager
Handles OpenCV webcam access, frame reading, and lifecycle.
Maps to: SD001 (Real-time gesture detection)
"""

import cv2
import time
import logging

logger = logging.getLogger(__name__)


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
        from core.config import config
        source = config.get("webcam.camera_source", "builtin")
        self._camera_index = self._SOURCE_MAP.get(source, camera_index)

        resolution = config.get("webcam.resolution", "480p")
        w, h = self._RESOLUTION_MAP.get(resolution, (target_width, target_height))
        self._target_width = w
        self._target_height = h

        self._cap = None
        self._is_running = False
        self._last_frame_time = 0.0
        self._fps = 0.0
        # Consecutive read-failure counter — used to detect silent disconnection
        self._consecutive_failures = 0
        self._MAX_FAILURES = 10

    def start(self) -> tuple[bool, str]:
        """
        Opens the webcam and configures it.

        Returns (True, success_msg) on success, (False, error_msg) on failure.
        Handles: webcam disabled, device missing, permission denied, and any
        unexpected exception — none of these will crash the caller.
        """
        from core.config import config

        # Guard: setting disabled
        if not config.webcam_enabled:
            logger.warning("CameraManager.start(): webcam access is disabled by settings.")
            return False, "Webcam access is disabled. Please enable camera to continue gesture detection."

        # Guard: already running — stop first to avoid resource leak
        if self._is_running:
            logger.warning("CameraManager.start(): called while already running; stopping first.")
            self.stop()

        try:
            # Prefer DirectShow on Windows for reliable FOURCC support;
            # falls back to the platform default on non-Windows.
            try:
                self._cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            except Exception:
                # CAP_DSHOW may not be available on all platforms
                self._cap = cv2.VideoCapture(self._camera_index)

            if self._cap is None or not self._cap.isOpened():
                self._cap = None
                logger.error("CameraManager.start(): VideoCapture could not open device %d.", self._camera_index)
                return False, "Webcam device not detected. Please connect a webcam and try again."

            # Set FOURCC to MJPG before resolution — required for CAP_DSHOW
            # to prevent raw YUV noise and ensure correct color output.
            # Ignore return value: not all backends support FOURCC changes.
            self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

            # Configure resolution and FPS
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._target_width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._target_height)
            self._cap.set(cv2.CAP_PROP_FPS, 30)

            self._is_running = True
            self._consecutive_failures = 0
            self._last_frame_time = time.time()
            logger.info("CameraManager: started on device %d (%dx%d).", self._camera_index, self._target_width, self._target_height)
            return True, "Webcam started successfully."

        except PermissionError as exc:
            logger.error("CameraManager.start(): permission denied — %s", exc)
            self._cap = None
            return False, "Webcam permission denied. Please enable camera access in your system settings."

        except cv2.error as exc:
            logger.error("CameraManager.start(): OpenCV error — %s", exc)
            self._cap = None
            return False, "Webcam initialisation failed (OpenCV error). Please reconnect the webcam."

        except Exception as exc:
            logger.exception("CameraManager.start(): unexpected error — %s", exc)
            self._cap = None
            return False, "Webcam device not detected. Please connect a webcam and try again."

    def read_frame(self):
        """
        Read one frame from the webcam.

        Returns (True, frame, fps) on success.
        Returns (False, None, 0) on failure — never raises.

        After _MAX_FAILURES consecutive failures the camera is stopped
        automatically to free the OS resource.
        """
        if not self._is_running or self._cap is None:
            return False, None, 0

        try:
            ret, frame = self._cap.read()
        except cv2.error as exc:
            logger.error("CameraManager.read_frame(): OpenCV read error — %s", exc)
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._MAX_FAILURES:
                logger.error("CameraManager: too many consecutive failures; stopping camera.")
                self.stop()
            return False, None, 0
        except Exception as exc:
            logger.exception("CameraManager.read_frame(): unexpected error — %s", exc)
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._MAX_FAILURES:
                self.stop()
            return False, None, 0

        if not ret or frame is None:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self._MAX_FAILURES:
                logger.error("CameraManager: camera disconnected (no frame); stopping.")
                self.stop()
            return False, None, 0

        self._consecutive_failures = 0

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
        """
        Stops the webcam feed and releases the underlying VideoCapture.

        Safe to call multiple times.  The actual cv2.VideoCapture.release()
        is dispatched to a daemon thread to prevent DirectShow from blocking
        the Qt main thread on Windows.
        """
        self._is_running = False
        if self._cap is not None:
            cap_to_release = self._cap
            self._cap = None
            import threading
            threading.Thread(target=self._safe_release, args=(cap_to_release,), daemon=True).start()
            logger.info("CameraManager: stopped.")

    @staticmethod
    def _safe_release(cap):
        """Releases a VideoCapture object without letting exceptions propagate."""
        try:
            cap.release()
        except Exception as exc:
            logger.warning("CameraManager._safe_release(): error during release — %s", exc)

    def is_opened(self) -> bool:
        return self._is_running and self._cap is not None and self._cap.isOpened()

    @property
    def fps(self) -> float:
        return self._fps

    def __del__(self):
        try:
            self.stop()
        except Exception:
            pass
