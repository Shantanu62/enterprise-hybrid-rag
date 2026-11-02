FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
# Install CPU-only PyTorch first (no CUDA dependencies).
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# Install the remaining application dependencies.
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
EXPOSE 8501
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
