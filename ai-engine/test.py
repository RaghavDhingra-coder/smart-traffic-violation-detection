from ultralytics import YOLO

# Load your trained model
model = YOLO("best.pt")

# Run detection
results = model("cap.webp", show=True)

# Print results
print(results)