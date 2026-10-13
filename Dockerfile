# Multi-stage production build for Noise-Resilient Quantum System (QFF 2026)
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
