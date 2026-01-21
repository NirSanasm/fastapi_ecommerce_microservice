FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY services/payment_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/payment_service/app ./app

EXPOSE 8005

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
