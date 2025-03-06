# Используем официальный образ Python 3.9
FROM python:3.9-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Создаем папку для сертификатов
RUN mkdir -p /app/ssl

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Копируем SSL сертификаты из секретов
RUN --mount=type=secret,id=ssl_key cat /run/secrets/ssl_key > /app/ssl/server-key.key
RUN --mount=type=secret,id=ssl_cert cat /run/secrets/ssl_cert > /app/ssl/server-cert.crt
RUN --mount=type=secret,id=ssl_ca cat /run/secrets/ssl_ca > /app/ssl/server-ca.crt

# Открываем порт
EXPOSE 8000

# Запуск сервера
CMD ["python", "main.py"]
