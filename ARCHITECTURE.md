# DataForge — Architecture Document

This document describes the system architecture, component interactions, data flows, and design decisions of the DataForge Synthetic Data Generation Platform.

---

## Table of Contents

- [System Overview](#system-overview)
- [High-Level Architecture](#high-level-architecture)
- [Backend Architecture](#backend-architecture)
  - [Application Entry Point](#application-entry-point)
  - [Router Layer (API)](#router-layer-api)
  - [Service Layer](#service-layer)
  - [Data Layer](#data-layer)
  - [Middleware](#middleware)
  - [Logging](#logging)
- [Frontend Architecture](#frontend-architecture)
  - [Application Structure](#application-structure)
  - [Routing](#routing)
  - [API Client](#api-client)
  - [Component Hierarchy](#component-hierarchy)
- [Data Flow](#data-flow)
  - [Structured Data Generation Flow](#structured-data-generation-flow)
  - [GPT-Powered Feature Flow](#gpt-powered-feature-flow)
  - [Background Task Pattern](#background-task-pattern)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [Synthesis Engine](#synthesis-engine)
  - [Model Selection](#model-selection)
  - [Model Adapters](#model-adapters)
  - [Validation Pipeline](#validation-pipeline)
- [Key Design Decisions](#key-design-decisions)
- [Security Considerations](#security-considerations)
- [Scalability & Limitations](#scalability--limitations)
- [Dependency Architecture](#dependency-architecture)

---

## System Overview

DataForge is a **monorepo** containing two independently deployable applications:

| Component | Technology | Port | Role |
|-----------|-----------|------|------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy | 8000 | REST API, ML model orchestration, file management |
| **Frontend** | React 19, TypeScript, Vite | 5173 | Single-page application, data visualization |

Communication between frontend and backend is exclusively via **HTTP REST API** over JSON, with **Server-Sent Events (SSE)** for real-time progress streaming.

---

## High-Level Architecture

```
                              ┌──────────────────────────────────────────────┐
                              │                   Client                      │
                              │                                              │
                              │   React 19 + TypeScript + Vite               │
                              │   ┌──────────┐ ┌──────────┐ ┌──────────┐   │
                              │   │  Pages    │ │Components│ │ Services │   │
                              │   │  (23)     │ │  (27)    │ │ api.ts   │   │
                              │   └──────────┘ └──────────┘ └────┬─────┘   │
                              │                                   │         │
                              └───────────────────────────────────┼─────────┘
                                                                  │
                                            HTTP/REST + SSE       │  Axios
                                                                  │
                              ┌───────────────────────────────────┼─────────┐
                              │              FastAPI Server        │         │
                              │                                   ▼         │
                              │   ┌──────────────────────────────────────┐  │
                              │   │           Middleware Stack            │  │
                              │   │  RequestTracking → UploadSizeLimit   │  │
                              │   │  → CORS → APIKeyAuth                 │  │
                              │   └──────────────────┬───────────────────┘  │
                              │                      │                      │
                              │   ┌──────────────────▼───────────────────┐  │
                              │   │         Router Layer (16 routers)     │  │
                              │   │                                      │  │
                              │   │  core │ pdf │ api_testing │ drift    │  │
                              │   │  compare │ pii │ logs │ cdc │ graph  │  │
                              │   │  presets │ api_keys │ streaming      │  │
                              │   │  model_rec │ multi_table │ conditional│ │
                              │   │  db_testing                          │  │
                              │   └──────────────────┬───────────────────┘  │
                              │                      │                      │
                              │   ┌──────────────────▼───────────────────┐  │
                              │   │         Service Layer (20+ modules)  │  │
                              │   │                                      │  │
                              │   │  generator │ validator │ privacy     │  │
                              │   │  pdf_generator │ api_test_generator  │  │
                              │   │  db_test_generator │ pii_masker      │  │
                              │   │  log_synthesizer │ cdc_generator     │  │
                              │   │  graph_synthesizer │ drift_detector  │  │
                              │   │  timegan_pytorch │ novel_quality     │  │
                              │   │  multi_table_generator │ llm_client  │  │
                              │   │  smote_processor │ synthcity_adapter │  │
                              │   │  realtabformer_adapter │ dgan_gen    │  │
                              │   └──────────┬──────────────┬────────────┘  │
                              │              │              │               │
                              │   ┌──────────▼──────┐ ┌────▼────────────┐  │
                              │   │   SQLAlchemy     │ │  File System    │  │
                              │   │   (SQLite/PG)    │ │  uploads/       │  │
                              │   │   Jobs, Presets,  │ │  outputs/       │  │
                              │   │   APIKeys        │ │  logs/          │  │
                              │   └─────────────────┘ └─────────────────┘  │
                              │                                             │
                              └─────────────────────────────────────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │   External Services  │
                                   │                      │
                                   │   OpenAI API         │
                                   │   (GPT-4o / 4o-mini) │
                                   └─────────────────────┘
```

---

## Backend Architecture

### Application Entry Point

**File**: `backend/app/main.py`

The FastAPI application is configured in a specific order:

1. **Environment loading** — `dotenv` loads `.env` before any imports
2. **TensorFlow env vars** — Prevents macOS mutex deadlocks
3. **Middleware registration** — Order matters (first registered = outermost):
   - `RequestTrackingMiddleware` — Injects unique request IDs
   - `UploadSizeLimitMiddleware` — Rejects oversized uploads (configurable, default 100 MB)
   - `CORSMiddleware` — Configurable origin allowlist
4. **Router registration** — All 16 routers mounted at `/api` with shared auth dependency
5. **Health endpoint** — `/health` with database connectivity check

```python
# All routers share the same auth dependency
for r in _all_routers:
    app.include_router(r, prefix="/api", dependencies=[Depends(verify_api_key)])
```

### Router Layer (API)

The API is organized into **16 domain routers**, each in its own file under `backend/app/api/routers/`. This replaced a previous monolithic `routes.py` (2,280 lines) for better maintainability.

| Router | File | Endpoints | Domain |
|--------|------|-----------|--------|
| `core` | `core.py` | 7 | Upload, generate, status, download, validation, jobs |
| `compare` | `compare.py` | 1 | Dataset comparison |
| `presets` | `presets.py` | 3 | Configuration preset CRUD |
| `model_rec` | `model_rec.py` | 1 | ML model recommendation |
| `api_keys` | `api_keys.py` | 3 | API key management |
| `multi_table` | `multi_table.py` | 2 | Multi-table relational generation |
| `conditional` | `conditional.py` | 1 | Conditional generation with constraints |
| `drift` | `drift.py` | 2 | Statistical drift detection |
| `streaming` | `streaming.py` | 2 | SSE progress streaming, data preview |
| `pdf` | `pdf.py` | 5 | PDF upload, generation, download |
| `api_testing` | `api_testing.py` | 4 | OpenAPI spec → test suites |
| `db_testing` | `db_testing.py` | 4 | SQL schema → test data |
| `pii` | `pii.py` | 4 | PII detection and masking |
| `logs` | `logs.py` | 4 | Log synthesis |
| `cdc` | `cdc.py` | 4 | CDC event generation |
| `graph` | `graph.py` | 4 | Graph/network synthesis |
| | | **57 total** | |

**Router conventions:**
- Each router creates its own `APIRouter()` instance
- File uploads use `multipart/form-data` with FastAPI's `UploadFile`
- Long-running tasks use FastAPI's `BackgroundTasks` for async processing
- All routers use `HTTPException` for error responses
- Exception handlers follow the pattern: `except HTTPException: raise` before `except Exception`

### Service Layer

Services contain all business logic and are called by routers. They are **stateless** — all state lives in the database or file system.

#### Core Services

| Service | Responsibility |
|---------|---------------|
| `generator.py` | Orchestrates synthesis: loads data, selects model, trains, generates, saves output. Supports 11+ models with automatic fallbacks. |
| `validator.py` | Computes quality scores: distribution similarity (KS, chi-square, KL divergence), correlation preservation, privacy metrics, ML efficacy. |
| `privacy.py` | Calculates privacy-specific metrics: Distance to Closest Record, re-identification risk, attribute disclosure risk. |
| `novel_quality.py` | Advanced validation: ML efficacy (train-on-synthetic test-on-real), feature importance, rare event preservation, boundary analysis. |

#### Synthesis Adapters

Each ML library is wrapped in an adapter that normalizes the interface:

| Adapter | Library | Models Provided |
|---------|---------|----------------|
| `generator.py` (built-in) | SDV | CTGAN, TVAE, Gaussian Copula, CopulaGAN |
| `synthcity_adapter.py` | Synthcity | TabDDPM, CTAB-GAN+, Bayesian Network |
| `realtabformer_adapter.py` | REaLTabFormer | GPT-2 based tabular |
| `dgan_generator.py` | Gretel Synthetics | DGAN time-series |
| `timegan_pytorch.py` | Custom PyTorch | TimeGAN |
| `llm_row_generator.py` | OpenAI API | LLM Row Generator |
| `smote_processor.py` | imbalanced-learn | SMOTE augmentation |

**Lazy loading**: All optional ML libraries are imported at call time with try/except. If a library is missing, the model gracefully falls back to a simpler alternative (typically Gaussian Copula).

#### GPT-Powered Services

| Service | External Dependency | Function |
|---------|-------------------|----------|
| `pdf_generator.py` | OpenAI API | Extracts PDF structure, generates synthetic documents |
| `api_test_generator.py` | OpenAI API | Parses OpenAPI specs, generates Postman collections |
| `db_test_generator.py` | OpenAI API | Parses SQL schemas, generates test data and queries |
| `llm_client.py` | OpenAI API | Shared HTTP client with retry logic and timeout handling |

#### Specialized Services

| Service | Function |
|---------|----------|
| `pii_masker.py` | Regex + heuristic PII detection across 7+ types, configurable masking |
| `log_synthesizer.py` | Pattern extraction and synthesis for application/access/event logs |
| `cdc_generator.py` | Generates Debezium-style CDC events from database schemas |
| `graph_synthesizer.py` | NetworkX-based graph analysis and topology-preserving synthesis |
| `drift_detector.py` | Column-level statistical drift analysis (KS, chi-square, PSI) |
| `multi_table_generator.py` | Referential integrity-preserving multi-table generation |
| `timeseries_metrics.py` | LSTM and ARIMA-based time-series quality evaluation |

### Data Layer

**File**: `backend/app/db/database.py`

DataForge uses SQLAlchemy ORM with three tables:

```
┌─────────────────────────────────────────────────────┐
│                        Job                           │
├─────────────────────────────────────────────────────┤
│ id (PK)          │ UUID string                       │
│ filename          │ Original upload filename          │
│ original_path     │ Path to uploaded file             │
│ synthetic_path    │ Path to generated output          │
│ status            │ PENDING → PROCESSING → COMPLETED  │
│ progress          │ 0.0 to 1.0                       │
│ message           │ Human-readable status             │
│ error             │ Error details (if failed)         │
│ rows_original     │ Input row count                   │
│ columns           │ Input column count                │
│ rows_generated    │ Output row count                  │
│ model_type        │ Selected model name               │
│ config_json       │ Full generation config (JSON)     │
│ privacy_enabled   │ DP enabled flag                   │
│ privacy_epsilon   │ DP epsilon                        │
│ quality_score     │ Computed quality (0-1)            │
│ privacy_score     │ Computed privacy (0-1)            │
│ correlation_score │ Correlation preservation          │
│ created_at        │ UTC timestamp                     │
│ updated_at        │ UTC timestamp (auto)              │
│ completed_at      │ UTC timestamp                     │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────┐   ┌────────────────────────────┐
│          Preset              │   │          APIKey             │
├─────────────────────────────┤   ├────────────────────────────┤
│ id (PK, auto)               │   │ id (PK, auto)              │
│ name (unique)               │   │ key_hash (unique, SHA-256) │
│ description                 │   │ name                       │
│ config_json                 │   │ created_at                 │
│ created_at                  │   │ last_used                  │
└─────────────────────────────┘   └────────────────────────────┘
```

**Database choice**: SQLite by default for zero-config local development. PostgreSQL is supported for production via the `DATABASE_URL` environment variable. The `connect_args={"check_same_thread": False}` is SQLite-specific and should be conditionally applied.

**File storage**: Uploaded files go to `uploads/` and generated outputs to `outputs/{job_id}/`. These directories are created at startup.

### Middleware

```
Request → RequestTracking → UploadSizeLimit → CORS → APIKeyAuth → Router
```

| Middleware | File | Purpose |
|-----------|------|---------|
| `RequestTrackingMiddleware` | `request_tracking.py` | Generates a UUID per request, stores it in a `ContextVar` for correlated logging |
| `UploadSizeLimitMiddleware` | `main.py` | Checks `Content-Length` header against `MAX_UPLOAD_SIZE` (default 100 MB), returns 413 if exceeded |
| `CORSMiddleware` | `main.py` (FastAPI built-in) | Configurable origin allowlist via `CORS_ORIGINS` env var |
| `verify_api_key` | `auth.py` | Dependency-based auth: if any API keys exist in DB, require valid `X-API-Key` header |

### Logging

**File**: `backend/app/utils/logger.py`

Centralized structured logging with:

- **Request ID correlation** — Every log line includes the request UUID via `ContextVar`
- **Colored console output** — ANSI colors by log level for development
- **JSON format option** — Structured JSON logs for production/log aggregation
- **File logging** — Optional `logs/dataforge.log` file output
- **Third-party noise reduction** — `uvicorn.access` and `watchfiles` set to WARNING

Format: `2024-01-15 10:30:45 | INFO | [req-uuid] | module:function:line | message`

All services use `from app.utils.logger import get_logger` instead of `print()`.

---

## Frontend Architecture

### Application Structure

```
src/
├── App.tsx              # Root: Router + ErrorBoundary wrapper
├── main.tsx             # React DOM render entry point
├── index.css            # Tailwind directives
├── pages/               # Route-level components (23 files)
├── components/          # Reusable UI components (27 files)
├── services/api.ts      # Centralized API client
├── types/index.ts       # TypeScript type definitions
├── lib/utils.ts         # Utility functions
└── utils/reportGenerator.ts  # PDF report export
```

### Routing

React Router v7 with 25 routes, all wrapped in an `ErrorBoundary` component:

| Path | Page | Feature |
|------|------|---------|
| `/` | Upload | File upload & data type selection |
| `/configure/:jobId` | Configure | Model & parameter configuration |
| `/generate/:jobId` | Generate | Real-time generation progress |
| `/results/:jobId` | Results | Validation results, charts, download |
| `/configure-pdf/:jobId` | ConfigurePDF | PDF generation config |
| `/pdf-results/:jobId` | PDFResults | Generated PDF list & download |
| `/configure-api-test/:jobId` | ConfigureAPITest | API test config |
| `/api-test-results/:jobId` | APITestResults | Test suite results |
| `/configure-db-test/:jobId` | ConfigureDBTest | DB test config |
| `/db-test-results/:jobId` | DBTestResults | Test data results |
| `/configure-multi/:jobId` | ConfigureMultiTable | Relationship builder |
| `/configure-pii/:jobId` | ConfigurePII | PII masking config |
| `/pii-results/:jobId` | PIIResults | Masked data results |
| `/configure-logs/:jobId` | ConfigureLogs | Log synthesis config |
| `/log-results/:jobId` | LogResults | Synthetic log results |
| `/configure-cdc/:jobId` | ConfigureCDC | CDC config |
| `/cdc-results/:jobId` | CDCResults | CDC event results |
| `/configure-graph/:jobId` | ConfigureGraph | Graph synthesis config |
| `/graph-results/:jobId` | GraphResults | Graph visualization |
| `/history` | JobHistory | Job list & management |
| `/compare` | Compare | Dataset comparison |
| `/drift` | DriftDetection | Drift analysis |
| `/settings` | Settings | API keys & preferences |
| `*` | 404 | Not found page |

### API Client

**File**: `frontend/src/services/api.ts`

A centralized Axios-based client with:

- **Base URL configuration** via `VITE_API_BASE_URL` environment variable
- **Fully typed** — all functions return specific TypeScript types (no `any`)
- **Consistent patterns** — upload functions use `FormData`, generate functions use JSON
- **Download helpers** — URL builders for file download endpoints

```typescript
// Example: fully typed API function
export const generatePDFs = async (
  jobId: string,
  config: Record<string, unknown>
): Promise<GenerateResponse> => {
  const response = await api.post('/generate-pdfs', { job_id: jobId, config });
  return response.data;
};
```

### Component Hierarchy

```
App (ErrorBoundary)
├── Upload
│   ├── DataTypeSelector        # Structured/PDF/API/DB/PII/Log/CDC/Graph tabs
│   ├── react-dropzone          # File drag & drop
│   ├── PDFUploader             # Multi-file PDF upload
│   ├── APISpecUploader         # OpenAPI spec upload
│   ├── DBSchemaUploader        # SQL schema upload
│   ├── LogUploader             # Log file upload
│   └── GraphUploader           # Graph file upload
├── Configure
│   ├── GPTConfigSection        # Shared GPT model/key config
│   ├── TimeGANConfig           # Time-series specific settings
│   ├── ConditionBuilder        # Column constraint editor
│   └── RelationshipBuilder     # FK relationship visual editor
├── Generate
│   ├── LivePreview             # Real-time SSE data preview
│   └── Progress indicators
├── Results
│   ├── CorrelationHeatmap      # Pearson/Spearman heatmaps
│   ├── NovelQualityMetrics     # ML efficacy charts
│   ├── TimeSeriesMetrics       # LSTM/ARIMA results
│   ├── PrivacyOverview         # Privacy score breakdown
│   ├── DataPreviewTable        # Paginated data table
│   └── Recharts                # Distribution charts
└── Shared
    ├── ErrorBanner             # Dismissible error display
    ├── Button                  # Styled button component
    └── Card                    # Content card wrapper
```

**Error handling pattern**: All pages use `catch (err: unknown)` with `getApiErrorMessage(err)` from `lib/utils.ts`, displaying errors via the `ErrorBanner` component instead of `alert()`.

---

## Data Flow

### Structured Data Generation Flow

```
User uploads CSV
       │
       ▼
POST /api/upload
       │  → Save file to uploads/{job_id}.csv
       │  → Read file, extract metadata (rows, columns, types)
       │  → Create Job record (status: PENDING)
       │  → Return job_id + column info
       │
       ▼
User configures model & parameters
       │
       ▼
POST /api/generate
       │  → Validate job exists and is PENDING
       │  → Update job status to PROCESSING
       │  → Launch background task: generator.generate()
       │       │
       │       ├── Load CSV with pandas
       │       ├── Apply column-level config (types, constraints)
       │       ├── Select/instantiate model (CTGAN, TVAE, etc.)
       │       ├── Train model (update job.progress periodically)
       │       ├── Generate N synthetic rows
       │       ├── Apply post-processing (rounding, clipping)
       │       ├── Apply SMOTE augmentation (if configured)
       │       ├── Apply differential privacy (if configured)
       │       ├── Save to outputs/{job_id}/synthetic.csv
       │       ├── Run validator.validate()
       │       │     ├── Statistical similarity per column
       │       │     ├── Correlation matrix comparison
       │       │     ├── Privacy metrics
       │       │     └── ML efficacy (optional)
       │       ├── Save validation results to outputs/{job_id}/
       │       └── Update job status to COMPLETED
       │
       ▼
GET /api/status/{job_id}  (polling)
       │  → Return status, progress, message
       │
       ▼
GET /api/validation/{job_id}
       │  → Return quality scores, charts, column metrics
       │
       ▼
GET /api/download/{job_id}
       │  → Stream synthetic.csv as file response
```

### GPT-Powered Feature Flow

```
User uploads file (PDF / OpenAPI spec / SQL schema)
       │
       ▼
POST /api/upload-{type}
       │  → Save file, create Job record
       │  → Parse/analyze uploaded content
       │  → Return job_id + extracted metadata
       │
       ▼
POST /api/generate-{type}
       │  → Launch background task
       │       │
       │       ├── Initialize LLM client (llm_client.py)
       │       │     └── OpenAI API with retry + exponential backoff
       │       ├── Construct prompt with extracted content
       │       ├── Call GPT API (multiple calls for large inputs)
       │       ├── Parse and validate LLM response
       │       ├── Generate output files
       │       └── Save results to outputs/{job_id}/
       │
       ▼
GET /api/{type}-results/{job_id}
GET /api/download-{type}/{job_id}
```

### Background Task Pattern

All long-running operations (generation, synthesis) use FastAPI's `BackgroundTasks`:

```python
@router.post("/generate")
async def generate(request: GenerateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == request.job_id).first()
    job.status = JobStatusEnum.PROCESSING
    db.commit()

    background_tasks.add_task(
        generate_background,           # Function to run
        job_id=request.job_id,
        original_path=job.original_path,
        config=request.config.dict()
    )

    return {"job_id": request.job_id, "status": "processing"}
```

The frontend polls `GET /status/{job_id}` to track progress, or uses SSE via `GET /stream-generate/{job_id}` for real-time updates.

---

## Database Schema

### Entity Relationship

```
┌──────────┐
│   Job    │  (Main entity — one per upload/generation)
├──────────┤
│ id (PK)  │──── Referenced by file paths: uploads/{id}.csv, outputs/{id}/
│ status   │──── PENDING → PROCESSING → COMPLETED | FAILED
│ ...      │
└──────────┘

┌──────────┐
│  Preset  │  (Standalone — no FK to Job)
├──────────┤
│ id (PK)  │
│ name     │──── Unique constraint
│ config   │──── JSON blob of GenerationConfig
└──────────┘

┌──────────┐
│  APIKey  │  (Standalone — no FK to Job)
├──────────┤
│ id (PK)  │
│ key_hash │──── SHA-256 of the raw key (raw key never stored)
│ name     │
└──────────┘
```

### Job Lifecycle

```
PENDING ──── POST /generate ────► PROCESSING ────► COMPLETED
                                       │               │
                                       │          (validation results
                                       │           computed & stored)
                                       │
                                       └────► FAILED
                                              (error message stored)
```

---

## Authentication

DataForge uses an **opt-in API key model**:

```
┌────────────────────────────────────────────┐
│           Authentication Flow              │
│                                            │
│  1. Check: any APIKey records in DB?       │
│     │                                      │
│     ├── NO  → Allow request (open mode)    │
│     │                                      │
│     └── YES → Check X-API-Key header       │
│          │                                 │
│          ├── Missing → 401 Unauthorized    │
│          ├── Invalid → 403 Forbidden       │
│          └── Valid   → Allow + update      │
│                        last_used timestamp │
└────────────────────────────────────────────┘
```

- Keys are created via `POST /api/api-keys` (returns raw key once, never again)
- Keys are stored as SHA-256 hashes (raw key is not persisted)
- Applied globally via `dependencies=[Depends(verify_api_key)]` on all routers
- The `/health` and `/` root endpoints are outside the router prefix and not protected

---

## Synthesis Engine

### Model Selection

The `generator.py` service is the central orchestrator:

```
Input: model_type from config
  │
  ├── "ctgan"              → SDV CTGANSynthesizer
  ├── "tvae"               → SDV TVAESynthesizer
  ├── "gaussian_copula"    → SDV GaussianCopulaSynthesizer
  ├── "copula_gan"         → SDV CopulaGANSynthesizer (fallback: CTGAN)
  ├── "timegan"            → Custom PyTorch TimeGAN
  ├── "tabddpm"            → Synthcity TabDDPM (fallback: Gaussian Copula)
  ├── "bayesian_network"   → Synthcity BayesianNetwork (fallback: Gaussian Copula)
  ├── "ctab_gan_plus"      → Synthcity CTAB-GAN+ (fallback: CTGAN)
  ├── "dp_ctgan"           → SmartNoise DP-CTGAN (fallback: CTGAN + manual DP)
  ├── "realtabformer"      → REaLTabFormer GPT-2 (fallback: Gaussian Copula)
  ├── "dgan"               → Gretel DGAN (fallback: TimeGAN)
  ├── "llm_row_generator"  → OpenAI API row generation
  └── "auto"               → Recommendation engine selects based on data characteristics
```

### Model Adapters

Each external library has a thin adapter that provides:

1. **Lazy import** — `try: import library except ImportError: raise/fallback`
2. **Normalized interface** — `train(df, config) → model` and `generate(model, n) → df`
3. **Graceful fallback** — If library unavailable, fall back to a simpler model with a warning

### Validation Pipeline

After generation completes, the validator runs automatically:

```
Synthetic DataFrame
       │
       ├── Per-Column Statistical Tests
       │     ├── Numeric: KS test, t-test, KL divergence, JSD
       │     └── Categorical: Chi-square, frequency comparison
       │
       ├── Correlation Preservation
       │     ├── Pearson correlation matrix (original vs synthetic)
       │     └── Spearman rank correlation matrix
       │
       ├── Privacy Metrics
       │     ├── Distance to Closest Record (DCR)
       │     ├── Re-identification risk
       │     └── DP guarantees (if enabled)
       │
       ├── Novel Quality Metrics (optional)
       │     ├── ML Efficacy (TRTR vs TSTR)
       │     ├── Feature importance preservation
       │     ├── Rare event coverage
       │     └── Boundary preservation
       │
       └── Time-Series Metrics (if applicable)
             ├── LSTM prediction comparison
             └── ARIMA prediction comparison
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Domain routers (16 files) vs. monolithic routes** | Single `routes.py` grew to 2,280 lines. Domain splitting improves navigation, ownership, and merge conflict avoidance. |
| **SQLite default, PostgreSQL optional** | Zero-config local development. Production deployments should use PostgreSQL via `DATABASE_URL`. |
| **Background tasks vs. Celery** | FastAPI's built-in `BackgroundTasks` avoids the operational complexity of a message broker. Trade-off: tasks are lost if the server restarts mid-generation. |
| **Lazy model imports** | ML libraries (PyTorch, SDV, Synthcity) are heavy. Lazy loading keeps startup fast and allows the app to run without optional dependencies. |
| **File-based output storage** | Simple and portable. Cloud deployments should mount persistent volumes (EFS, Azure Files, GCS). |
| **SSE for progress** | Server-Sent Events are simpler than WebSockets for one-directional progress updates. The frontend polls as a fallback. |
| **SHA-256 key hashing** | API keys are never stored in plaintext. SHA-256 is sufficient for this use case (keys are high-entropy random strings, not passwords). |
| **Typed API client (no `any`)** | All frontend API functions return specific TypeScript types, catching type mismatches at compile time. |
| **Error state over `alert()`** | UI errors are displayed as dismissible banners rather than blocking `alert()` dialogs, improving UX. |

---

## Security Considerations

| Area | Implementation |
|------|---------------|
| **API authentication** | Optional API key via `X-API-Key` header (SHA-256 hashed storage) |
| **Upload validation** | File extension allowlists per feature, size limit middleware |
| **CORS** | Configurable origin allowlist (not wildcard in production) |
| **SQL injection** | SQLAlchemy ORM with parameterized queries throughout |
| **Path traversal** | UUIDs for job IDs, no user-controlled path components |
| **Secret management** | `.env` files excluded from git, `.env.example` provided |
| **Error exposure** | Generic error messages in API responses; details logged server-side |
| **Dependency security** | Pinned minimum versions in requirements.txt |

**Recommendations for production:**
- Enable HTTPS via reverse proxy (Nginx, ALB, Cloud Run)
- Use a cloud secret manager for `OPENAI_API_KEY`
- Restrict or disable `/docs` and `/redoc` endpoints
- Set `CORS_ORIGINS` to exact production domains
- Enable rate limiting at the load balancer level

---

## Scalability & Limitations

### Current Limitations

| Area | Limitation | Mitigation |
|------|-----------|------------|
| **Concurrency** | Background tasks run in-process; a single task blocks one worker thread | Scale uvicorn workers (`--workers N`) |
| **Task persistence** | Background tasks are lost on server restart | For production, consider Celery + Redis |
| **File storage** | Local filesystem doesn't scale across instances | Use cloud object storage (S3, Azure Blob, GCS) |
| **Database** | SQLite doesn't support concurrent writes well | Use PostgreSQL for multi-worker deployments |
| **Memory** | Large datasets (>100K rows) with complex models (TabDDPM) may OOM | Set appropriate `MAX_UPLOAD_SIZE` and model-specific limits |

### Scaling Path

```
Local (current)                Production                    Enterprise
─────────────                  ──────────                    ──────────
SQLite                    →    PostgreSQL                →   PostgreSQL (replicas)
Local filesystem          →    Cloud storage (S3/GCS)   →   CDN + object storage
In-process background     →    Celery + Redis           →   Kubernetes Jobs
Single uvicorn            →    Gunicorn + N workers     →   Auto-scaling pods
                               Load balancer                 Multi-region
```

---

## Dependency Architecture

### Core Dependencies (always installed)

```
fastapi ─── uvicorn ─── pydantic
   │
   ├── sqlalchemy (ORM + DB)
   ├── pandas + numpy + scipy + scikit-learn (data processing)
   ├── faker (fake data generation)
   ├── networkx (graph processing)
   ├── statsmodels + pmdarima (time-series analysis)
   ├── PyPDF2 + reportlab (PDF read/write)
   ├── imbalanced-learn (SMOTE)
   └── sse-starlette (SSE streaming)
```

### Optional ML Dependencies (lazy-loaded)

```
torch ─── sdv (CTGAN, TVAE, Gaussian Copula, CopulaGAN)
  │
  ├── synthcity (TabDDPM, CTAB-GAN+, Bayesian Network)
  ├── realtabformer (GPT-2 tabular)
  ├── gretel-synthetics (DGAN)
  └── smartnoise-synth (DP-CTGAN)  ⚠️ Conflicts with synthcity on opacus
```

### Frontend Dependencies

```
react + react-dom + react-router-dom (core)
  │
  ├── axios (HTTP client)
  ├── recharts (charts/visualization)
  ├── lucide-react (icons)
  ├── react-dropzone (file upload)
  ├── react-markdown (markdown rendering)
  ├── tailwindcss + tailwind-merge + clsx (styling)
  ├── html2canvas + jspdf (PDF report export)
  └── typescript + vite (build tooling)
```
