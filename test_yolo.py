from ultralytics import YOLO
model = YOLO('runs/grocery_baseline/weights/best.pt')
img_path = 'uploads/organizations/fc7e750a-5dbd-45da-8ce7-3d747d38c5f7/audits/bc44128c-0863-4785-adea-3840b6f929e0/6f933c41-51df-4c11-be2c-7fa58964d101.jpg'
results = model(img_path, conf=0.1) # Try lower threshold
print("Found", len(results[0].boxes), "boxes at conf 0.1")
