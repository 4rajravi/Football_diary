FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data

# Run initial data load on first start
CMD ["sh", "-c", "python -m app.etl.pipeline && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
