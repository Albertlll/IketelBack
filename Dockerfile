# Используем официальный образ Python 3.9
FROM python:3.9-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

RUN mkdir -p /app/ssl

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .

RUN --mount=type=secret,id=ssl_key cat /run/secrets/ssl_key > /app/ssl/server-key.key
RUN --mount=type=secret,id=ssl_cert cat /run/secrets/ssl_cert > /app/ssl/server-cert.crt
RUN --mount=type=secret,id=ssl_ca cat /run/secrets/ssl_ca > /app/ssl/server-ca.crt

# Указываем порт, который будет использовать приложение
EXPOSE 8000

# Команда для запуска приложения с SSL
CMD uvicorn main:asgi_app --host 0.0.0.0 --port 8000 \
    --ssl-keyfile /app/ssl/server-key.key \
    --ssl-certfile /app/ssl/server-cert.crt \
    --ssl-ca-certs /app/ssl/server-ca.crt

