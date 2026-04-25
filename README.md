# Smart Traffic Violation Detection

Traffic violation detection system with:

- React + Vite frontend
- FastAPI backend
- FastAPI AI engine
- PostgreSQL
- Redis

The current codebase is best run in this mode:

- PostgreSQL and Redis in Docker
- Backend locally on port `8000`
- AI engine locally on port `8001`
- Frontend locally on port `3000`

## Current Features

- Vehicle detection with YOLOv8
- Object tracking with DeepSORT
- Number plate detection with YOLO + fallback heuristics
- OCR with EasyOCR
- Helmet violation detection using `helmet_best.pt` with safe fallback
- Triple riding detection
- Signal violation detection
- No parking detection
- Overspeeding estimation
- Challan creation flow in backend

## Project Structure

```text
smart-traffic-violation-detection/
├── ai-engine/
├── backend/
├── frontend/
├── nginx/
├── docker-compose.yml
└── README.md
```

## Ports

- Frontend: `3000`
- Backend: `8000`
- AI engine: `8001`
- PostgreSQL: `5432`
- Redis: `6379`

## Prerequisites

- Docker Desktop
- Node.js 20+
- Python 3.11 recommended
- `pip`

## Environment Setup

Copy the example env file:

```bash
cp .env.example .env
```

For local development, update `.env` so backend can reach local services:

```env
POSTGRES_DB=traffic
POSTGRES_USER=postgres
POSTGRES_PASSWORD=1234

DATABASE_URL=postgresql+psycopg2://postgres:1234@localhost:5432/traffic
REDIS_URL=redis://localhost:6379/0

RAZORPAY_KEY_ID=rzp_test_dummyKeyId
RAZORPAY_KEY_SECRET=dummyKeySecret
VAAHAN_API_KEY=dummy_vaahan_api_key

AI_ENGINE_URL=http://localhost:8001

BACKEND_CORS_ORIGINS=*
AI_ENGINE_CORS_ORIGINS=*

VITE_API_BASE_URL=/api
```

Notes:

- `frontend/vite.config.js` already proxies `/api` to `http://localhost:8000`
- If backend runs in Docker instead of locally, `AI_ENGINE_URL` should not use `localhost` unless AI engine is reachable from that container

## Recommended Local Setup

### 1. Start PostgreSQL and Redis

```bash
docker-compose up -d postgres redis
```

Verify:

```bash
docker-compose ps
```

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

### 3. Start the AI Engine

```bash
cd ai-engine
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

Health check:

```bash
curl http://localhost:8001/health
```

Expected:

```json
{"status":"ok"}
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

- Frontend: [http://localhost:3000](http://localhost:3000)

## Model Files

Place model files inside `ai-engine/`.

### Required / Supported Paths

- Vehicle detector:
  - `ai-engine/yolov8n.pt`
  - or pass a custom model with `--model`
- Plate detector:
  - `ai-engine/models/plate/best.pt`
  - older fallback path still referenced in some docs: `ai-engine/models/plate_model.pt`
- Helmet detector:
  - `ai-engine/helmet_best.pt`

Suggested structure:

```text
ai-engine/
├── yolov8n.pt
├── helmet_best.pt
└── models/
    └── plate/
        └── best.pt
```

Notes:

- If the plate model is missing, plate detection falls back to heuristics
- If `helmet_best.pt` is missing or fails to load, helmet detection falls back to the older placeholder logic instead of crashing

## Running the AI Engine Manually

### API Mode

The frontend uses the AI engine through backend -> AI engine:

- Frontend sends frames to backend `/detect`
- Backend calls AI engine `/run`

### Webcam / Local Video Mode

You can also run the AI engine directly:

```bash
cd ai-engine
python3 main.py --source 0 --enable-tracking
```

Useful flags:

```bash
python3 main.py --source 0 --enable-tracking --enable-ocr
python3 main.py --source 0 --enable-tracking --accurate-tracking
python3 main.py --source 0 --enable-tracking --helmet-model helmet_best.pt
python3 main.py --source path/to/video.mp4
```

Notes:

- Webcam mode defaults to lighter processing for better FPS
- OCR is off by default in webcam mode unless `--enable-ocr` is provided
- Tracking is off by default in webcam mode unless `--enable-tracking` is provided

## Backend Detection Flow

Current live flow:

```text
Frontend Webcam
  -> POST /api/detect
  -> Backend /detect
  -> AI Engine /run
  -> YOLO detection
  -> DeepSORT tracking
  -> violation checks
  -> OCR / plate extraction
  -> backend challan creation
```

## Troubleshooting

### Frontend shows `503 Failed to reach AI detection service`

This means:

- frontend can reach backend
- backend cannot reach AI engine

Check:

```bash
curl http://localhost:8001/health
```

If it fails:

- start or restart the AI engine
- verify `.env` has `AI_ENGINE_URL=http://localhost:8001`

### Frontend shows `500 AI engine failed`

This means backend reached AI engine, but AI engine crashed while processing a frame.

Check the AI engine terminal logs first.

### AI engine not using helmet model

Make sure this file exists:

```text
ai-engine/helmet_best.pt
```

### Plate model not found

Make sure this file exists:

```text
ai-engine/models/plate/best.pt
```

## Docker Notes

The current `docker-compose.yml` only starts:

- PostgreSQL
- Redis

Start them with:

```bash
docker-compose up -d postgres redis
```

Stop them with:

```bash
docker-compose down
```

## API Health Endpoints

- Backend root: [http://localhost:8000/](http://localhost:8000/)
- Backend health: [http://localhost:8000/health](http://localhost:8000/health)
- AI engine root: [http://localhost:8001/](http://localhost:8001/)
- AI engine health: [http://localhost:8001/health](http://localhost:8001/health)

## Current Limitation

- The repo still contains `nginx/` and Dockerfiles, but the current active setup in code and compose is local app processes plus Dockerized Postgres/Redis.
- If you later want, the README can be expanded again for a full containerized deployment path after the compose stack is updated to match the current code.
