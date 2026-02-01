# pii-anonymizer-service Development Guidelines

## Project Structure

```text
├── backend/
│   └── src/
│       ├── models/          # SQLAlchemy models
│       ├── services/        # Core logic (detector, anonymizer, mapping_store)
│       ├── api/             # FastAPI routes
│       └── generators/      # Synthetic data generators (uses names-dataset, geonamescache)
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── static/                  # Built frontend assets
├── data/                    # SQLite database
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Technologies

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Microsoft Presidio, Faker, names-dataset, geonamescache
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Database**: SQLite (local file-based)
- **Deployment**: Docker container, Azure Container Apps

## Commands

```bash
# Backend development
cd backend && pytest
ruff check .

# Frontend development
cd frontend && npm run dev
npm run build

# Docker
docker-compose up --build
docker-compose down
```

## Running Locally

```bash
# Backend
source .venv/bin/activate
uvicorn backend.src.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

## Code Style

- Python 3.11: Follow standard conventions
- TypeScript: React functional components with hooks
