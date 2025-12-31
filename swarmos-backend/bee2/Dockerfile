FROM python:3.11-slim

# For GPU support, use: nvidia/cuda:12.4.0-runtime-ubuntu22.04
# Then install Python

WORKDIR /app

# Install dependencies
COPY bee2/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared rails (only what worker needs)
COPY rails/crypto/ ./rails/crypto/
COPY rails/schemas/ ./rails/schemas/

# Copy Bee-2 code
COPY bee2/ ./bee2/

CMD ["python", "-m", "bee2.worker.main"]
