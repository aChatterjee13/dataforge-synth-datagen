# DataForge — Synthetic Data Generation Platform

A full-stack platform for generating privacy-safe synthetic data across structured tables, time-series, PDFs, API tests, database tests, logs, CDC events, graphs, and more — powered by 11+ generative AI models.

![DataForge Upload](docs/screenshots/upload.png)

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Guide](#usage-guide)
- [Test Data](#test-data)
- [Supported Models](#supported-models)
- [API Reference](#api-reference)
- [Validation Metrics](#validation-metrics)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Structured Data Synthesis
- Upload CSV/Excel datasets with drag-and-drop interface
- 11+ model options: CTGAN, TVAE, Gaussian Copula, TimeGAN, TabDDPM, DP-CTGAN, CTAB-GAN+, Bayesian Network, RealTabFormer, DGAN, LLM Row Generator
- Auto-detection recommends the best model for your dataset
- Conditional generation with column-level constraints
- Multi-table relational synthesis preserving foreign key relationships
- SMOTE augmentation for imbalanced datasets

### Unstructured & Specialized Data
- **PDF Generation** — GPT-powered synthesis of realistic documents from sample PDFs
- **API Test Generation** — Upload OpenAPI/Swagger specs, get Postman collections and test suites
- **Database Test Data** — Upload SQL/DDL schemas, generate constraint-aware insert scripts
- **PII Detection & Masking** — Automatic PII detection across 7+ types with configurable masking strategies
- **Log Synthesis** — Pattern-based log generation matching original format and distributions
- **CDC Event Generation** — Debezium/Kafka-style change data capture events from database schemas
- **Graph/Network Synthesis** — Generate synthetic graphs preserving topology and node/edge properties

### Validation & Privacy
- Quality scores with column-wise breakdown (0-1 scale)
- Statistical tests: KS, Chi-square, KL divergence, Jensen-Shannon divergence
- Correlation preservation heatmaps (Pearson and Spearman)
- Privacy scoring with re-identification risk analysis
- Differential privacy support (Laplace, Gaussian, DP-SGD mechanisms)
- ML efficacy evaluation — measures how well synthetic data preserves predictive relationships
- Data drift detection between baseline and snapshot datasets

### Platform
- Real-time progress tracking with SSE streaming
- Preset configurations (Quick Preview, High Quality, Privacy First, and more)
- Job history with search and management
- Dataset comparison tool
- API key authentication for automation
- Interactive charts and visualizations (Recharts)
- PDF report export

---

## Screenshots

> **Add your screenshots to `docs/screenshots/` and update the paths below.**

| Screen | Preview |
|--------|---------|
| Upload & Data Type Selection | ![Upload](docs/screenshots/upload.png) |
| Configuration Panel | ![Configure](docs/screenshots/configure.png) |
| Generation Progress | ![Generate](docs/screenshots/generate.png) |
| Validation Results & Charts | ![Results](docs/screenshots/results.png) |
| Quality Metrics Dashboard | ![Quality](docs/screenshots/quality-metrics.png) |
| PDF Generation | ![PDF](docs/screenshots/pdf-generation.png) |
| API Test Generation | ![API Tests](docs/screenshots/api-tests.png) |
| DB Test Generation | ![DB Tests](docs/screenshots/db-tests.png) |
| PII Masking | ![PII](docs/screenshots/pii-masking.png) |
| Drift Detection | ![Drift](docs/screenshots/drift-detection.png) |
| Graph Synthesis | ![Graph](docs/screenshots/graph-synthesis.png) |
| Log Synthesis | ![Logs](docs/screenshots/log-synthesis.png) |
| Multi-Table Generation | ![Multi-Table](docs/screenshots/multi-table.png) |
| Job History | ![History](docs/screenshots/job-history.png) |
| Settings & API Keys | ![Settings](docs/screenshots/settings.png) |

---

## Tech Stack

### Backend
| Component | Technology |
|-----------|------------|
| Framework | FastAPI |
| Tabular Synthesis | SDV (Synthetic Data Vault), Synthcity |
| Time-Series | TimeGAN (PyTorch), DGAN (Gretel) |
| Privacy | SmartNoise (DP-CTGAN), custom metrics |
| LLM Integration | OpenAI API (GPT-4o-mini / GPT-4) |
| Database | SQLAlchemy + SQLite (PostgreSQL for production) |
| Data Processing | Pandas, NumPy, SciPy, scikit-learn |
| Graph Processing | NetworkX |
| Logging | Centralized structured logging with request tracking |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 19 + TypeScript |
| Build Tool | Vite 7 |
| Styling | Tailwind CSS |
| Charts | Recharts |
| Icons | Lucide React |
| Routing | React Router v7 |
| HTTP Client | Axios (fully typed) |

---

## Architecture

DataForge follows a **client-server architecture** with a FastAPI backend (16 domain routers, 57 endpoints) and a React SPA frontend.

```
┌─────────────┐       HTTP/REST       ┌──────────────────┐       ┌──────────┐
│   React UI  │ ◄───────────────────► │  FastAPI Server   │ ◄────►│ SQLite / │
│  (Vite/TS)  │       Axios           │  16 Domain        │       │ Postgres │
│  Port 5173  │                       │  Routers          │       └──────────┘
└─────────────┘                       │  Port 8000        │
                                      │                   │──► uploads/
                                      │                   │──► outputs/
                                      └──────────────────┘
                                              │
                                       ┌──────┴───────┐
                                       │  20+ Service  │
                                       │   Modules     │
                                       │  (ML models,  │
                                       │   validators) │
                                       └──────────────┘
```

For a detailed architecture breakdown including data flows, service interactions, database schema, and design decisions, see **[ARCHITECTURE.md](ARCHITECTURE.md)**.

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Python** | 3.11 or 3.12 | 3.13 works for core features but PyTorch lacks wheels |
| **Node.js** | 18+ | LTS recommended |
| **npm** | 9+ | Comes with Node.js |
| **Git** | 2.x | For cloning |

Optional (for advanced ML models):
- **PyTorch** 2.0+ — required for CTGAN, TVAE, TimeGAN
- **CUDA toolkit** — for GPU-accelerated training (not required)

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/<your-org>/dataforge-synth-datagen.git
cd dataforge-synth-datagen
```

### 2. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install core dependencies
pip install -r requirements.txt

# (Optional) Install ML model dependencies for full synthesis support
pip install -r requirements-ml.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OpenAI API key (needed for PDF/API/DB test generation)

# Start the backend server
uvicorn app.main:app --reload --port 8000
```

The API is now live at **http://localhost:8000**. Verify with:

```bash
curl http://localhost:8000/health
# {"status":"healthy","database":"connected"}
```

Swagger docs: **http://localhost:8000/docs**

### 3. Frontend Setup

Open a **new terminal**:

```bash
cd frontend

# Install dependencies
npm install

# (Optional) Configure API URL if backend is not on localhost:8000
cp .env.example .env

# Start the dev server
npm run dev
```

The UI is now live at **http://localhost:5173**.

### 4. Verify Installation

1. Open **http://localhost:5173** in your browser
2. Upload a CSV file (sample files are in `test-data/structured/`)
3. Choose a model (Gaussian Copula is fastest) and generate
4. View the validation results with quality scores and charts

---

## Configuration

All configuration is via environment variables. A root-level `.env.example` is provided as a reference. Copy it to the appropriate directory:

```bash
# Backend
cp .env.example backend/.env    # then edit backend/.env

# Frontend (only VITE_* vars are used)
cp .env.example frontend/.env   # or use frontend/.env.example
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./dataforge.db` | Database connection string |
| `OPENAI_API_KEY` | — | OpenAI API key for GPT-powered features |
| `OPENAI_API_ENDPOINT` | `https://api.openai.com/v1/chat/completions` | LLM API endpoint |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `MAX_UPLOAD_SIZE` | `104857600` (100 MB) | Maximum file upload size in bytes |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Frontend API base URL |

---

## Usage Guide

### Structured Data Generation

1. **Upload** — Drag and drop a CSV/XLSX file or select "Structured Data" type
2. **Configure** — Choose a synthesis model, set row count, epochs, batch size, and column-level overrides
3. **Generate** — Monitor real-time progress with the live preview
4. **Results** — Review quality scores, distribution charts, correlation heatmaps, and ML efficacy metrics
5. **Download** — Export the synthetic dataset as CSV or generate a PDF report

### PDF Generation

1. Select "PDF / Unstructured" data type and upload one or more PDFs
2. Configure GPT model, API key, and generation parameters
3. Generate synthetic PDFs that mimic the structure and content of the originals

### API / DB Test Generation

1. Upload an OpenAPI spec (YAML/JSON) or SQL schema file
2. Configure test generation parameters
3. Download Postman collections, test scripts, or SQL insert statements

### Multi-Table Generation

1. Upload multiple related CSV files
2. Define foreign-key relationships using the visual relationship builder
3. Generate coherent synthetic data that preserves referential integrity

### Other Features

- **PII Masking**: Upload a dataset, review detected PII columns, choose masking strategies
- **Drift Detection**: Upload baseline and snapshot files, view statistical drift per column
- **Graph Synthesis**: Upload CSV/JSON/GraphML edge lists, generate topology-preserving synthetic graphs
- **Log Synthesis**: Upload application/access logs, generate realistic synthetic log entries
- **CDC Testing**: Upload DB schemas, generate change-data-capture events in Debezium/Kafka format

---

## Test Data

The `test-data/` directory contains sample files for every feature:

```
test-data/
├── structured/          # CSV datasets (ecommerce_sales, healthcare_patients)
├── pdf/                 # Sample PDFs (invoices, quarterly reports)
├── api-spec/            # OpenAPI specs (petstore_api.yaml)
├── db-schema/           # SQL schemas (inventory_system.sql)
├── cdc-schema/          # CDC SQL schemas (ecommerce_cdc.sql)
├── multi-table/         # Related CSVs (customers, orders, order_items)
├── pii/                 # Customer records with PII (customer_records.csv)
├── logs/                # Application, access, and event logs
├── drift/               # Baseline and drifted snapshots
├── graph/               # Social network CSV, citation GraphML, network JSON
└── compare/             # Original vs. synthetic customer datasets
```

---

## Supported Models

### Structured Data
| Model | Library | Best For | Speed | Quality |
|-------|---------|----------|-------|---------|
| **CTGAN** | SDV | Complex tabular data | Slow | Highest |
| **TVAE** | SDV | Mixed data types | Medium | High |
| **Gaussian Copula** | SDV | Quick generation | Fastest | Good |
| **CopulaGAN** | SDV | Copula + GAN hybrid | Medium | High |
| **TabDDPM** | Synthcity | State-of-the-art diffusion | Slow | Highest |
| **Bayesian Network** | Synthcity | Interpretable generation | Fast | Good |
| **CTAB-GAN+** | Synthcity | ML utility optimized | Slow | High |
| **DP-CTGAN** | SmartNoise | Differential privacy | Slow | High |
| **RealTabFormer** | Custom | GPT-2 based tabular | Medium | High |
| **LLM Row Generator** | OpenAI | Fast prototyping | Fast | Variable |
| **Auto** | — | Auto-selects best model | — | — |

### Time-Series
| Model | Library | Best For |
|-------|---------|----------|
| **TimeGAN** | PyTorch | Temporal pattern preservation |
| **DGAN** | Gretel | Long sequence generation |

### Presets
| Preset | Model | Use Case |
|--------|-------|----------|
| Quick Preview | Gaussian Copula | Fast iteration |
| High Quality | CTGAN (500 epochs) | Production datasets |
| Privacy First | CTGAN + DP | Sensitive data |
| Time Series | TimeGAN | Temporal data |
| State of the Art | TabDDPM | Best quality |
| LLM Prototyping | LLM Row Gen | Quick mock data |
| Privacy Native | DP-CTGAN | Built-in differential privacy |

---

## API Reference

The backend exposes **57 REST endpoints** across 16 domain routers. Full interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Core Synthesis
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload` | Upload CSV/Excel dataset |
| `POST` | `/api/generate` | Start synthetic data generation |
| `POST` | `/api/generate-conditional` | Generate with column constraints |
| `GET` | `/api/status/{job_id}` | Check job progress |
| `GET` | `/api/validation/{job_id}` | Get validation metrics and charts |
| `GET` | `/api/download/{job_id}` | Download synthetic CSV |
| `GET` | `/api/preview/{job_id}` | Get data preview |
| `GET` | `/api/stream-generate/{job_id}` | SSE stream for real-time progress |
| `GET` | `/api/recommend/{job_id}` | Get model recommendation |
| `POST` | `/api/compare` | Compare two datasets |

### Multi-Table
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-multi` | Upload multiple related CSVs |
| `POST` | `/api/generate-multi` | Generate preserving relationships |

### PDF Generation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-pdfs` | Upload sample PDFs |
| `POST` | `/api/generate-pdfs` | Generate synthetic PDFs |
| `GET` | `/api/list-pdfs/{job_id}` | List generated files |
| `GET` | `/api/download-pdf/{job_id}/{filename}` | Download single PDF |
| `GET` | `/api/download-pdfs-zip/{job_id}` | Download all as ZIP |

### API Test Generation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-api-spec` | Upload OpenAPI/Swagger spec |
| `POST` | `/api/generate-api-tests` | Generate test cases |
| `GET` | `/api/api-test-results/{job_id}` | Get test results |
| `GET` | `/api/download-api-tests/{job_id}` | Download Postman/JSON suite |

### Database Test Generation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-db-schema` | Upload SQL/DDL schema |
| `POST` | `/api/generate-db-tests` | Generate test data |
| `GET` | `/api/db-test-results/{job_id}` | Get results |
| `GET` | `/api/download-db-tests/{job_id}` | Download test scripts |

### PII Masking
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-pii` | Upload dataset for PII scanning |
| `POST` | `/api/generate-pii-mask` | Apply masking strategy |
| `GET` | `/api/pii-results/{job_id}` | Get detection results |
| `GET` | `/api/download-pii/{job_id}` | Download masked data |

### Log Synthesis
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-logs` | Upload log file |
| `POST` | `/api/generate-logs` | Generate synthetic logs |
| `GET` | `/api/log-results/{job_id}` | Get synthesis results |
| `GET` | `/api/download-logs/{job_id}` | Download synthetic logs |

### CDC Event Generation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-cdc-schema` | Upload database schema |
| `POST` | `/api/generate-cdc` | Generate CDC events |
| `GET` | `/api/cdc-results/{job_id}` | Get results |
| `GET` | `/api/download-cdc/{job_id}` | Download CDC events |

### Graph/Network Synthesis
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/upload-graph` | Upload graph (CSV/JSON/GraphML/GEXF) |
| `POST` | `/api/generate-graph` | Generate synthetic graph |
| `GET` | `/api/graph-results/{job_id}` | Get results |
| `GET` | `/api/download-graph/{job_id}` | Download synthetic graph |

### Drift Detection
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/drift-detect` | Compare baseline vs snapshot |
| `POST` | `/api/drift-columns` | Get column info from a file |

### Jobs, Presets & API Keys
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/jobs` | List all jobs |
| `DELETE` | `/api/jobs/{job_id}` | Delete a job |
| `GET` | `/api/presets` | List all presets |
| `POST` | `/api/presets` | Create custom preset |
| `DELETE` | `/api/presets/{preset_id}` | Delete preset |
| `POST` | `/api/api-keys` | Create API key |
| `GET` | `/api/api-keys` | List API keys |
| `DELETE` | `/api/api-keys/{key_id}` | Revoke API key |

### Authentication

API key authentication is **optional**. When no API keys exist in the database, all requests are allowed. To enable:

1. Go to **Settings** in the UI and create an API key
2. Include the key in subsequent requests: `X-API-Key: your-key-here`

---

## Validation Metrics

### Quality Score (0-1)
Overall measure combining statistical similarity, correlation preservation, and privacy.

### Statistical Tests
- **KS Test** — Continuous variable distribution matching
- **Chi-Square Test** — Categorical variable distribution matching
- **KL Divergence** — Information-theoretic distribution distance
- **Jensen-Shannon Divergence** — Symmetric distribution distance
- **T-test** — Mean comparison between real and synthetic

### Correlation Preservation
- Pearson correlation matrix comparison
- Spearman rank correlation comparison
- Side-by-side heatmap visualization

### Privacy Score
- Distance to Closest Record (DCR)
- Re-identification risk score
- Attribute disclosure risk
- Differential privacy guarantees (when enabled)

### ML Efficacy
- Train-on-Real Test-on-Real (TRTR) vs. Train-on-Synthetic Test-on-Real (TSTR)
- LSTM and ARIMA models for time-series evaluation
- Feature importance preservation
- Target variable relationship maintenance

---

## Deployment

### Docker

Create a `docker-compose.yml` at the project root:

```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: ./backend/.env
    volumes:
      - uploads:/app/uploads
      - outputs:/app/outputs

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - VITE_API_BASE_URL=http://your-domain:8000/api

volumes:
  uploads:
  outputs:
```

**Backend Dockerfile** (`backend/Dockerfile`):

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: uncomment for full ML model support
# COPY requirements-ml.txt .
# RUN pip install --no-cache-dir -r requirements-ml.txt

COPY . .
RUN mkdir -p uploads outputs logs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Frontend Dockerfile** (`frontend/Dockerfile`):

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8000/api
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

### AWS

#### Option A: EC2 (Simple)

1. Launch an EC2 instance (t3.medium or larger, Amazon Linux 2023)
2. Install Python 3.12, Node.js 20, and Git
3. Clone the repo and follow the [Quick Start](#quick-start) steps
4. Use **systemd** to daemonize the backend, **Nginx** as reverse proxy
5. Build the frontend (`npm run build`) and serve `dist/` from Nginx
6. Open ports 80/443 in the security group

#### Option B: ECS Fargate (Production)

1. Build Docker images and push to **ECR**
2. Create an **ECS cluster** with Fargate launch type
3. Define task definitions for backend and frontend services
4. Use an **Application Load Balancer** (ALB) for routing:
   - `/api/*` → backend service (port 8000)
   - `/*` → frontend service (port 80)
5. Use **RDS PostgreSQL** instead of SQLite:
   ```
   DATABASE_URL=postgresql://user:pass@your-rds-endpoint:5432/dataforge
   ```
6. Mount **EFS** for `uploads/` and `outputs/` persistence
7. Use **Secrets Manager** for `OPENAI_API_KEY`

#### Option C: AWS App Runner

1. Push Docker images to ECR
2. Create two App Runner services (backend + frontend)
3. App Runner auto-scales and handles TLS

---

### Azure

#### Option A: Azure Container Apps (Recommended)

1. Build Docker images and push to **Azure Container Registry (ACR)**
2. Create a **Container Apps Environment**
3. Deploy backend and frontend as separate container apps
4. Use **Azure Database for PostgreSQL** for production DB
5. Use **Azure Key Vault** for secrets (`OPENAI_API_KEY`)
6. Mount **Azure Files** for upload/output persistence

```bash
az containerapp create \
  --name dataforge-backend \
  --resource-group dataforge-rg \
  --environment dataforge-env \
  --image your-acr.azurecr.io/dataforge-backend:latest \
  --target-port 8000 \
  --env-vars DATABASE_URL=secretref:db-url OPENAI_API_KEY=secretref:openai-key

az containerapp create \
  --name dataforge-frontend \
  --resource-group dataforge-rg \
  --environment dataforge-env \
  --image your-acr.azurecr.io/dataforge-frontend:latest \
  --target-port 80 \
  --ingress external
```

#### Option B: Azure App Service

1. Deploy backend as a Python App Service (B1 tier or higher)
2. Deploy frontend as a Static Web App
3. Configure application settings for environment variables

---

### GCP

#### Option A: Cloud Run (Recommended)

1. Build Docker images and push to **Artifact Registry**
2. Deploy as two Cloud Run services:

```bash
gcloud run deploy dataforge-backend \
  --image gcr.io/your-project/dataforge-backend \
  --port 8000 \
  --set-env-vars DATABASE_URL=...,OPENAI_API_KEY=... \
  --allow-unauthenticated

gcloud run deploy dataforge-frontend \
  --image gcr.io/your-project/dataforge-frontend \
  --port 80 \
  --set-env-vars VITE_API_BASE_URL=https://dataforge-backend-xxxxx.run.app/api \
  --allow-unauthenticated
```

3. Use **Cloud SQL (PostgreSQL)** for production database
4. Use **Secret Manager** for API keys
5. Use **Cloud Storage** for persistent uploads/outputs

#### Option B: GKE (Kubernetes)

1. Create a GKE Autopilot cluster
2. Deploy using Kubernetes manifests or Helm charts
3. Use Ingress with Cloud Load Balancer for routing

---

### Production Checklist

- [ ] Switch from SQLite to PostgreSQL/MySQL
- [ ] Set `CORS_ORIGINS` to your actual domain(s)
- [ ] Store secrets in your cloud provider's secret manager
- [ ] Use persistent storage (EFS / Azure Files / GCS) for `uploads/` and `outputs/`
- [ ] Enable HTTPS via a load balancer or reverse proxy
- [ ] Set `LOG_LEVEL=WARNING` for production
- [ ] Set up monitoring and alerting
- [ ] Configure database backups
- [ ] Set appropriate `MAX_UPLOAD_SIZE` for your use case
- [ ] Remove or restrict Swagger UI in production (`/docs`, `/redoc`)

---

## Project Structure

```
dataforge-synth-datagen/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, middleware, router registration
│   │   ├── api/
│   │   │   ├── models.py            # Pydantic request/response schemas (550+ lines)
│   │   │   └── routers/             # 16 domain-specific route modules
│   │   │       ├── core.py          #   Upload, generate, status, download, jobs
│   │   │       ├── compare.py       #   Dataset comparison
│   │   │       ├── presets.py       #   Configuration presets
│   │   │       ├── model_rec.py     #   Model recommendation engine
│   │   │       ├── api_keys.py      #   API key CRUD
│   │   │       ├── multi_table.py   #   Multi-table relational generation
│   │   │       ├── conditional.py   #   Conditional generation
│   │   │       ├── drift.py         #   Drift detection
│   │   │       ├── streaming.py     #   SSE streaming & live preview
│   │   │       ├── pdf.py           #   PDF synthesis (GPT-powered)
│   │   │       ├── api_testing.py   #   API test generation from OpenAPI specs
│   │   │       ├── db_testing.py    #   DB test data from SQL schemas
│   │   │       ├── pii.py           #   PII detection & masking
│   │   │       ├── logs.py          #   Log synthesis
│   │   │       ├── cdc.py           #   CDC event generation
│   │   │       └── graph.py         #   Graph/network synthesis
│   │   ├── db/
│   │   │   └── database.py          # SQLAlchemy ORM models (Job, Preset, APIKey)
│   │   ├── middleware/
│   │   │   ├── auth.py              # API key authentication
│   │   │   └── request_tracking.py  # Request ID injection
│   │   ├── services/                # 20+ business logic modules
│   │   │   ├── generator.py         #   Core SDV synthesis engine
│   │   │   ├── validator.py         #   Statistical validation & quality scoring
│   │   │   ├── privacy.py           #   Privacy metrics (DCR, re-identification)
│   │   │   ├── novel_quality.py     #   Advanced ML efficacy metrics
│   │   │   ├── timegan_pytorch.py   #   PyTorch TimeGAN implementation
│   │   │   ├── timeseries_metrics.py #  LSTM/ARIMA time-series evaluation
│   │   │   ├── pdf_generator.py     #   GPT-powered PDF generation
│   │   │   ├── api_test_generator.py #  OpenAPI → test cases
│   │   │   ├── db_test_generator.py #   SQL → test data
│   │   │   ├── pii_masker.py        #   PII detection and masking
│   │   │   ├── log_synthesizer.py   #   Log pattern synthesis
│   │   │   ├── cdc_generator.py     #   CDC event generation
│   │   │   ├── graph_synthesizer.py #   Graph/network synthesis
│   │   │   ├── multi_table_generator.py
│   │   │   ├── drift_detector.py    #   Statistical drift analysis
│   │   │   ├── llm_client.py        #   Shared OpenAI API client
│   │   │   ├── llm_row_generator.py #   LLM-based row generation
│   │   │   ├── smote_processor.py   #   SMOTE augmentation
│   │   │   ├── synthcity_adapter.py #   Synthcity model wrapper
│   │   │   ├── realtabformer_adapter.py
│   │   │   └── dgan_generator.py    #   DGAN time-series wrapper
│   │   └── utils/
│   │       ├── logger.py            # Centralized logging with request context
│   │       └── file_handler.py      # File upload utilities
│   ├── requirements.txt             # Core Python dependencies
│   ├── requirements-ml.txt          # Optional ML model dependencies
│   ├── .env.example                 # Backend env template
│   ├── run.sh                       # Dev start script (with TF env vars)
│   └── start.sh                     # Full setup + start script
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Router (25 routes) & error boundary
│   │   ├── main.tsx                 # React entry point
│   │   ├── pages/                   # 23 page components
│   │   │   ├── Upload.tsx           #   File upload & data type selection
│   │   │   ├── Configure.tsx        #   Model & parameter configuration
│   │   │   ├── Generate.tsx         #   Generation progress tracking
│   │   │   ├── Results.tsx          #   Validation results & charts
│   │   │   └── ...                  #   (20 more feature-specific pages)
│   │   ├── components/              # 27 reusable UI components
│   │   │   ├── ErrorBanner.tsx      #   Dismissible error banner
│   │   │   ├── GPTConfigSection.tsx #   GPT model/key config
│   │   │   ├── CorrelationHeatmap.tsx
│   │   │   ├── NetworkGraph.tsx
│   │   │   └── ...
│   │   ├── services/api.ts          # Typed Axios API client
│   │   ├── types/index.ts           # TypeScript type definitions (900+ lines)
│   │   ├── lib/utils.ts             # Utility functions (cn, error helpers)
│   │   └── utils/reportGenerator.ts # PDF report export
│   ├── .env.example
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── test-data/                       # Sample files for every feature
├── docs/
│   └── screenshots/                 # UI screenshots (add your own)
├── .env.example                     # Root env template (combined)
├── .gitignore
├── ARCHITECTURE.md                  # Detailed architecture document
└── README.md                        # This file
```

---

## Troubleshooting

### Backend Issues

**Import errors:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Database errors:**
Delete `dataforge.db` and restart — the database is recreated automatically.

**LLM timeout errors:**
The LLM client uses a 120-second timeout with exponential backoff retries. If you still see timeouts:
- Check your OpenAI API key is valid
- Try a faster model (gpt-4o-mini)
- Reduce the complexity of uploaded specs/schemas

**TensorFlow mutex errors on macOS:**
The `run.sh` script sets the required environment variables. If running manually:
```bash
export TF_CPP_MIN_LOG_LEVEL=3
export KMP_DUPLICATE_LIB_OK=TRUE
```

### Frontend Issues

**Module not found:**
```bash
rm -rf node_modules package-lock.json
npm install
```

**CORS errors:**
Ensure the backend is running on port 8000. Check that `CORS_ORIGINS` includes your frontend URL.

### Performance Tips

- **Quick testing**: Use Gaussian Copula or the "Quick Preview" preset
- **Best quality**: Use CTGAN or TabDDPM with 500+ epochs
- **Large datasets (>10K rows)**: Use CTGAN with 300 epochs
- **Privacy-sensitive data**: Use DP-CTGAN with epsilon 0.1-1.0
- **Time-series**: Use TimeGAN with appropriate sequence length
- **API test generation**: Complex OpenAPI specs (30+ endpoints) take 3-5 minutes

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes and verify:
   ```bash
   # Backend
   cd backend && python -c "from app.main import app; print(len(app.routes), 'routes')"

   # Frontend
   cd frontend && npx tsc --noEmit && npm run build
   ```
4. Commit and open a pull request

---

## License

MIT

---

## Acknowledgments

- [SDV (Synthetic Data Vault)](https://docs.sdv.dev/sdv) by DataCebo
- [Synthcity](https://github.com/vanderschaarlab/synthcity) by van der Schaar Lab
- [FastAPI](https://fastapi.tiangolo.com) by Sebastian Ramirez
- [React](https://react.dev) and [Vite](https://vitejs.dev)
- [Tailwind CSS](https://tailwindcss.com)
- [Recharts](https://recharts.org)
- [OpenAI](https://platform.openai.com) for LLM-powered generation
