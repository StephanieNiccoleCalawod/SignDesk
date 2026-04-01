"""
tracker.py - Hand Landmark Tracker
Detects and tracks hand landmarks using Modern MediaPipe Tasks API.
Maps to: SD002 (Hand detection system)
"""

import mediapipe as mp
import cv2
import os
import urllib.request
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Download URL for the task model
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

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

    Acceptance Criteria:
    - SD002-AC1: MediaPipe Hands detects 21 hand landmarks per frame
    - SD002-AC2: Landmarks are visually overlaid on the webcam feed
    - SD002-AC3: Detection occurs within 1 second of gesture being made
    - SD002-AC4: Tracking remains stable during normal hand movement
    - SD002-AC5: Works under standard indoor lighting conditions
    """

    def __init__(self, max_num_hands: int = 1, min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.5):
        
        self._ensure_model_exists()
        
        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_tracking_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self._detector = vision.HandLandmarker.create_from_options(options)

        self._last_landmarks = None
        self._hand_detected = False

    def _ensure_model_exists(self):
        """Downloads the MediaPipe task file if not present."""
        if not os.path.exists(MODEL_PATH):
            print(f"Downloading MediaPipe model to {MODEL_PATH}...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Download complete.")

    def process_frame(self, frame):
        """
        Processes a BGR frame and extracts hand landmarks.

        Returns:
            (hand_detected: bool, landmarks: list | None, annotated_frame: ndarray)

        landmarks is a list of 21 (x, y, z) tuples normalized to [0, 1]
        if a hand is detected, otherwise None.
        """
        # MediaPipe requires RGB input
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Modern Tasks Image wrapper
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Detect hands (synchronous call for single frame)
        results = self._detector.detect(mp_image)

        annotated_frame = frame.copy()

        if results.hand_landmarks:
            self._hand_detected = True

            # Take the first detected hand
            hand_landmarks = results.hand_landmarks[0]

            # Extract 21 landmark coordinates
            landmarks = []
            for lm in hand_landmarks:
                landmarks.append((lm.x, lm.y, lm.z))

            self._last_landmarks = landmarks
            
            # Custom Landmark Overlay (SD002-AC2) to avoid crashed solutions library
            self._draw_custom_landmarks(annotated_frame, landmarks)
            
            return True, landmarks, annotated_frame
        else:
            self._hand_detected = False
            self._last_landmarks = None
            return False, None, annotated_frame

    def _draw_custom_landmarks(self, frame, landmarks):
        """Manually draws 21 landmarks and connections using OpenCV."""
        h, w, _ = frame.shape
        
        # Convert normalized (x,y) to pixel coordinates
        pixels = []
        for x, y, _ in landmarks:
            cx, cy = int(x * w), int(y * h)
            pixels.append((cx, cy))
            
        # Draw skeleton connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(pixels) and end_idx < len(pixels):
                pt1 = pixels[start_idx]
                pt2 = pixels[end_idx]
                cv2.line(frame, pt1, pt2, (0, 0, 0), 2)       # Shadow outline
                cv2.line(frame, pt1, pt2, (255, 255, 255), 1) # White inner line
                
        # Draw joints
        for cx, cy in pixels:
            cv2.circle(frame, (cx, cy), 5, (0, 0, 0), -1)   # Shadow outline
            cv2.circle(frame, (cx, cy), 3, (0, 255, 0), -1) # Green center

    @property
    def is_hand_detected(self) -> bool:
        return self._hand_detected

    @property
    def last_landmarks(self):
        return self._last_landmarks

    def release(self):
        """Releases MediaPipe resources."""
        self._detector.close()

    def __del__(self):
        try:
            self.release()
        except:
            pass
