# Use an official lightweight Python image
FROM python:3.11-slim

# Install FFmpeg and SSL certificates for HTTPS streams
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Set default port
ENV PORT=8000
EXPOSE 8000

# Run stream.py
CMD ["python", "stream.py"]
