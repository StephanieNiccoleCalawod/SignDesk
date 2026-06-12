import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

base_options = python.BaseOptions(
    model_asset_path='modules/vision/hand_landmarker.task'
)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1
)
detector = vision.HandLandmarker.create_from_options(options)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_image)

    if result.hand_landmarks:
        landmarks = result.hand_landmarks[0]

        # Extract raw x, y
        xs = [lm.x for lm in landmarks]
        ys = [lm.y for lm in landmarks]

        # Normalize to hand bounding box with padding
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        pad = 0.1
        min_x -= pad; max_x += pad
        min_y -= pad; max_y += pad
        range_x = max(max_x - min_x, 0.001)
        range_y = max(max_y - min_y, 0.001)

        CANVAS = 400
        pts = []
        for lm in landmarks:
            nx = int(((lm.x - min_x) / range_x) * (CANVAS - 40) + 20)
            ny = int(((lm.y - min_y) / range_y) * (CANVAS - 40) + 20)
            pts.append((nx, ny))

        white = np.ones((CANVAS, CANVAS, 3), dtype=np.uint8) * 255
        connections = [
            (0,1),(1,2),(2,3),(3,4),
            (0,5),(5,6),(6,7),(7,8),
            (0,9),(9,10),(10,11),(11,12),
            (0,13),(13,14),(14,15),(15,16),
            (0,17),(17,18),(18,19),(19,20),
            (5,9),(9,13),(13,17)
        ]
        for s, e in connections:
            cv2.line(white, pts[s], pts[e], (0,255,0), 3)
        for pt in pts:
            cv2.circle(white, pt, 4, (0,0,255), -1)

        cv2.imshow("What CNN Sees", white)

    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()