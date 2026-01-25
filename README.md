```
    __                           ____                                          __
   / /   ____  ____ _____       / __ \____  _______  ______ ___  ___  ____  / /_
  / /   / __ \/ __ `/ __ \     / / / / __ \/ ___/ / / / __ `__ \/ _ \/ __ \/ __/
 / /___/ /_/ / /_/ / / / /    / /_/ / /_/ / /__/ /_/ / / / / / /  __/ / / / /_
/_____/\____/\__,_/_/ /_/    /_____/\____/\___/\__,_/_/ /_/ /_/\___/_/ /_/\__/

    ____        __           ______     __                  __  _
   / __ \____ _/ /_____ _   / ____/  __/ /__________ ______/ /_(_)___  ____
  / / / / __ `/ __/ __ `/  / __/ | |/_/ __/ ___/ __ `/ ___/ __/ / __ \/ __ \
 / /_/ / /_/ / /_/ /_/ /  / /____>  </ /_/ /  / /_/ / /__/ /_/ / /_/ / / / /
/_____/\__,_/\__/\__,_/  /_____/_/|_|\__/_/   \__,_/\___/\__/_/\____/_/ /_/

                    _____ __  _____ __
                   / ___// / / /   / /______ _
                   \__ \/ / / / /| / __/ __ `/
                  ___/ / /_/ / ___ / /_/ /_/ /
                 /____/\__, /_/  |_\__/\__,_/
                      /____/
                           _____________
                          |  _________  |
                          | |   PDF   | |  📄 → 🤖 → 💾
                          | |  .docx  | |
                          | |   📷    | |
                          | |_________| |
                          |_____________|
                               UPLOAD
```

# 📋 Loan Document Data Extraction System

> 🤖 **AI-Powered** | 📄 **Multi-Format** | 🔍 **Traceable** | ⚡ **Production-Ready**

A production-grade system for extracting structured borrower data from loan documents (PDF, DOCX, images) using AI-powered document processing with **complete source traceability**.

---

## 🌟 Highlights

| | |
|---|---|
| 🧪 **490 Tests** | ✅ 86.98% Coverage |
| 📝 **95,818 LOC** | 🚀 v2.0 Shipped 2026-01-25 |
| 🔒 **mypy Strict** | 🐍 Python + 📘 TypeScript |

---

## ✨ Features

### 🎯 Core Capabilities

- 📄 **Document Processing** — Parse PDF, DOCX, and scanned images with intelligent layout understanding
- 🤖 **AI Extraction** — Extract borrower information using Google Gemini 3.0 with dynamic model selection
- 🔍 **Source Attribution** — Every extracted field traces back to source document and page
- ✅ **Validation** — Automated format validation (SSN, phone, zip) with confidence scoring
- 🖥️ **Web Dashboard** — React-based UI for document upload and borrower management

### 🆕 v2.0 Dual Pipeline Architecture

- ⚡ **Docling Pipeline** — Fast page-level attribution, built-in OCR
- 🎯 **LangExtract Pipeline** — Precise character-level attribution with few-shot examples
- 🔄 **Auto-Selection** — Intelligent routing or manual method selection via API
- 🖼️ **LightOnOCR GPU** — High-quality OCR for scanned documents (scale-to-zero enabled)
- 🔁 **Circuit Breaker** — Automatic fallback from LangExtract → Docling on errors

---

## 🏗️ Architecture

The system follows a **document processing pipeline architecture**:

```mermaid
flowchart LR
    subgraph Upload["📤 Upload"]
        A[Document Upload]
    end

    subgraph OCR["🖼️ OCR Layer"]
        B{Scanned?}
        C[LightOnOCR GPU]
        D[Docling OCR]
    end

    subgraph Extract["🤖 Extraction"]
        E{Method}
        F[Docling + Gemini]
        G[LangExtract + Gemini]
    end

    subgraph Store["💾 Storage"]
        H[Validation]
        I[(PostgreSQL)]
    end

    subgraph Serve["🌐 API"]
        J[FastAPI REST]
        K[Next.js Dashboard]
    end

    A --> B
    B -->|Yes| C
    B -->|No| E
    C --> E
    D -.->|Fallback| E
    E -->|docling| F
    E -->|langextract| G
    F --> H
    G --> H
    H --> I
    I --> J
    J --> K
```

📚 See [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for detailed architecture documentation.

---

## 🛠️ Tech Stack

| Component | Technology | Purpose | Emoji |
|-----------|------------|---------|-------|
| 🐍 Backend | FastAPI | Async REST API with OpenAPI docs | ⚡ |
| 🖥️ Frontend | Next.js 14 | React dashboard with App Router | ⚛️ |
| 📄 Doc Processing | Docling | PDF/DOCX/Image parsing with OCR | 📋 |
| 🎯 Extraction | LangExtract | Character-level attribution extraction | 🔍 |
| 🤖 LLM | Google Gemini 3.0 | Flash (standard) / Pro (complex) | 💡 |
| 🖼️ OCR | LightOnOCR | GPU-accelerated scanned doc OCR | 🚀 |
| 💾 Database | PostgreSQL 16 | Relational storage with async driver | 🗄️ |
| ☁️ Storage | Cloud Storage | Document file storage | 📦 |
| 🚀 Deployment | Cloud Run | Serverless containers (incl. GPU) | 🐳 |
| 🔧 CI/CD | CloudBuild | GitHub-triggered deployments | 🔄 |
| 🏗️ Infrastructure | gcloud CLI | Infrastructure provisioning scripts | 📝 |

---

## 📊 Project Metrics

```
┌─────────────────────────────────────────────────────────────┐
│                    📈 v2.0 Statistics                       │
├─────────────────────────────────────────────────────────────┤
│  🧪 Tests:        490 passing                               │
│  📊 Coverage:     86.98%                                    │
│  📝 Lines:        95,818 LOC                                │
│  ✅ Requirements: 294/294 (v1.0: 222, v2.0: 72)             │
│  📦 Phases:       18 complete                               │
│  📋 Plans:        64 executed                               │
│  🔒 Type Safety:  mypy strict (0 errors)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| 🐍 Python | 3.10+ | `python --version` |
| 📦 Node.js | 20+ | `node --version` |
| 🐳 Docker | Latest | `docker --version` |
| ☁️ gcloud CLI | Latest | `gcloud --version` |
| 🔑 Gemini API Key | — | [Get from AI Studio](https://aistudio.google.com/) |

---

## 🚀 Setup

### 1️⃣ Clone the Repository

```bash
git clone <repository-url>
cd loan
```

### 2️⃣ Backend Setup

```bash
cd backend

# 🐍 Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 📦 Install dependencies (including dev tools)
pip install -e ".[dev]"
```

### 3️⃣ Frontend Setup

```bash
cd frontend

# 📦 Install dependencies
npm install
```

### 4️⃣ Environment Configuration

Create `.env` files for local development:

**📝 backend/.env:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/loan_extraction
GCS_BUCKET_NAME=  # Optional for local dev (mock GCS client used when not set)
GEMINI_API_KEY=your-api-key-here
GOOGLE_API_KEY=your-api-key-here  # For LangExtract (same key)
```

**📝 frontend/.env.local:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🏃 Running Locally

### 🐳 Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d
```

This starts:
- 🗄️ PostgreSQL 16 on port 5432 (database: `loan_extraction`, user: `postgres`, password: `postgres`)
- 📮 Redis 7 on port 6379

### 📊 Run Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### 🖥️ Start Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

🌐 The API will be available at:
- 📡 API: http://localhost:8000
- 📚 Docs: http://localhost:8000/docs
- ❤️ Health: http://localhost:8000/health

### 💻 Start Frontend Development Server

```bash
cd frontend
npm run dev
```

🖥️ The dashboard will be available at http://localhost:3000

---

## 🧪 Development

### 🔬 Running Tests

```bash
cd backend
source venv/bin/activate

# 🧪 Run all tests with coverage
pytest

# 📁 Run only unit tests
pytest tests/unit

# 📄 Run specific test file
pytest tests/extraction/test_llm_client.py

# 📊 Run with verbose output and HTML coverage report
pytest -v --cov-report=html
```

### ✅ Code Quality

```bash
cd backend
source venv/bin/activate

# 🔒 Type checking (strict mode)
mypy src/

# 🔍 Linting
ruff check src/

# ✨ Format code
ruff format src/
```

### 💻 Frontend Development

```bash
cd frontend

# 🔒 Type checking
npx tsc --noEmit

# 🔍 Linting
npm run lint

# 📦 Build for production
npm run build
```

---

## 📁 Project Structure

```
loan/
├── 🐍 backend/
│   ├── src/
│   │   ├── api/           # 🌐 FastAPI routes and endpoints
│   │   ├── extraction/    # 🤖 LLM extraction and validation logic
│   │   ├── ingestion/     # 📄 Document processing with Docling
│   │   ├── ocr/           # 🖼️ LightOnOCR client and router
│   │   ├── models/        # 📋 Pydantic schemas and SQLAlchemy models
│   │   └── storage/       # 💾 Database repositories and GCS client
│   ├── tests/             # 🧪 pytest unit and integration tests
│   └── alembic/           # 📊 Database migrations
├── 💻 frontend/
│   ├── src/
│   │   ├── app/           # 📱 Next.js pages and routes
│   │   ├── components/    # 🎨 React components (shadcn/ui)
│   │   └── lib/           # 🔧 API client and utilities
│   └── public/            # 🖼️ Static assets
├── 🏗️ infrastructure/
│   ├── cloudbuild/        # 🔧 CloudBuild YAML configs
│   └── scripts/           # 📝 Deployment automation scripts
├── 📚 docs/               # 📖 Documentation
├── 🐳 docker-compose.yml  # Local development infrastructure
└── 📋 README.md           # This file
```

---

## ☁️ Deployment

### 📋 Prerequisites

1. ☁️ Google Cloud project with billing enabled
2. 🔧 gcloud CLI installed and authenticated (`gcloud auth login`)
3. 🐳 Docker installed for building images

### 🏗️ Initialize GCP Resources

```bash
cd infrastructure/scripts
chmod +x setup-gcp.sh provision-infra.sh

# 🚀 Initialize GCP project (enables APIs, creates resources)
./setup-gcp.sh YOUR_PROJECT_ID us-central1

# 🏗️ Provision infrastructure
./provision-infra.sh YOUR_PROJECT_ID us-central1
```

### 🔧 Set Up CloudBuild Triggers

```bash
cd infrastructure/scripts

# 🔗 Connect GitHub and create triggers
./setup-github-triggers.sh YOUR_PROJECT_ID us-central1 your-github-repo
```

### 🚀 Deploy Services

Services deploy automatically on push to main branch via CloudBuild triggers:

- 🐍 **Backend**: `backend-cloudbuild.yaml`
- 💻 **Frontend**: `frontend-cloudbuild.yaml`
- 🖼️ **GPU Service**: `gpu-cloudbuild.yaml`

📚 See [docs/cloudbuild-deployment-guide.md](docs/cloudbuild-deployment-guide.md) for detailed deployment instructions.

### 🔑 Environment Variables (Production)

Managed automatically via Secret Manager:
- 🔗 `DATABASE_URL`: Cloud SQL connection string (private IP)
- 🔑 `GEMINI_API_KEY`: Gemini API key
- 📦 `GCS_BUCKET_NAME`: Document storage bucket name

---

## 📡 API Usage

### 📤 Upload a Document

```bash
# 📄 Default (Docling extraction)
curl -X POST http://localhost:8000/api/documents \
  -F "file=@/path/to/document.pdf"

# 🎯 With LangExtract (character-level attribution)
curl -X POST "http://localhost:8000/api/documents?method=langextract" \
  -F "file=@/path/to/document.pdf"

# 🖼️ Force OCR for scanned documents
curl -X POST "http://localhost:8000/api/documents?method=docling&ocr=force" \
  -F "file=@/path/to/scanned.pdf"
```

**📋 Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "completed",
  "page_count": 5,
  "extraction_method": "langextract",
  "ocr_processed": false
}
```

### 🔍 Extraction Method Options

| Parameter | Options | Description |
|-----------|---------|-------------|
| `method` | `docling` (default), `langextract`, `auto` | 🤖 Extraction pipeline to use |
| `ocr` | `auto` (default), `force`, `skip` | 🖼️ OCR behavior for scanned docs |

📚 See [docs/api/extraction-method-guide.md](docs/api/extraction-method-guide.md) for detailed API guide.

### 📊 Get Document Status

```bash
curl http://localhost:8000/api/documents/{document_id}/status
```

**📋 Response:**
```json
{
  "status": "completed",
  "page_count": 5,
  "extraction_method": "docling",
  "ocr_processed": true,
  "error_message": null
}
```

### 📋 List Documents

```bash
curl "http://localhost:8000/api/documents?page=1&page_size=10"
```

### 👥 List Borrowers

```bash
curl "http://localhost:8000/api/borrowers?page=1&page_size=10"
```

**📋 Response:**
```json
{
  "borrowers": [
    {
      "id": "uuid",
      "name": "John Smith",
      "ssn_last_four": "1234",
      "income_count": 3
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10
}
```

### 👤 Get Borrower Details

```bash
curl http://localhost:8000/api/borrowers/{borrower_id}
```

**📋 Response includes:**
- 👤 Borrower information (name, SSN, address, phone)
- 💰 Income records with amounts and periods
- 🔢 Account numbers
- 📄 Source references (document ID, page number, text snippet)
- 🔍 Character offsets (when using LangExtract)

### 🔎 Search Borrowers

```bash
# 👤 Search by name
curl "http://localhost:8000/api/borrowers/search?name=John"

# 🔢 Search by account number
curl "http://localhost:8000/api/borrowers/search?account_number=12345"
```

### ❤️ Health Check

```bash
curl http://localhost:8000/health
```

**📋 Response:**
```json
{
  "status": "healthy"
}
```

---

## 📚 Documentation

### 🏗️ Architecture & Design

| Document | Description |
|----------|-------------|
| 📐 [System Design](docs/SYSTEM_DESIGN.md) | Architecture, pipeline, scaling analysis |
| 📝 [Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md) | ADRs for technology choices |

### 📖 Guides

| Guide | Description |
|-------|-------------|
| 🤖 [Extraction Method Guide](docs/api/extraction-method-guide.md) | API parameters and method selection |
| 📝 [Few-Shot Examples](docs/guides/few-shot-examples.md) | Creating extraction schema examples |
| 💰 [GPU Service Cost](docs/guides/gpu-service-cost.md) | Cost management strategies |
| 🖼️ [LightOnOCR Deployment](docs/guides/lightonocr-deployment.md) | GPU service deployment |
| 🚀 [CloudBuild Deployment](docs/cloudbuild-deployment-guide.md) | CI/CD deployment guide |

### 🔄 Migration & Operations

| Document | Description |
|----------|-------------|
| 🔄 [Terraform Migration](docs/migration/terraform-migration.md) | Terraform to CloudBuild migration |
| 📋 [Terraform Inventory](docs/terraform-to-gcloud-inventory.md) | gcloud CLI equivalents |

---

## 🆕 v2.0 Release Notes (2026-01-25)

### 🎯 Dual Extraction Pipelines

**Docling Pipeline** (default)
- ⚡ Fast page-level attribution
- 📄 Built-in OCR for scanned documents
- 🔧 Mature, battle-tested processing

**LangExtract Pipeline** (new)
- 🎯 Character-level source attribution (char_start/char_end)
- 📝 Few-shot example-based extraction schema
- 🔍 Precise text grounding for verification

### 🖼️ LightOnOCR GPU Service

- 🚀 High-quality OCR powered by LightOn VLM
- 💰 Scale-to-zero ($0 baseline vs $485/month always-on)
- 🔁 Circuit breaker fallback to Docling OCR
- ⚡ L4 GPU for fast processing

### 🔧 CloudBuild CI/CD

- 🔗 GitHub-triggered deployments
- 📦 Separate configs for backend, frontend, GPU
- 🔄 Replaces Terraform for application deployments
- 🏗️ Infrastructure via gcloud CLI scripts

### 📊 Quality Improvements

- 🧪 490 tests (up from 283 in v1.0)
- 📊 86.98% coverage (threshold: 80%)
- 🔒 mypy strict compliance (0 errors)

---

## 📜 License

MIT

---

<div align="center">

```
 _____ _                 _           __             _   _     _
|_   _| |__   __ _ _ __ | | _____   / _| ___  _ __| | | |___(_)_ __   __ _
  | | | '_ \ / _` | '_ \| |/ / __| | |_ / _ \| '__| | | / __| | '_ \ / _` |
  | | | | | | (_| | | | |   <\__ \ |  _| (_) | |  | |_| \__ \ | | | | (_| |
  |_| |_| |_|\__,_|_| |_|_|\_\___/ |_|  \___/|_|   \___/|___/_|_| |_|\__, |
                                                                     |___/
```

**Built with** 💻 **FastAPI** + ⚛️ **Next.js** + 🤖 **Gemini** + ☁️ **GCP**

🌟 Star this repo if you found it helpful!

</div>
