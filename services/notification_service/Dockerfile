FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared
COPY services/notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/notification_service/app ./app

EXPOSE 8006

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]
