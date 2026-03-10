# Multi-stage build for smaller image
FROM python:3.9-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in builder stage
COPY AI_SOS_SYSTEM/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final stage - smaller image
FROM python:3.9-slim

WORKDIR /app/backend

# Copy only system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend code (to current directory)
COPY AI_SOS_SYSTEM/backend/ ./

# Create uploads directory for temporary audio files
RUN mkdir -p /app/backend/uploads

# Expose port
EXPOSE 8000

# Run the server from backend directory
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

