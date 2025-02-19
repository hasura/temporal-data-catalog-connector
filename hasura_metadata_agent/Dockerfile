FROM python:3.9-slim

# Set working directory to root level
WORKDIR /workspace

# Define build arguments
ARG SRC_DIR

# Copy requirements and install dependencies
COPY hasura_metadata_agent/ /workspace/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code maintaining the app package structure
COPY ${SRC_DIR}/engine/build/metadata.json /build/metadata.json

# Environment variables
ENV ENGINE_BUILD_PATH=/build/metadata.json \
    CLEAN_DATABASE=False \
    PYTHONPATH=/workspace

# Set the default command
CMD ["python", "/workspace/run.py", "--log-cli-level=DEBUG"]
