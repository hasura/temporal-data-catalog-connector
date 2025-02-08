FROM python:3.10

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY /docker /scripts
COPY /functions /functions

# Ensure scripts are executable
RUN chmod +x /scripts/package-restore.sh /scripts/start.sh

# Run the package-restore script
RUN /scripts/package-restore.sh

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=10s --start-period=1s --retries=3 \
    CMD [ "bash", "-c", "exec curl -f http://localhost:${HASURA_CONNECTOR_PORT:-8080}/health" ]

CMD [ "/scripts/start.sh" ]