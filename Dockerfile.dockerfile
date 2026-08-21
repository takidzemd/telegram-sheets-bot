FROM python:3.10-slim

# Устанавливаем зависимости для Pillow
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]