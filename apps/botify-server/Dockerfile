FROM python:3.9-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.7.1

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not use a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies without development dependencies
RUN poetry install --only main

# Copy the application code
COPY ./app ./app

# Expose the API port
EXPOSE 8000

# Command to run the application with the correct module path
CMD ["python", "-m", "app.main"]