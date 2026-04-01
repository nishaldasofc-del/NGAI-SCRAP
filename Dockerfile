# =============================================================================
# NGAI Dockerfile
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies required for Playwright and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser & OS dependencies
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy the application code
COPY ngai.py .

# Default command (overridden by docker-compose)
CMD ["uvicorn", "ngai:app", "--host", "0.0.0.0", "--port", "8000"]
