# Production-Grade Task Queue Service

A production-ready async job processing service built with FastAPI, Celery, Redis, and MongoDB, complete with containerization, CI/CD, comprehensive observability, and an AWS deployment.

## 🌐 Live Application Links

- **Application API**: [https://craon.rajatrulaniya.com](https://craon.rajatrulaniya.com)
- **API Documentation**: [https://craon.rajatrulaniya.com/docs](https://craon.rajatrulaniya.com/docs)
- **Prometheus Metrics**: [https://craon.rajatrulaniya.com/prometheus](https://craon.rajatrulaniya.com/prometheus)
- **Grafana Dashboards**: [https://craon.rajatrulaniya.com/grafana](https://craon.rajatrulaniya.com/grafana)

---

## 🏗️ Architecture & AWS Deployment

The application is deployed to AWS on a **t3.medium EC2 instance**. Traffic is securely served over **HTTPS via Let's Encrypt** certificates, with **Nginx** functioning as a reverse proxy to route requests to the appropriate Docker containers (FastAPI, Prometheus, Grafana).

### 🧠 System Flow
1. Client sends `POST /jobs` request
2. FastAPI validates and stores job in MongoDB (status = `pending`)
3. Job is pushed to Redis queue via Celery
4. Worker consumes job → updates status to `processing`
5. Task executes → success/failure
6. Final state stored in MongoDB
7. Metrics emitted → Prometheus → Grafana dashboards

### 🏗️ Design Decisions
- **Celery + Redis**: Chosen for simplicity and reliability in async job processing.
- **MongoDB**: Flexible schema for job payloads and state tracking.
- **Docker Compose**: Ensures reproducible local + production environments.
- **EC2 deployment**: Chosen for rapid iteration and simplicity; system remains containerized and portable to ECS/EKS.
- **Nginx reverse proxy**: Single entry point with path-based routing and HTTPS termination.
- **Prometheus + Grafana**: Full observability stack with automated provisioning.

### Nginx Reverse Proxy Configuration (`craon-project.conf`)
The Nginx configuration plays a critical role in the deployment by routing traffic securely to the correct internal Docker containers:
- **Root (`/`)**: Proxies incoming API traffic directly to the FastAPI server on port `8000`.
- **Prometheus (`/prometheus/`)**: Proxies metrics dashboard traffic to the Prometheus container on port `9090`, allowing external access without exposing the port directly.
- **Grafana (`/grafana/`)**: Proxies visualization dashboard traffic to the Grafana container on port `3000`.
- Both `/prometheus` and `/grafana` paths include exact-match redirects to ensure trailing slashes are appended properly, facilitating correct relative path resolution for the UIs.


---

## 🚀 Features

### Part 1: REST API and Job Queue
- **Async Job Queue**: Enqueue jobs via REST API, process asynchronously using Celery and Redis.
- **State Persistence**: Job states (pending → processing → completed/failed) persisted in MongoDB using Beanie ODM.
- **Retry Logic**: Automatic retries with exponential backoff and jitter (max 3 retries).
- **Rate Limiting**: 10 POST requests per minute per IP using `slowapi` backed by Redis.
- **Simulated Tasks**: `parse_csv`, `send_email`, and `process_data`.

### Part 2: Containerization & CI/CD
- **Dockerized**: Fully containerized API, Worker, Redis, and MongoDB with health checks and dependency ordering.
- **CI/CD Pipeline**: Automated using GitHub Actions with three jobs:
  1. `test_and_lint`: Runs Ruff linter and tests.
  2. `build_and_push`: Builds Docker image and pushes to Docker Hub registry.
  3. `deploy_to_EC2`: Pulls the latest image via SSH and restarts the `docker-compose` stack on the EC2 instance.

### Part 3: Observability
- **Prometheus**: Exposed `/metrics` via `prometheus-fastapi-instrumentator`. Set up via Docker Compose with persistent volumes. Explicitly tracks:
  - **Queue depth gauge**
  - **Processing duration histogram**
  - **Job counters** (enqueued and completed)
- **Grafana**: Pre-configured dashboards automatically loaded via provisioning. Persistent data and set up for reverse proxy routing.
- **Alerts**: Grafana alerts configured to fire if queue depth exceeds 50 for more than 2 minutes.
- **Structured Logging**: Implemented via `structlog`, capturing request ID, user ID, job ID, duration, and status in JSON format.

### Part 4: AWS Deployment
- **Compute**: Deployed API and worker to AWS on a **t3.medium EC2 instance** for rapid iteration and simplicity.
- **Domain & SSL**: Exposed securely via `craon.rajatrulaniya.com` with HTTPS termination handled by Let's Encrypt Certbot.
- **Reverse Proxy**: Nginx utilized as a single entry point with path-based routing to internal Docker containers.
- **Automated Delivery**: Extended GitHub Actions pipeline to automatically pull the latest image and restart the `docker-compose` stack on the EC2 instance upon merge to `main`.

---

## 💻 How to Run Locally

### Option 1: Docker Compose (Recommended)
This is the easiest way to run the entire stack (API, Worker, Database, Cache, and Observability).

```bash
# 1. Clone the repository
git clone https://github.com/Rajat-Rulaniya/task-queue-service.git
cd task-queue-service

# 2. Setup environment variables
cp .env.example .env

# 3. Start the entire stack
docker-compose up -d
```

> **Note on Local Observability:** 
> The `docker-compose.yml` is configured for production deployment behind an Nginx reverse proxy. If you want to access Prometheus and Grafana locally on your machine, you must comment out the following deployment-specific lines in `docker-compose.yml`:
> - Under **`prometheus`** -> `command`:
>   - `"--web.external-url=http://craon.rajatrulaniya.com/prometheus"`
>   - `"--web.route-prefix=/prometheus"`
> - Under **`grafana`** -> `environment`:
>   - `- GF_SERVER_ROOT_URL=http://craon.rajatrulaniya.com/grafana/`
>   - `- GF_SERVER_SERVE_FROM_SUB_PATH=true`

### Option 2: Single Terminal Setup (Without Docker)

*Prerequisites: Python 3.10, Redis, and MongoDB must be installed and running locally.*

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up environment:
   ```bash
   cp .env.example .env
   ```
3. Start FastAPI server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. Start Celery worker (in a new terminal):
   ```bash
   celery -A worker worker --loglevel=info -c 4
   ```

---

## 📁 Codebase Structure

| Directory / File | Description |
|------------------|-------------|
| `main.py` | FastAPI application initialization, routing, and observability setup. |
| `routes.py` | API endpoint definitions (`POST /jobs`, `GET /jobs`, `GET /jobs/:id`). |
| `tasks.py` | Celery task definitions (`parse_csv`, `send_email`, etc.) and retry logic. |
| `worker.py` | Celery application entry point and worker setup. |
| `models.py` | Database schema using Beanie ODM. |
| `database.py` | MongoDB connection logic. |
| `logger.py` | Structlog configuration for structured JSON logging. |
| `metrics.py` | Prometheus custom metric definitions. |
| `.github/workflows/cicd.yaml` | GitHub Actions pipeline configuration. |
| `Dockerfile` | Multi-purpose container image definition for the API and Worker. |
| `docker-compose.yml` | Full stack orchestration including Observability and Databases. |
| `craon-project.conf` | Nginx reverse proxy configuration. |
| `Observability/` | Prometheus configuration and Grafana provisioning (dashboards & alerts). |

---

## 🧪 Testing the API

### Create a Job
```bash
curl -X POST https://craon.rajatrulaniya.com/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "parse_csv",
    "payload": {
      "csv_data": "name,age\nJohn,30\nJane,28"
    }
  }'
```

### Check Job Status
```bash
curl https://craon.rajatrulaniya.com/api/v1/jobs/{job_id}
```

### List Jobs (Paginated)
```bash
curl "https://craon.rajatrulaniya.com/api/v1/jobs?page=1&page_size=10"
```

### Automated Testing Script
An automated integration test script is included in the repository. You can run `test_service.py` to validate all core functionality end-to-end. 

To test against the deployed instance, simply update the `BASE_URL` at the top of `test_service.py`:
```python
BASE_URL = "https://craon.rajatrulaniya.com/api/v1"
```
Then run the script:
```bash
python test_service.py
```
