FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and metadata
COPY ./app /app
COPY ./example/engine/build/metadata.json /build/metadata.json

# Environment variables
ENV ENGINE_BUILD_PATH=/build/metadata.json \
    CLEAN_DATABASE=False \
    PYTHONPATH=/app

# Set the default command
CMD ["python", "-m", "app.metadata.run"]
