FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY bee1/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared rails
COPY rails/ ./rails/

# Copy Bee-1 code
COPY bee1/ ./bee1/

# Create data directory
RUN mkdir -p /app/data /app/audit

EXPOSE 8000

CMD ["python", "-m", "bee1.api.main"]
