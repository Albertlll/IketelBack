import socketio
import logging
from core.consts import ORIGINS
from core.security import get_current_user_ws
from db.session import get_db
from . import events

# Настройка логгера с максимальной детализацией
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def check_origin(origin):
    allowed = [
        "exp://",
        "http://localhost",
        "https://iketel.ru"
    ]
    return origin in allowed


# Создаем Socket.IO сервер с явными параметрами
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*",
    logger=True,  # Включаем логирование
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    namespaces=['/']  # Явно указываем namespace
)


