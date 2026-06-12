

import os
import json
import numpy as np
from tensorflow.keras.models import load_model


class CNNPredictor:
    """
    Loads a trained model and predicts ASL gestures from hand landmarks.

    Supports two modes:
      1. Landmark model (preferred): feeds 63 coords directly
      2. CNN fallback: converts to skeleton image if landmark model missing

    Drop-in replacement for LandmarkComparator — same interface:
        best_match(landmarks) → (gesture_name, confidence)
    """

    # Landmark-based model (preferred)
    LANDMARK_MODEL_PATH  = "training/models/asl_landmark.h5"
    LANDMARK_LABELS_PATH = "training/models/landmark_label_map.json"

    # CNN fallback
    CNN_MODEL_PATH  = "training/models/asl_cnn.h5"
    CNN_LABELS_PATH = "training/models/label_map.json"

    IMG_SIZE = 64  # only used by CNN fallback

    def __init__(self):
        self._use_landmarks = False

        # Try landmark model first (much more accurate)
        if os.path.exists(self.LANDMARK_MODEL_PATH):
            print("[CNNPredictor] Loading landmark model...")
            self._model = load_model(self.LANDMARK_MODEL_PATH)
            labels_path = self.LANDMARK_LABELS_PATH
            self._use_landmarks = True
            print("[CNNPredictor] Using LANDMARK mode (direct coordinates)")

        elif os.path.exists(self.CNN_MODEL_PATH):
            print("[CNNPredictor] Landmark model not found, falling back to CNN...")
            self._model = load_model(self.CNN_MODEL_PATH)
            labels_path = self.CNN_LABELS_PATH
            print("[CNNPredictor] Using CNN mode (skeleton image)")

        else:
            raise FileNotFoundError(
                "No trained model found. Run:\n"
                "  1. python training/collect_landmarks.py\n"
                "  2. python training/train_landmark_model.py"
            )

        with open(labels_path, "r") as f:
            label_map = json.load(f)

        # Reverse: {0: 'A', 1: 'B', ...}
        self._labels = {v: k for k, v in label_map.items()}
        print(f"[CNNPredictor] Recognizes {len(self._labels)} gestures.")

    # ── Main prediction entry point ───────────────────────────────────────────

    def best_match(self, landmarks) -> tuple[str | None, float]:
        """
        Predicts the ASL letter from hand landmarks.

        Args:
            landmarks: 21 (x, y, z) tuples from MediaPipe.

        Returns:
            (gesture_name, confidence) e.g. ('A', 0.97)
            (None, 0.0) if landmarks are invalid.
        """
        if landmarks is None or len(landmarks) != 21:
            return None, 0.0

        if self._use_landmarks:
            return self._predict_from_landmarks(landmarks)
        else:
            return self._predict_from_image(landmarks)

    # ── Landmark-based prediction (preferred) ─────────────────────────────────

    def _predict_from_landmarks(self, landmarks) -> tuple[str | None, float]:
        """Feed normalized landmark coordinates directly to Dense model."""
        features = self._normalize_landmarks(landmarks)
        if features is None:
            return None, 0.0

        features_input = features.reshape(1, -1)
        predictions = self._model.predict(features_input, verbose=0)[0]

        top_idx = int(np.argmax(predictions))
        confidence = float(predictions[top_idx])
        gesture = self._labels[top_idx]

        print(f"[CNN] Top: {gesture} | Confidence: {confidence:.3f}")
        return gesture, confidence
        
    @staticmethod
    def _normalize_landmarks(landmarks) -> np.ndarray | None:
        """
        Normalize 21 landmarks to the hand's bounding box.

        MUST match the normalization in train_landmark_model.py exactly.
        Makes the model position-invariant and scale-invariant:
          - x, y are normalized to [0, 1] within the hand's bounding box
          - z (depth) is kept as-is (already relative in MediaPipe)
        """
        try:
            coords = np.array(
                [(lm[0], lm[1], lm[2]) for lm in landmarks],
                dtype="float32"
            )

            x = coords[:, 0].copy()
            y = coords[:, 1].copy()

            min_x, max_x = x.min(), x.max()
            min_y, max_y = y.min(), y.max()
            range_x = max(max_x - min_x, 0.001)
            range_y = max(max_y - min_y, 0.001)

            coords[:, 0] = (x - min_x) / range_x
            coords[:, 1] = (y - min_y) / range_y

            return coords.flatten()

        except Exception as e:
            print(f"[CNNPredictor] Normalization error: {e}")
            return None

    # ── CNN fallback (skeleton image) ─────────────────────────────────────────

    def _predict_from_image(self, landmarks) -> tuple[str | None, float]:
        """Convert landmarks to skeleton image for CNN. Used as fallback."""
        import cv2

        try:
            # Normalize to hand bounding box
            xs = [lm[0] for lm in landmarks]
            ys = [lm[1] for lm in landmarks]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            pad_x = (max_x - min_x) * 0.10
            pad_y = (max_y - min_y) * 0.10
            min_x = max(0.0, min_x - pad_x)
            max_x = min(1.0, max_x + pad_x)
            min_y = max(0.0, min_y - pad_y)
            max_y = min(1.0, max_y + pad_y)
            range_x = max(max_x - min_x, 0.001)
            range_y = max(max_y - min_y, 0.001)

            CANVAS = 400
            pts = []
            for lm in landmarks:
                nx = int(((lm[0] - min_x) / range_x) * (CANVAS - 40) + 20)
                ny = int(((lm[1] - min_y) / range_y) * (CANVAS - 40) + 20)
                pts.append((nx, ny))

            white = np.ones((CANVAS, CANVAS, 3), dtype=np.uint8) * 255

            connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),
                (0, 5), (5, 6), (6, 7), (7, 8),
                (5, 9), (9, 10), (10, 11), (11, 12),
                (9, 13), (13, 14), (14, 15), (15, 16),
                (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
            ]

            for start, end in connections:
                cv2.line(white, pts[start], pts[end], (0, 255, 0), 10)
            for pt in pts:
                cv2.circle(white, pt, 4, (0, 128, 0), -1)

            img = cv2.resize(white, (self.IMG_SIZE, self.IMG_SIZE))
            img = (img / 255.0).astype("float32")

            img_input = img.reshape(1, self.IMG_SIZE, self.IMG_SIZE, 3)
            predictions = self._model.predict(img_input, verbose=0)[0]

            top_idx = int(np.argmax(predictions))
            confidence = float(predictions[top_idx])
            gesture = self._labels[top_idx]

            return gesture, confidence

        except Exception as e:
            print(f"[CNNPredictor] CNN fallback error: {e}")
            return None, 0.0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def gesture_names(self) -> list[str]:
        return list(self._labels.values())

    @property
    def gesture_count(self) -> int:
        return len(self._labels)