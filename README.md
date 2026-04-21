# TODO for project-documentation: expand deployment, security hardening, and production observability before shipping.
# Traffic Violation Detection System

A hackathon-ready scaffold for a traffic violation detection platform with:

- React + Vite frontend
- FastAPI backend
- FastAPI-based AI engine
- PostgreSQL
- Redis
- Nginx reverse proxy
- Docker Compose support

This scaffold is designed so each team member can immediately start working in their own module with minimal setup friction.

## Project Structure

```text
traffic-violation-system/
├── docker-compose.yml
├── nginx/
├── frontend/
├── backend/
└── ai-engine/
```

## Setup Strategy

For this project, PostgreSQL and Redis will run using Docker only.

You can use the project in either of these ways:

1. Full Docker setup:
   Run frontend, backend, AI engine, PostgreSQL, Redis, and Nginx with Docker Compose.

2. Hybrid local development:
   Run only PostgreSQL and Redis in Docker, and run frontend, backend, and AI engine locally from your machine.

The hybrid setup is often better during development because:

- database and cache setup stay consistent across all teammates
- frontend/backend code changes reflect faster locally
- you avoid rebuilding containers for every small code change

## Prerequisites

Install these first:

- Docker Desktop
- Node.js 20+
- Python 3.11+
- `pip`

Optional but recommended:

- PostgreSQL client tools
- Redis GUI or CLI tools

## Environment Setup

1. Copy the example environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

2. Review the values inside `.env`.

Default scaffold values are already suitable for local development.

Important variables:

- `DATABASE_URL=postgresql+psycopg2://traffic_admin:traffic_password@postgres:5432/traffic_violation_db`
- `REDIS_URL=redis://redis:6379/0`
- `AI_ENGINE_URL=http://ai-engine:8001`
- `VITE_API_BASE_URL=/api`

If you run backend and AI engine locally instead of via Docker, you will usually want to change:

- `DATABASE_URL` host from `postgres` to `localhost`
- `REDIS_URL` host from `redis` to `localhost`
- `AI_ENGINE_URL` host from `ai-engine` to `http://localhost:8001`

Example local-development values:

```env
DATABASE_URL=postgresql+psycopg2://traffic_admin:traffic_password@localhost:5432/traffic_violation_db
REDIS_URL=redis://localhost:6379/0
AI_ENGINE_URL=http://localhost:8001
VITE_API_BASE_URL=http://localhost:8000
```

## Option 1: Full Docker Setup

This runs the entire stack in containers.

### Start Everything

```bash
docker-compose up --build
```

### Access URLs

- App via Nginx: `http://localhost`
- Frontend dev server: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- AI engine: `http://localhost:8001`

### Stop Everything

```bash
docker-compose down
```

To remove volumes too:

```bash
docker-compose down -v
```

## Option 2: Run PostgreSQL and Redis in Docker Only

This is the setup you requested for day-to-day development.

### Step 1: Start PostgreSQL and Redis with Docker

```bash
docker-compose up -d postgres redis
```

Verify they are running:

```bash
docker-compose ps
```

### Step 2: Update `.env` for Local App Execution

Use local hostnames for services your machine will call directly:

```env
DATABASE_URL=postgresql+psycopg2://traffic_admin:traffic_password@localhost:5432/traffic_violation_db
REDIS_URL=redis://localhost:6379/0
AI_ENGINE_URL=http://localhost:8001
VITE_API_BASE_URL=http://localhost:8000
```

### Step 3: Run the Backend Locally

Open a terminal in `backend/`:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On Windows, if `uvicorn` is not directly available:

```bash
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Run the AI Engine Locally

Open a second terminal in `ai-engine/`:

```bash
cd ai-engine
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

On Windows:

```bash
py -m pip install -r requirements.txt
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Step 5: Run the Frontend Locally

Open a third terminal in `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Then open:

- Frontend: `http://localhost:3000`

## Database Notes

PostgreSQL is provisioned by Docker Compose with:

- database: `traffic_violation_db`
- username: `traffic_admin`
- password: `traffic_password`
- port: `5432`

Data is persisted in the Docker volume:

- `postgres_data`

## Redis Notes

Redis is provisioned by Docker Compose with:

- port: `6379`
- volume: `redis_data`

The backend currently uses Redis for vehicle lookup caching.

## Backend Migration Notes

The scaffold includes Alembic files and an initial migration:

- [backend/alembic/env.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\alembic\env.py)
- [backend/alembic/versions/001_initial.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\alembic\versions\001_initial.py)

If you want to run migrations manually:

```bash
cd backend
alembic upgrade head
```

On Windows:

```bash
cd backend
py -m alembic upgrade head
```

Note:

- the current backend also calls `Base.metadata.create_all(bind=engine)` on startup
- for a real project, the team should eventually rely on Alembic migrations consistently

## How To Add The Trained YOLOv8 Model

Place your trained YOLO weights file here:

- [ai-engine/models](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\ai-engine\models)

Expected filename:

```text
ai-engine/models/best.pt
```

If `best.pt` is not present, the AI engine falls back to `yolov8n.pt`.

If you are running the AI engine in Docker and add a new model, restart that service:

```bash
docker-compose up --build ai-engine
```

If you are running the AI engine locally, just restart the local process.

## API Endpoints

### Backend

- `GET /` - backend root
- `GET /health` - backend health check
- `POST /detect` - detect violations from a base64 webcam frame
- `POST /detect/upload` - detect violations from uploaded image or video
- `GET /challan/{plate}` - fetch challans for a vehicle plate
- `POST /challan` - create a challan
- `PATCH /challan/{id}/status` - update challan status
- `GET /vehicle/{plate}` - fetch vehicle details with challan history
- `POST /payment/create-order` - create Razorpay order stub
- `POST /payment/verify` - verify Razorpay payment stub

### AI Engine

- `GET /` - AI engine root
- `GET /health` - AI engine health check
- `POST /run` - run violation detection on a base64 image

## Suggested Team Module Ownership

### Frontend team

Focus on:

- [frontend/src/pages/PoliceDashboard.jsx](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\frontend\src\pages\PoliceDashboard.jsx)
- [frontend/src/pages/UserDashboard.jsx](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\frontend\src\pages\UserDashboard.jsx)
- [frontend/src/pages/AwareUserDashboard.jsx](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\frontend\src\pages\AwareUserDashboard.jsx)
- [frontend/src/components](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\frontend\src\components)
- [frontend/src/context/AuthContext.jsx](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\frontend\src\context\AuthContext.jsx)

### Backend API team

Focus on:

- [backend/main.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\main.py)
- [backend/routers](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\routers)
- [backend/services](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\services)
- [backend/schemas](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\schemas)

### Database team

Focus on:

- [backend/models](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\models)
- [backend/database.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\database.py)
- [backend/alembic](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\backend\alembic)

### AI/CV team

Focus on:

- [ai-engine/main.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\ai-engine\main.py)
- [ai-engine/detector.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\ai-engine\detector.py)
- [ai-engine/ocr.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\ai-engine\ocr.py)
- [ai-engine/speed_estimator.py](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\ai-engine\speed_estimator.py)

### DevOps and integration team

Focus on:

- [docker-compose.yml](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\docker-compose.yml)
- [nginx/nginx.conf](c:\Users\HP\OneDrive\Desktop\smart-traffic-detection\traffic-violation-system\nginx\nginx.conf)
- frontend/backend/ai-engine Dockerfiles

## Important Development Notes

- All placeholder logic is marked with `STUB` comments.
- Both FastAPI apps currently allow all origins for CORS to keep hackathon setup simple.
- Uploaded evidence files are stored in `backend/uploads/`.
- Razorpay integration is currently a stub and not production-ready.
- Vehicle lookup is currently mocked and cached in Redis.
- AI detections are scaffolded with placeholder logic until the real trained model is integrated.

## Recommended Daily Workflow

For your team, the simplest workflow is:

1. Start PostgreSQL and Redis:

```bash
docker-compose up -d postgres redis
```

2. Run backend locally
3. Run AI engine locally
4. Run frontend locally

That gives you:

- consistent shared DB and cache services via Docker
- faster local coding and debugging
- less rebuild overhead during the hackathon
