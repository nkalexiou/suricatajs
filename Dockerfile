# Stage 1: build React SPA
FROM node:20-alpine AS ui-builder
WORKDIR /ui
COPY ui/package*.json ./
RUN npm ci
COPY ui/ .
RUN npm run build

# Stage 2: install Python dependencies into an isolated venv
FROM python:3.13-slim AS python-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
RUN python -m venv --copies /venv
RUN /venv/bin/pip install --upgrade pip setuptools
COPY requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Stage 3: distroless runtime — no shell, no package manager, no OS CVE surface
FROM gcr.io/distroless/python3-debian13
COPY --from=python-builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=python-builder /usr/local/lib/libpython3.13.so.1.0 /usr/local/lib/libpython3.13.so.1.0
COPY --from=python-builder /venv /venv
ENV LD_LIBRARY_PATH=/usr/local/lib
WORKDIR /app
COPY . .
COPY --from=ui-builder /ui/dist ./ui/dist
EXPOSE 8085
ENTRYPOINT ["/venv/bin/python"]
CMD ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8085"]
