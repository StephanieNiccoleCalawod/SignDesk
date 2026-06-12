"""
Landmark Data Collection Tool for SignDesk
==========================================
Collects hand landmark coordinates from the camera for each ASL letter.
Run in Anaconda Prompt with (signdesk) environment active.

Usage:
    python training/collect_landmarks.py

Controls:
    SPACE  = Start/stop collecting for current letter (8 seconds)
    N      = Save & move to next letter
    R      = Redo current letter (clear samples)
    ESC    = Save current letter & quit
"""

import os
import sys
import cv2
import numpy as np
import time

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ── Configuration ──────────────────────────────────────────────
SAVE_DIR           = "training/landmark_data"
LETTERS            = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
COLLECTION_SECONDS = 8      # seconds per collection burst
MODEL_PATH         = "modules/vision/hand_landmarker.task"

# Hand connections for drawing overlay
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    # ── Verify model file exists ──────────────────────────────
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: MediaPipe model not found at '{MODEL_PATH}'")
        print("Make sure you run this from the SignDesk project root.")
        sys.exit(1)

    # ── Initialize MediaPipe HandLandmarker ────────────────────
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # ── Open camera ───────────────────────────────────────────
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera")
        sys.exit(1)

    print("=" * 55)
    print("    SIGNDESK — LANDMARK DATA COLLECTION")
    print("=" * 55)
    print("  SPACE  = Start collecting (8 seconds)")
    print("  N      = Save & next letter")
    print("  R      = Redo current letter")
    print("  ESC    = Save & quit")
    print("=" * 55)
    print()
    print("TIP: Move your hand slightly while signing")
    print("     to capture natural variation!")
    print()

    letter_idx = 0

    while letter_idx < len(LETTERS):
        letter = LETTERS[letter_idx]
        samples = []
        collecting = False
        start_time = None

        # Check existing data
        existing_path = os.path.join(SAVE_DIR, f"{letter}.npy")
        if os.path.exists(existing_path):
            existing = np.load(existing_path)
            print(f"[{letter}] Found {len(existing)} existing samples. "
                  f"Press SPACE to add more, R to redo, N to skip.")

        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera feed lost!")
                break

            h, w = frame.shape[:2]

            # ── Detect hand (same as tracker.py — no flip) ────
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB, data=rgb
            )
            results = detector.detect(mp_image)
            hand_detected = bool(results.hand_landmarks)

            # ── Draw landmarks on frame ───────────────────────
            if hand_detected:
                hand = results.hand_landmarks[0]
                pixels = [(int(lm.x * w), int(lm.y * h)) for lm in hand]

                for s, e in HAND_CONNECTIONS:
                    cv2.line(frame, pixels[s], pixels[e], (0, 255, 0), 2)
                for pt in pixels:
                    cv2.circle(frame, pt, 4, (0, 255, 0), -1)

            # ── UI: Header ────────────────────────────────────
            cv2.rectangle(frame, (0, 0), (w, 80), (30, 30, 30), -1)
            cv2.putText(
                frame, f"Sign: {letter}",
                (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.8,
                (0, 255, 0), 3
            )
            cv2.putText(
                frame, f"({letter_idx + 1}/26)",
                (220, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                (150, 150, 150), 2
            )
            cv2.putText(
                frame, f"Samples: {len(samples)}",
                (w - 220, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (0, 255, 255), 2
            )

            # ── UI: Status bar ────────────────────────────────
            if collecting:
                elapsed = time.time() - start_time
                remaining = max(0, COLLECTION_SECONDS - elapsed)
                progress = min(elapsed / COLLECTION_SECONDS, 1.0)

                cv2.rectangle(frame, (0, h - 70), (w, h), (0, 0, 180), -1)
                cv2.putText(
                    frame, f"COLLECTING... {remaining:.1f}s",
                    (20, h - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                    (255, 255, 255), 2
                )

                # Progress bar
                bar_w = int(progress * (w - 40))
                cv2.rectangle(
                    frame, (20, h - 75), (20 + bar_w, h - 72),
                    (0, 255, 0), -1
                )

                # Auto-stop after time limit
                if elapsed >= COLLECTION_SECONDS:
                    collecting = False
                    print(f"  [{letter}] Burst complete: {len(samples)} samples")

            else:
                if hand_detected:
                    cv2.rectangle(
                        frame, (0, h - 45), (w, h), (0, 80, 0), -1
                    )
                    cv2.putText(
                        frame, "Hand OK! Press SPACE to collect",
                        (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 255), 2
                    )
                else:
                    cv2.rectangle(
                        frame, (0, h - 45), (w, h), (80, 0, 0), -1
                    )
                    cv2.putText(
                        frame, "Show your hand to the camera",
                        (20, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (200, 200, 200), 2
                    )

            # ── Collect landmarks during burst ────────────────
            if collecting and hand_detected:
                hand = results.hand_landmarks[0]
                lm_array = []
                for lm in hand:
                    lm_array.extend([lm.x, lm.y, lm.z])
                samples.append(lm_array)

            # ── Display frame ─────────────────────────────────
            cv2.imshow("SignDesk — Collect Landmarks", frame)
            key = cv2.waitKey(1) & 0xFF

            # ── Key handling ──────────────────────────────────
            if key == ord(' ') and not collecting:
                collecting = True
                start_time = time.time()
                print(f"  [{letter}] Collecting...")

            elif key == ord('n'):
                _save_samples(SAVE_DIR, letter, samples)
                letter_idx += 1
                break

            elif key == ord('r'):
                samples = []
                print(f"  [{letter}] Reset — signing again")

            elif key == 27:  # ESC
                _save_samples(SAVE_DIR, letter, samples)
                _cleanup(cap, detector)
                print("\nCollection ended. Run again to continue.")
                sys.exit(0)

    _cleanup(cap, detector)
    print("\n" + "=" * 55)
    print("    ALL 26 LETTERS COLLECTED!")
    print("=" * 55)
    print(f"  Data saved to: {SAVE_DIR}/")
    print()
    print("  Next step:")
    print("    python training/train_landmark_model.py")
    print()


def _save_samples(save_dir, letter, samples):
    """Save collected samples to .npy file."""
    if not samples:
        print(f"  [{letter}] No samples to save, skipping")
        return

    path = os.path.join(save_dir, f"{letter}.npy")

    # Append to existing data if present
    if os.path.exists(path):
        existing = np.load(path)
        arr = np.concatenate([existing, np.array(samples, dtype="float32")])
    else:
        arr = np.array(samples, dtype="float32")

    np.save(path, arr)
    print(f"  [{letter}] Saved {len(arr)} total samples → {path}")


def _cleanup(cap, detector):
    cap.release()
    cv2.destroyAllWindows()
    detector.close()


if __name__ == "__main__":
    main()
