import cv2
import numpy as np

img = np.ones((400, 400, 3), dtype=np.uint8) * 230
cv2.circle(img, (200, 200), 100, (120, 160, 210), -1)  # Head
cv2.circle(img, (160, 170), 15, (40, 40, 40), -1)     # Left eye
cv2.circle(img, (240, 170), 15, (40, 40, 40), -1)     # Right eye
cv2.ellipse(img, (200, 240), (40, 20), 0, 0, 180, (40, 40, 40), 5) # Smile

cv2.imwrite("sample_face.jpg", img)
print("Saved sample_face.jpg")
