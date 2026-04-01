# Use a specific slim version to keep base small
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Crucial: Tell Playwright where to install browsers
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

# Install system dependencies in one layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    # Required for Playwright to function
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (only Chromium to save space)
RUN playwright install chromium && \
    playwright install-deps chromium && \
    # Cleanup to save space
    rm -rf /var/lib/apt/lists/*

# Copy only the necessary files
COPY ngai.py .

CMD ["uvicorn", "ngai:app", "--host", "0.0.0.0", "--port", "8000"]
