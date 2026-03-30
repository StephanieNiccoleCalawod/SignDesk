"""
tracker.py - Hand Landmark Tracker
Detects and tracks hand landmarks using MediaPipe Hands.
Maps to: SD002 (Hand detection system)
"""

import mediapipe as mp
import cv2


class HandTracker:
    """
    Detects 21 hand landmarks per frame using MediaPipe Hands.

    Acceptance Criteria:
    - SD002-AC1: MediaPipe Hands detects 21 hand landmarks per frame
    - SD002-AC2: Landmarks are visually overlaid on the webcam feed
    - SD002-AC3: Detection occurs within 1 second of gesture being made
    - SD002-AC4: Tracking remains stable during normal hand movement
    - SD002-AC5: Works under standard indoor lighting conditions
    """

    def __init__(self, max_num_hands: int = 1, min_detection_confidence: float = 0.7,
                 min_tracking_confidence: float = 0.5):
        self._mp_hands = mp.solutions.hands
        self._mp_drawing = mp.solutions.drawing_utils
        self._mp_drawing_styles = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self._last_landmarks = None
        self._hand_detected = False

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
        rgb_frame.flags.writeable = False

        results = self._hands.process(rgb_frame)

        rgb_frame.flags.writeable = True
        annotated_frame = frame.copy()

        if results.multi_hand_landmarks:
            self._hand_detected = True

            # Take the first detected hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # Draw landmarks on the frame (SD002-AC2)
            self._mp_drawing.draw_landmarks(
                annotated_frame,
                hand_landmarks,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_drawing_styles.get_default_hand_landmarks_style(),
                self._mp_drawing_styles.get_default_hand_connections_style(),
            )

            # Extract 21 landmark coordinates
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append((lm.x, lm.y, lm.z))

            self._last_landmarks = landmarks
            return True, landmarks, annotated_frame
        else:
            self._hand_detected = False
            self._last_landmarks = None
            return False, None, annotated_frame

    @property
    def is_hand_detected(self) -> bool:
        return self._hand_detected

    @property
    def last_landmarks(self):
        return self._last_landmarks

    def release(self):
        """Releases MediaPipe resources."""
        self._hands.close()

    def __del__(self):
        self.release()
