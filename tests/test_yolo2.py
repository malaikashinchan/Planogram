from ultralytics import YOLO
import cv2

model = YOLO('runs/grocery_baseline/weights/best.pt')
img = cv2.imread('test_image.jpg')
results = model(img, conf=0.1) # low conf
print("Boxes at 0.1:", len(results[0].boxes))

results_high = model(img, conf=0.25)
print("Boxes at 0.25:", len(results_high[0].boxes))
