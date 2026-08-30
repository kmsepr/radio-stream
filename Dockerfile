FROM python:3.11-slim

# 1. Install FFmpeg and system certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy app code
COPY . .

# 5. Set default port
ENV PORT=8000
EXPOSE 8000

# 6. Start the server
CMD ["python", "app.py"]
