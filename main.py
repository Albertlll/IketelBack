from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import socketio
from fastapi.responses import JSONResponse
from api.endpoints import worlds, game, cards, auth
from api.sockets.server import sio
from api.sockets.events import register_socket_events

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Language Learning App API",
    description="API для обучающего приложения по языкам"
)

# Укажите широкий спектр разрешенных доменов для разработки
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://localhost",
    "https://localhost:3000",
    "https://localhost:8000",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
    "https://127.0.0.1",
    "https://127.0.0.1:3000",
    "https://127.0.0.1:8000",
    "http://127.0.0.1:8000",
    "https://iketel.ru",
    "https://www.iketel.ru",
    "http://iketel.ru",
    "http://www.iketel.ru",
    "capacitor://localhost",
    "ionic://localhost",
    # Добавьте другие домены, с которых будут приходить запросы
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

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request, call_next):
    logger.debug(f"Входящий запрос: {request.method} {request.url}")
    logger.debug(f"Заголовки: {request.headers}")
    response = await call_next(request)
    return response

# Подключаем эндпоинты
app.include_router(worlds.router, prefix="/worlds", tags=["worlds"])
app.include_router(game.router, prefix="/game", tags=["game"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# Регистрируем события Socket.IO
register_socket_events()

# Создаем ASGI приложение
app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path='socket.io'
)

if __name__ == "__main__":
    logger.info("Запуск сервера...")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
        # Для поддержки HTTPS раскомментируйте следующие строки и укажите пути к сертификатам
        # ssl_keyfile="./ssl/key.pem",
        # ssl_certfile="./ssl/cert.pem",
    )