# Loan Document Data Extraction System

A production-grade system for extracting structured borrower data from loan documents (PDF, DOCX, images) using AI-powered document processing.

## Features

- **Document Processing**: Parse PDF, DOCX, and scanned images using Docling with built-in OCR
- **AI Extraction**: Extract borrower information using Google Gemini 3.0 with dynamic model selection
- **Source Attribution**: Every extracted field traces back to the source document and page
- **Validation**: Automated format validation (SSN, phone, zip) with confidence scoring
- **Web Dashboard**: React-based UI for document upload and borrower management

## Architecture

The system follows a document processing pipeline architecture: documents are uploaded and parsed by Docling, then sent to Gemini for structured data extraction, validated and stored in PostgreSQL with full source attribution, served via FastAPI REST API, and displayed in a Next.js dashboard. See [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) for detailed architecture documentation.

```mermaid
flowchart LR
    Upload[Document Upload] --> Docling[Docling Parser]
    Docling --> Gemini[Gemini Extraction]
    Gemini --> Validate[Validation]
    Validate --> DB[(PostgreSQL)]
    DB --> API[REST API]
    API --> UI[Dashboard]
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | Async REST API |
| Frontend | Next.js 16 | React dashboard with App Router |
| Document Processing | Docling | PDF/DOCX/Image parsing with OCR |
| LLM | Google Gemini 3.0 | Data extraction |
| Database | PostgreSQL 16 | Relational storage |
| Storage | Google Cloud Storage | Document files |
| Deployment | Cloud Run | Serverless containers |
| Infrastructure | Terraform | Infrastructure as Code |

## Prerequisites

- Python 3.10+
- Node.js 20+
- Docker and Docker Compose
- Google Cloud SDK (for deployment)
- Gemini API key (from [Google AI Studio](https://aistudio.google.com/))

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd loan
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including dev tools)
pip install -e ".[dev]"
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

### 4. Environment Configuration

Create `.env` files for local development:

**backend/.env:**
```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/loan_extraction
GCS_BUCKET_NAME=  # Optional for local dev (mock GCS client used when not set)
GEMINI_API_KEY=your-api-key-here
```

**frontend/.env.local:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running Locally

### Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d
```

This starts:
- PostgreSQL 16 on port 5432 (database: `loan_extraction`, user: `postgres`, password: `postgres`)
- Redis 7 on port 6379

### Run Database Migrations

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

### Start Backend Server

```bash
cd backend
source venv/bin/activate
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Start Frontend Development Server

```bash
cd frontend
npm run dev
```

The dashboard will be available at http://localhost:3000

## Development

### Running Tests

```bash
cd backend
source venv/bin/activate

# Run all tests with coverage
pytest

# Run only unit tests
pytest tests/unit

# Run specific test file
pytest tests/extraction/test_llm_client.py

# Run with verbose output and HTML coverage report
pytest -v --cov-report=html
```

### Code Quality

```bash
cd backend
source venv/bin/activate

# Type checking (strict mode)
mypy src/

# Linting
ruff check src/

# Format code
ruff format src/
```

### Frontend Development

```bash
cd frontend

# Type checking
npx tsc --noEmit

# Linting
npm run lint

# Build for production
npm run build
```

## Project Structure

```
loan/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI routes and endpoints
│   │   ├── extraction/    # LLM extraction and validation logic
│   │   ├── ingestion/     # Document processing with Docling
│   │   ├── models/        # Pydantic schemas and SQLAlchemy models
│   │   └── storage/       # Database repositories and GCS client
│   ├── tests/             # pytest unit and integration tests
│   └── alembic/           # Database migrations
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js pages and routes
│   │   ├── components/    # React components (shadcn/ui)
│   │   └── lib/           # API client and utilities
│   └── public/            # Static assets
├── infrastructure/
│   ├── terraform/         # IaC configuration for GCP
│   └── scripts/           # Deployment automation scripts
├── docs/                  # Documentation
├── docker-compose.yml     # Local development infrastructure
└── README.md              # This file
```

## Deployment

### Prerequisites

1. Google Cloud project with billing enabled
2. gcloud CLI installed and authenticated (`gcloud auth login`)
3. Docker installed for building images

### Initialize GCP Resources

```bash
cd infrastructure/scripts
chmod +x setup-gcp.sh deploy.sh

# Initialize GCP project (enables APIs, creates Artifact Registry, Terraform state bucket)
./setup-gcp.sh YOUR_PROJECT_ID us-central1
```

This script:
- Enables required GCP APIs (Cloud Run, Cloud SQL, Secret Manager, etc.)
- Creates Artifact Registry repository for Docker images
- Configures Docker authentication
- Creates Terraform state bucket with versioning

### Configure Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars from example
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values:
#   project_id = "your-project-id"
#   db_password = "secure-password"
#   gemini_api_key = "your-api-key"
```

### Deploy Services

```bash
cd infrastructure/scripts

# Set required environment variable
export PROJECT_ID=your-project-id

# Deploy (builds images, pushes to registry, applies Terraform)
./deploy.sh
```

The deploy script:
1. Builds backend Docker image and pushes to Artifact Registry
2. Builds frontend Docker image and pushes to Artifact Registry
3. Applies Terraform configuration to create/update Cloud Run services
4. Outputs the service URLs

### Environment Variables (Production)

These are managed automatically by Terraform via Secret Manager:
- `DATABASE_URL`: Cloud SQL connection string (private IP)
- `GEMINI_API_KEY`: Gemini API key
- `GCS_BUCKET_NAME`: Document storage bucket name

## API Usage

### Upload a Document

```bash
curl -X POST http://localhost:8000/api/documents \
  -F "file=@/path/to/document.pdf"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "completed",
  "page_count": 5
}
```

### Get Document Status

```bash
curl http://localhost:8000/api/documents/{document_id}/status
```

Response:
```json
{
  "status": "completed",
  "page_count": 5,
  "error_message": null
}
```

### List Documents

```bash
curl "http://localhost:8000/api/documents?page=1&page_size=10"
```

### List Borrowers

```bash
curl "http://localhost:8000/api/borrowers?page=1&page_size=10"
```

Response:
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

### Get Borrower Details

```bash
curl http://localhost:8000/api/borrowers/{borrower_id}
```

Response includes:
- Borrower information (name, SSN, address, phone)
- Income records with amounts and periods
- Account numbers
- Source references (document ID, page number, text snippet)

### Search Borrowers

```bash
# Search by name
curl "http://localhost:8000/api/borrowers/search?name=John"

# Search by account number
curl "http://localhost:8000/api/borrowers/search?account_number=12345"
```

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy"
}
```

## Documentation

- [System Design](docs/SYSTEM_DESIGN.md) - Architecture, pipeline, scaling analysis
- [Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md) - ADRs for technology choices

## License

MIT
