FROM python:3.13-slim-bookworm

ENV PYTHONUNBUFFERED=true
WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get -y install libpq-dev gcc curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv and move to PATH
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# Copy dependency files and install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

# DEBUG STEP
RUN uv run uvicorn --version

# Copy source code
COPY src/ ./src/

# Environment
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Run app
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
