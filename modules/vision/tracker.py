"""
tracker.py - Hand Landmark Tracker
Detects and tracks hand landmarks using Modern MediaPipe Tasks API.
Runs detection in a background thread so the camera feed never blocks.
Maps to: SD002 (Hand detection system)
"""

import threading
import logging
import cv2
import os
import urllib.request

logger = logging.getLogger(__name__)

# Download URL for the task model
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

# ── Developer flag ────────────────────────────────────────────────────────────
# Set to True ONLY during development when the bundled model file is unavailable.
# Must remain False in all production builds and final demo deployments.
# The application must never download model files during normal operation.
DEV_ALLOW_MODEL_DOWNLOAD = False

# Standard MediaPipe Hand Connections for custom drawing
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]


class HandTracker:
    """
    Detects 21 hand landmarks per frame using Modern MediaPipe Tasks API.
    Detection runs in a background daemon thread — camera feed is never blocked.

    Acceptance Criteria:
    - SD002-AC1: MediaPipe Hands detects 21 hand landmarks per frame
    - SD002-AC2: Landmarks are visually overlaid on the webcam feed
    - SD002-AC3: Detection occurs within 1 second of gesture being made
    - SD002-AC4: Tracking remains stable during normal hand movement
    - SD002-AC5: Works under standard indoor lighting conditions
    """

    def __init__(self, max_num_hands: int = 1,
                 min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.5):

        self._initialised = False   # True only when MediaPipe loaded correctly
        self._init_error: str | None = None

        # ── Background thread state ───────────────────────────────────────
        self._lock             = threading.Lock()
        self._detection_thread = None
        self._running          = True

        # Latest results — updated by background thread, read by main thread
        self._latest_landmarks: list | None = None
        self._hand_detected: bool = False

        # Latest frame to process — set by main thread, read by background
        self._pending_frame = None
        self._frame_event   = threading.Event()

        # Attempt model download and MediaPipe initialisation.
        # Any failure sets _init_error and leaves _initialised=False so the
        # rest of the application continues without crashing.
        try:
            self._ensure_model_exists()
        except Exception as exc:
            self._init_error = f"Model download failed: {exc}"
            logger.error("HandTracker.__init__: %s", self._init_error)
            return

        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=max_num_hands,
                min_hand_detection_confidence=min_detection_confidence,
                min_hand_presence_confidence=min_tracking_confidence,
                min_tracking_confidence=min_tracking_confidence,
            )
            self._detector = vision.HandLandmarker.create_from_options(options)
            self._mp = mp                 # keep reference for frame conversion
        except ImportError as exc:
            self._init_error = f"MediaPipe not installed: {exc}"
            logger.error("HandTracker.__init__: %s", self._init_error)
            return
        except Exception as exc:
            self._init_error = f"MediaPipe initialisation failed: {exc}"
            logger.exception("HandTracker.__init__: %s", self._init_error)
            return

        self._initialised = True

        # Start background detection thread only when MediaPipe is ready
        self._detection_thread = threading.Thread(
            target=self._detection_loop,
            name="HandDetection",
            daemon=True,
        )
        self._detection_thread.start()
        logger.info("HandTracker: initialised successfully.")

    # ── Model download ────────────────────────────────────────────────────

    def _ensure_model_exists(self):
        """
        Checks that the bundled hand-landmark model file is present.

        In production (DEV_ALLOW_MODEL_DOWNLOAD = False) the model must be
        shipped with the application package.  If the file is missing a clear
        RuntimeError is raised so the caller can surface a useful message to
        the user without crashing.

        Set DEV_ALLOW_MODEL_DOWNLOAD = True only during development when you
        need to fetch the model for the first time.  Never enable this flag
        in production or demo builds.
        """
        if os.path.exists(MODEL_PATH):
            return  # Model present — nothing to do

        if DEV_ALLOW_MODEL_DOWNLOAD:
            logger.warning(
                "HandTracker: DEV_ALLOW_MODEL_DOWNLOAD is enabled. "
                "Downloading model to %s — disable this flag for production.", MODEL_PATH
            )
            try:
                urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
                logger.info("HandTracker: model download complete.")
            except Exception as exc:
                if os.path.exists(MODEL_PATH):
                    try:
                        os.remove(MODEL_PATH)
                    except OSError:
                        pass
                raise RuntimeError(f"Could not download hand-landmark model: {exc}") from exc
        else:
            raise RuntimeError(
                f"Bundled model file not found: {MODEL_PATH}\n"
                "Please ensure 'hand_landmarker.task' is included in the application package "
                "alongside modules/vision/. "
                "Do not enable DEV_ALLOW_MODEL_DOWNLOAD in production builds."
            )

    # ── Background detection loop ─────────────────────────────────────────

    def _detection_loop(self):
        """
        Runs in a background daemon thread.
        Waits for a new frame, runs MediaPipe detection, stores results.
        Never propagates exceptions to the Qt main thread.
        """
        while self._running:
            signaled = self._frame_event.wait(timeout=1.0)
            if not signaled:
                continue

            with self._lock:
                frame = self._pending_frame
                self._frame_event.clear()

            if frame is None:
                continue

            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image  = self._mp.Image(
                    image_format=self._mp.ImageFormat.SRGB,
                    data=rgb_frame,
                )
                results = self._detector.detect(mp_image)

                if results.hand_landmarks:
                    hand_landmarks = results.hand_landmarks[0]
                    landmarks = [(lm.x, lm.y, lm.z) for lm in hand_landmarks]
                    with self._lock:
                        self._latest_landmarks = landmarks
                        self._hand_detected    = True
                else:
                    with self._lock:
                        self._latest_landmarks = None
                        self._hand_detected    = False

            except cv2.error as exc:
                logger.error("[HandTracker] OpenCV error in detection loop: %s", exc)
                with self._lock:
                    self._latest_landmarks = None
                    self._hand_detected    = False

            except Exception as exc:
                logger.exception("[HandTracker] Unexpected error in detection loop: %s", exc)
                with self._lock:
                    self._latest_landmarks = None
                    self._hand_detected    = False

    # ── Public API ────────────────────────────────────────────────────────

    def process_frame(self, frame):
        """
        Submits a frame for background detection and returns the
        latest available results immediately — never blocks.

        If the tracker failed to initialise, returns (False, None, frame)
        so the caller can still display the raw camera feed.

        Returns:
            (hand_detected: bool, landmarks: list | None, annotated_frame: ndarray)
        """
        if not self._initialised:
            # Return raw frame; caller can show an error overlay if desired
            return False, None, frame

        try:
            with self._lock:
                self._pending_frame = frame
            self._frame_event.set()

            with self._lock:
                hand_detected = self._hand_detected
                landmarks     = self._latest_landmarks

            annotated_frame = frame.copy()

            if hand_detected and landmarks:
                from core.config import config
                try:
                    if config.get("appearance.show_landmark_overlay", True):
                        self._draw_custom_landmarks(annotated_frame, landmarks)
                except Exception as exc:
                    logger.warning("[HandTracker] Landmark overlay error: %s", exc)

            return hand_detected, landmarks, annotated_frame

        except Exception as exc:
            logger.exception("[HandTracker] process_frame error: %s", exc)
            return False, None, frame

    def _draw_custom_landmarks(self, frame, landmarks):
        """Manually draws 21 landmarks and connections using OpenCV."""
        try:
            h, w, _ = frame.shape
            pixels = [(int(x * w), int(y * h)) for x, y, _ in landmarks]

            for start_idx, end_idx in HAND_CONNECTIONS:
                if start_idx < len(pixels) and end_idx < len(pixels):
                    cv2.line(frame, pixels[start_idx], pixels[end_idx], (0, 0, 0), 2)
                    cv2.line(frame, pixels[start_idx], pixels[end_idx], (255, 255, 255), 1)

            for cx, cy in pixels:
                cv2.circle(frame, (cx, cy), 5, (0, 0, 0), -1)
                cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1)
        except Exception as exc:
            logger.warning("[HandTracker] _draw_custom_landmarks error: %s", exc)

    @property
    def is_hand_detected(self) -> bool:
        with self._lock:
            return self._hand_detected

    @property
    def last_landmarks(self):
        with self._lock:
            return self._latest_landmarks

    @property
    def init_error(self) -> str | None:
        """Non-None when initialisation failed; contains a human-readable reason."""
        return self._init_error

    def release(self):
        """Stops the background thread and releases MediaPipe resources. Safe to call multiple times."""
        self._running = False
        self._frame_event.set()   # Unblock the waiting thread

        if self._detection_thread is not None:
            try:
                self._detection_thread.join(timeout=2.0)
            except Exception as exc:
                logger.warning("[HandTracker] Thread join error: %s", exc)
            self._detection_thread = None

        if self._initialised:
            try:
                self._detector.close()
            except Exception as exc:
                logger.warning("[HandTracker] Detector close error: %s", exc)
            self._initialised = False

        logger.info("HandTracker: released.")

    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
