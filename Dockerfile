# Stage 1: build React SPA
FROM node:20-alpine AS ui-builder
WORKDIR /ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

# Stage 2: Python API
FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=ui-builder /ui/dist ./ui/dist

EXPOSE 8085
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8085"]
