from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from fastapi.responses import JSONResponse
from api.endpoints import worlds, game, cards, auth

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="Language Learning App API",
    description="API для обучающего приложения по языкам"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)