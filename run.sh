#!/bin/bash

# go to project root (fix path issue)
cd ~/Desktop/smart-traffic-violation-detection

# start ONLY postgres + redis (not full stack)
docker-compose up postgres redis &

sleep 5

# start backend (local)
cd backend
python3.11 -m uvicorn main:app --reload &

# start AI engine
cd ../ai-engine
#!/bin/bash

cd ~/Desktop/smart-traffic-violation-detection

# Start DB + Redis
docker-compose up postgres redis &

sleep 5

# Backend
cd backend
python3.11 -m uvicorn main:app --reload &

# AI Engine
cd ../ai-engine
python3.11 -m uvicorn main:app --reload --port 8001 &

# Frontend
cd ../frontend
npm run dev
