FROM python:3.13-slim

ENV PYTHONUNBUFFERED=true
WORKDIR /app

# Install required system packages
RUN apt-get update && apt-get -y install libpq-dev gcc libcairo2-dev

# Copy app files and install dependencies
COPY /requirements.txt .
#COPY .env .
RUN pip install --no-cache-dir -r requirements.txt

COPY /cosm/ ./cosm/

# Fatal issue /!\
# COPY ./service-account.json ./

# Set environment
ENV PYTHONPATH=/app
ENV PORT=8000

EXPOSE 8000

# Run directly
CMD ["adk", "api_server", "--allow_origins", "*"]
