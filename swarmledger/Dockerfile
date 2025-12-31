FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/

RUN mkdir -p /app/data

EXPOSE 8100

CMD ["python", "-m", "api.main"]
