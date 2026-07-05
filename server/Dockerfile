# Immagine multi-arch: funziona su Mac (arm64) e Raspberry Pi 4/5 a 64 bit
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_DEBUG=0 \
    PORT=5000 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python", "app.py"]
