FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy backend including alembic files
COPY . /app

# Make your source importable: we want /app/src on PYTHONPATH
ENV PYTHONPATH=/app/src

EXPOSE 8000