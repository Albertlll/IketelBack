# IKETEL Server

## Установка

1. Установите зависимости:
```
pip install -r requirements.txt
```

2. Настройте переменные окружения в файле `.env`:
```
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/db
SECRET_KEY=supersecret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

S3_ENDPOINT=https://storage.yandexcloud.net
S3_BUCKET=your-bucket
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
```

## Запуск
```
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Авторизация
- Используется JWT (access/refresh).
- Точка получения токенов: `POST /auth/login` (также при `POST /auth/register`).
- Обновление токена: `POST /auth/refresh` {"refresh_token": "..."}.
- Защищённые маршруты используют `Authorization: Bearer <access_token>`.

Пример ответа при логине/регистрации:
```
{
  "success": true,
  "data": {
    "access_token": "...",
    "token_type": "bearer",
    "refresh_token": "...",
    "email": "user@example.com",
    "username": "User"
  }
}
```

## Формат ошибок
Единый ответ при ошибках:
```
{
  "success": false,
  "error": {
    "code": "<код>",
    "message": "<сообщение>",
    "details": { /* опционально */ }
  }
}
```

Валидация запроса: код `VALIDATION_ERROR` (HTTP 422). Неавторизован: HTTP 401.

## Основные маршруты
- `GET /worlds` — список публичных миров
- `GET /worlds/{id}` — детальная информация
- `POST /worlds` — создать мир (требуется авторизация)
- `PUT /worlds/{id}` — обновить мир (требуется авторизация)
- `DELETE /worlds/{id}` — удалить мир (требуется авторизация)
- `PATCH /worlds/{id}/visibility` — изменить публичность (требуется авторизация)
- `POST /adventures` — создать игровую сессию
- Сокеты — путь `/sio`

## Безопасность
- CORS ограничен списком доменов из `core/consts.py`.
- Загрузка изображений проверяет размер (до 5MB) и формат (jpeg/png).
- Refresh токен нельзя использовать как access.
