FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY harmonic_scanner.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CLOUD_MODE=true

# Run the scanner
CMD ["python", "harmonic_scanner.py"]
