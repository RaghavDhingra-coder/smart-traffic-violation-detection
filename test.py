import requests, json
import base64
with open('c:/Users/ASUS/OneDrive/Desktop/smart-traffic-violation-detection/ai-engine/helmet.webp', 'rb') as f:
    img = 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')
r=requests.post('http://localhost:8001/run', json={'image_base64': img, 'source': 'webcam'})
print(r.status_code)
print(r.text)
