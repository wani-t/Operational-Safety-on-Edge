import cv2
import os
print(cv2.data.haarcascades)
cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
print(os.path.exists(cascade_path))