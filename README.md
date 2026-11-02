# Enterprise Hybrid RAG

A secure, multi-tenant Retrieval-Augmented Generation (RAG) application combining hybrid search, semantic retrieval, reranking, and LLM-powered responses.

## Overview

Enterprise Hybrid RAG is an AI-powered document question-answering system designed to retrieve relevant information from uploaded documents and generate context-aware responses.

The application combines vector search and keyword-based retrieval to improve search relevance. It also implements organization-level tenant isolation, JWT authentication, and role-based access control (RBAC).

## Key Features

- **Hybrid Retrieval:** Combines dense vector search and BM25 keyword search.
- **Reciprocal Rank Fusion (RRF):** Combines results from multiple retrieval methods.
- **Cross-Encoder Reranking:** Reorders retrieved documents based on relevance.
- **Multi-Tenant Architecture:** Separates document access across organizations.
- **JWT Authentication:** Secures API endpoints using access tokens.
- **Role-Based Access Control:** Supports Owner, Admin, Member, and Viewer roles.
- **Document Ingestion:** Supports PDF, DOCX, and TXT uploads.
- **LLM-Powered Answers:** Uses Groq-hosted language models to generate responses.
- **Vector Storage:** Stores document embeddings in Qdrant.
- **Relational Database:** Uses PostgreSQL for users, organizations, documents, and ingestion metadata.
- **Automated Testing:** Includes tests for authentication, permissions, ingestion, retrieval, and tenant isolation.

## Architecture

```text
                 User
                  |
                  v
          Streamlit Frontend
                  |
                  v
             FastAPI API
                  |
          JWT Authentication
                  |
          RBAC / Tenant Check
                  |
          +-------+--------+
          |                |
          v                v
    Document Upload    User Query
          |                |
          v                v
    Ingestion Pipeline  Hybrid Retrieval
          |                |
          v                v
    Text Chunking       Vector Search
          |             + BM25 Search
          v                |
    Embedding Model        v
          |           Reciprocal Rank
          v             Fusion
        Qdrant               |
                             v
                       Cross-Encoder
                         Reranking
                             |
                             v
                         Groq LLM
                             |
                             v
                      Final Response
```

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Programming Language | Python |
| Relational Database | PostgreSQL |
| Vector Database | Qdrant |
| Embedding Model | BAAI/bge-small-en-v1.5 |
| Keyword Retrieval | BM25Plus |
| Hybrid Ranking | Reciprocal Rank Fusion |
| Reranking | Cross-Encoder |
| LLM Provider | Groq |
| Authentication | JWT |
| Password Hashing | Argon2 |
| API Validation | Pydantic |
| Testing | Pytest |

## Project Structure

```text
enterprise-hybrid-rag/
│
├── app.py
│
├── backend/
│   ├── main.py
│   ├── api/
│   │   ├── auth_routes.py
│   │   └── routes.py
│   └── auth/
│       ├── bootstrap.py
│       ├── dependencies.py
│       ├── permissions.py
│       ├── security.py
│       └── service.py
│
├── core/
│   ├── embeddings.py
│   └── vector_store.py
│
├── database/
│   ├── connection.py
│   ├── schema.sql
│   ├── document_service.py
│   └── migrations/
│
├── ingestion/
│   ├── pipeline.py
│   ├── chunking.py
│   └── loaders.py
│
├── retrieval/
│   ├── bm25_index.py
│   ├── hybrid_search.py
│   ├── rag_service.py
│   └── search_service.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── requirements-dev.txt
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Shantanu62/enterprise-hybrid-rag.git
cd enterprise-hybrid-rag
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

For application dependencies:

```bash
pip install -r requirements.txt
```

For development and testing:

```bash
pip install -r requirements-dev.txt
```

### 4. Configure Environment Variables

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the following variables in `.env`:

```env
# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=enterprise_rag
DB_USER=postgres
DB_PASSWORD=your_postgres_password

# Qdrant
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key

# Groq
GROQ_API_KEY=your_groq_api_key

# JWT Authentication
JWT_SECRET_KEY=your_secure_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important:** Never commit your `.env` file or expose API keys, database passwords, or JWT secrets.

### 5. Set Up PostgreSQL

Create a PostgreSQL database named:

```sql
CREATE DATABASE enterprise_rag;
```

Apply the database schema:

```powershell
python apply_schema.py
```

Configure your PostgreSQL credentials in `.env` before applying the schema.

### 6. Initialize the First Organization and Owner

Run the bootstrap script only once for a fresh database:

```powershell
python bootstrap_owner.py
```

Follow the prompts to initialize the first organization and owner account.

Do not run the bootstrap script again on an already initialized database.

### 7. Start the FastAPI Backend

Open a terminal and run:

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- Health Check: http://127.0.0.1:8000/health

### 8. Start the Streamlit Frontend

Open a second terminal, activate the virtual environment, and run:

```powershell
streamlit run app.py
```

The application will be available at:

http://localhost:8501

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Authenticate users |
| GET | `/organizations/{organization_id}/access-check` | Verify organization access |
| GET | `/organizations/{organization_id}/admin-check` | Verify administrative permissions |
| POST | `/organizations/{organization_id}/documents/upload` | Upload and ingest documents |
| POST | `/organizations/{organization_id}/ask` | Ask questions using RAG |
| GET | `/health` | Check API health |

All protected organization endpoints require valid authentication and membership authorization.

## Security

The application implements:

- Argon2 password hashing.
- JWT-based authentication.
- Role-based access control.
- Organization-level tenant isolation.
- Server-side membership verification.
- Tenant-scoped document retrieval.
- Organization-scoped vector search.
- Environment-based secret management.

## Testing

Run the complete test suite:

```powershell
python -m pytest tests/ -v
```

The test suite covers authentication, authorization, database services, ingestion, retrieval, and tenant isolation.

## Current Project Status

The application has completed its core implementation and local integration testing.

The automated test suite has passed 90 tests, with one deprecation warning.

Cloud deployment and production-readiness validation are separate steps and should not be considered complete until verified.

## Future Improvements

- Docker-based deployment.
- Cloud-hosted frontend and backend.
- Persistent document storage.
- Production monitoring and observability.
- Advanced evaluation and performance optimization.
- Expanded automated security testing.

## Author

**Shantanu Anand**

- GitHub: https://github.com/Shantanu62
- LinkedIn: https://www.linkedin.com/in/shantanu-anand-97b90b292/

---

*Built to demonstrate secure, multi-tenant AI application development using modern RAG architecture.*