# Use a smaller base image
FROM python:3.12-alpine

# Set work directory early for better caching
WORKDIR /app

# Copy only requirements first to take advantage of Docker caching
COPY requirements.txt .

# Install dependencies (Alpine needs some build dependencies)
RUN apk add --no-cache gcc musl-dev libffi-dev && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    apk del gcc musl-dev libffi-dev

# Copy application files last
COPY . .

# Expose the correct port
EXPOSE 5600

# Create a non-root user
RUN adduser -u 5678 --disabled-password --gecos "" appuser
USER appuser

# Command to start the server
CMD ["gunicorn", "--bind", "0.0.0.0:5600", "Backend.app:app"]
