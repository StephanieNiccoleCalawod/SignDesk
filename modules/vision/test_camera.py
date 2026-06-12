import cv2
import time

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
time.sleep(2)

for i in range(5):
    ret, frame = cap.read()
    print(f'Frame {i}: ret={ret}, shape={frame.shape if frame is not None else None}')

cap.release()
print("Done")