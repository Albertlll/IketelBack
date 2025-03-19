from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from fastapi.responses import JSONResponse
from api.endpoints import worlds, game, cards, auth

app = FastAPI(
    title="Language Learning App API",
    description="API для обучающего приложения по языкам"
)

# Укажите широкий спектр разрешенных доменов для разработки
origins = [
    "https://iketel.ru"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Указываем конкретные домены
    allow_origin_regex=r"https?://192\.168\.(\d+)\.(\d+)(:\d+)?",  # Поддержка локальной сети
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-CSRFToken", "Authorization"],
    max_age=86400,  # 1 день кеширования префлайт запросов
)

@app.get("/")
async def root():
    return JSONResponse({"status": "ok", "message": "Server is running"})


# Подключаем эндпоинты
app.include_router(worlds.router, prefix="/worlds", tags=["worlds"])
app.include_router(game.router, prefix="/game", tags=["game"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        # Для поддержки HTTPS раскомментируйте следующие строки и укажите пути к сертификатам
        # ssl_keyfile="./ssl/key.pem",
        # ssl_certfile="./ssl/cert.pem",
    )