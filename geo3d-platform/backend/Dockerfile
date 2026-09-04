FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL env
ENV GDAL_VERSION=3.6.2
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /data/raw /data/processed /data/terrain /data/tiles /data/samples

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
