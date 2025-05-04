from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import socketio
from fastapi.responses import JSONResponse
from api.endpoints import worlds, game, auth, adventures
from api.sockets.server import sio
from core.consts import ORIGINS
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
fastapi_app = FastAPI(
    title="Language Learning App API",
    description="API для обучающего приложения по языкам"
)


fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Указываем конкретные домены
    allow_origin_regex=r"https?://192\.168\.(\d+)\.(\d+)(:\d+)?",  # Поддержка локальной сети
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-CSRFToken", "Authorization"],
    max_age=86400,  # 1 день кеширования префлайт запросов
)

@fastapi_app.get("/")
async def root():
    return JSONResponse({"status": "ok", "message": "Server is running"})

# Middleware для логирования запросов
@fastapi_app.middleware("http")
async def log_requests(request, call_next):
    logger.debug(f"Входящий запрос: {request.method} {request.url}")
    logger.debug(f"Заголовки: {request.headers}")
    response = await call_next(request)
    return response

# Подключаем эндпоинты
fastapi_app.include_router(worlds.router, prefix="/worlds", tags=["worlds"])
fastapi_app.include_router(game.router, prefix="/game", tags=["game"])
fastapi_app.include_router(auth.router, prefix="/auth", tags=["auth"])
fastapi_app.include_router(adventures.router, prefix="/adventures", tags=["adventures"])



# Создаем ASGI приложение
app = socketio.ASGIApp(
    
    socketio_server=sio,
    other_asgi_app=fastapi_app,
    socketio_path='/sio'
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