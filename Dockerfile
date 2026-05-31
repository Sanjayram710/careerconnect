FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies (build-essential, libpq-dev are useful for PostgreSQL drivers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose port 8080 (Matches container mapping)
EXPOSE 8080

# Run with Gunicorn production server by default, binding to the dynamic PORT or 8080
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
