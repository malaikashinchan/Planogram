from ultralytics import YOLO
model = YOLO('runs/grocery_baseline/weights/best.pt')
print(model.names)
