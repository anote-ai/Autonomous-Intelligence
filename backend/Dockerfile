# Use a Python image
FROM python:3.13-slim

# Avoid buffering and enable pip optimizations
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set workdir inside container
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy requirements first (better caching)
COPY pyproject.toml /app/pyproject.toml

# Install dependencies
RUN uv pip install --system -e .

# Copy the rest of the project
COPY . /app

# Default command (overridden by docker-compose)
CMD ["python", "-V"]