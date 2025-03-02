# Используем официальный образ Python 3.9
FROM python:3.9-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в контейнер
COPY . .

# Указываем порт, который будет использовать приложение
EXPOSE 8000

# Команда для запуска приложения
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile /etc/ssl/certificate.key --ssl-certfile /etc/ssl/certificate.crt --ssl-ca-certs /etc/ssl/certificate_ca.crt
