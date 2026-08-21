FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Обязательно копируем файл с ключами в контейнер!
COPY credentials.json .
COPY bot.py .

CMD ["python", "bot.py"]
