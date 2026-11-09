# Service workflow Guide Administratif — LangGraph + FastAPI
FROM python:3.12-slim

WORKDIR /app

# Dépendances d'abord (cache de build)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
