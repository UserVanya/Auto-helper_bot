FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
COPY .env ./
COPY . ./

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot/main.py"] 