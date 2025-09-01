
# # Development stage
# FROM python:3.10-slim

# # Install system dependencies
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     default-jdk \
#     pkg-config \
#     default-libmysqlclient-dev \
#     && rm -rf /var/lib/apt/lists/* \
#     && apt-get clean

# # Create and activate virtual environment
# RUN python -m venv /opt/venv
# ENV PATH="/opt/venv/bin:$PATH"

# # Upgrade pip and install wheel
# RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# # Install tokenizers and anthropic separately
# RUN pip install --no-cache-dir tokenizers==0.13.3 anthropic==0.7.4

# # Install system dependencies needed for lxml (and python-docx)
# RUN apt-get update && apt-get install -y \
#     libxml2-dev \
#     libxslt-dev \
#     python3-dev \
#     build-essential \
#  && rm -rf /var/lib/apt/lists/*

# # Set up application directory
# WORKDIR /app

# COPY ./database/schema.sql /docker-entrypoint-initdb.d/init.sql

# # Copy requirements first for better caching
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the rest of the application
# COPY . .

# # Set environment variables for development
# ENV FLASK_APP=app.py \
#     FLASK_ENV=development \
#     FLASK_DEBUG=1 \
#     PYTHONUNBUFFERED=1 \
#     PYTHONDONTWRITEBYTECODE=1

# # Expose ports
# EXPOSE 5000 6379 9998 8000

# #!/bin/bash
# # start.sh
# ray start --head --port=6379 --dashboard-port=9998
# sleep 3  # small delay to ensure Ray is up
# flask run --host=0.0.0.0 --port=5000 --no-reload

# COPY start.sh /app/start.sh
# RUN chmod +x /app/start.sh
# CMD ["/app/start.sh"]


# # Use the start script as the entrypoint
# CMD ["bash", "-c", "ray start --head --port=6379 --dashboard-port=9998 && flask run --host=0.0.0.0 --port=5000 --no-reload"]a

# Development stage
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-jdk \
    pkg-config \
    default-libmysqlclient-dev \
    libxml2-dev \
    libxslt-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install tokenizers and anthropic separately
RUN pip install --no-cache-dir tokenizers==0.13.3 anthropic==0.7.4

# Set up application directory
WORKDIR /app

# Copy database schema
COPY ./database/schema.sql /docker-entrypoint-initdb.d/init.sql

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Set environment variables for development
ENV FLASK_APP=app.py \
    FLASK_ENV=development \
    FLASK_DEBUG=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose ports
EXPOSE 5000 6379 9998 8000

# Copy start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Use start script as the entrypoint
CMD ["/app/start.sh"]
