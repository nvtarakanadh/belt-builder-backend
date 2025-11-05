FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    make \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create media directories
RUN mkdir -p /app/media/components/original \
    /app/media/components/glb \
    /app/media/temp \
    /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Expose port (Railway will set PORT env var)
EXPOSE $PORT

# Run migrations and start server using gunicorn
# Railway sets PORT environment variable automatically
CMD python manage.py migrate && python manage.py collectstatic --noinput && gunicorn cadbuilder.wsgi:application --bind 0.0.0.0:${PORT:-8000}

