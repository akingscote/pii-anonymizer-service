# PII Anonymizer

Offline PII detection and anonymization using Microsoft Presidio.

## Deploy to Azure

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fakingscote%2Fpii-anonymizer-service%2Fmain%2Fazuredeploy.json)

Deploys to Azure Container Apps with automatic HTTPS. You'll get a URL like `https://pii-anonymizer.something.uksouth.azurecontainerapps.io`

## Run Locally

```bash
# Docker
docker-compose up -d
# Open http://localhost:8000
```

## Run from Docker Hub

```bash
docker run -p 8000:8000 ashleykingscote/pii-anonymizer:latest
```
