FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /backend_course2025
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
COPY requirements.txt .
RUN pip install --retries 10 --timeout 300 -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "routes.api:app", "--host", "0.0.0.0", "--port", "8000"]