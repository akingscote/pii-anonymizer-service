# PII Anonymizer - Multi-stage build
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build


# Stage 2: Python runtime
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model during build (not at runtime)
# Using en_core_web_lg for best accuracy (Presidio's default)
RUN python -m spacy download en_core_web_lg

# Copy backend code
COPY backend/ ./backend/
COPY pyproject.toml ./

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/static ./static/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:////app/data/pii_anonymizer.db

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

# Initialize database and run server
CMD ["sh", "-c", "python -m backend.src.cli init-db --seed && uvicorn backend.src.api.main:app --host 0.0.0.0 --port 80"]
