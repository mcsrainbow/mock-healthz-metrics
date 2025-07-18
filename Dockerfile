# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Bottle (latest)
RUN pip install --no-cache-dir bottle

# Copy application code
COPY mock-healthz-metrics.py .

# Expose the HTTP port
EXPOSE 8080

# Start the server
CMD ["python", "mock-healthz-metrics.py"]
