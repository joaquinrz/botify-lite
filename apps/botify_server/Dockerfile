FROM python:3.13-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies, no dev dependencies, clean up in the same layer
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    find /usr/local -type f -name '*.pyc' -delete


# Start from a clean, minimal base image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin/opentelemetry* /usr/local/bin/


# Install the uvicorn server and explicit OpenTelemetry packages
RUN pip install --no-deps --ignore-installed --no-cache-dir uvicorn && \
    opentelemetry-bootstrap -a install


# Copy bot-service code
COPY ./app/api ./app/api
COPY ./app/core ./app/core
COPY ./app/services ./app/services
COPY ./prompts ./prompts
COPY ./pyproject.toml ./pyproject.toml

# Expose the API port
EXPOSE 8000


# Copy entrypoint script and set to executable
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


# Set the entrypoint to run the app
ENTRYPOINT ["/entrypoint.sh"]
