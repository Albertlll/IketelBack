import socketio
import logging
from core.consts import ORIGINS
logger = logging.getLogger(__name__)

# Создаем Socket.IO сервер
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ORIGINS,
    logger=logger,
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25
)