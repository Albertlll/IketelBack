import logging
import socketio
from core.consts import ORIGINS

# Настройка логгера с максимальной детализацией
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def check_origin(origin):
    allowed = ORIGINS + [
        "exp://",
    ]
    return origin in allowed


# Создаем Socket.IO сервер с явными параметрами
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ORIGINS,
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
)


