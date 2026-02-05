FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create volume for database persistence
VOLUME ["/app/instance"]

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# Use PORT environment variable (set by hosting platform)
EXPOSE 8080

# Run the application
CMD gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 app:app
