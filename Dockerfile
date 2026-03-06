# SkyFi Remote MCP Server — single-stage image
FROM python:3.10-slim

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

EXPOSE 8000

# Same entrypoint as local: python -m src.server (streamable-http on :8000)
CMD ["python", "-m", "src.server"]
