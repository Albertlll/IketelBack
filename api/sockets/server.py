import socketio
import logging
from core.consts import ORIGINS
from core.security import get_current_user_ws
from db.session import get_db

# Настройка логгера с максимальной детализацией
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Создаем Socket.IO сервер с явными параметрами
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=ORIGINS,
    logger=True,  # Включаем логирование
    engineio_logger=True,
    ping_timeout=60,
    ping_interval=25,
    namespaces=['/']  # Явно указываем namespace
)


@sio.on('host_join', namespace='/')
async def host_join(sid, data):
    logger.debug(f"!!! ОБРАБОТЧИК host_join ВЫЗВАН !!! SID: {sid}")
    logger.debug(f"Полученные данные: {data}")
    await sio.emit('host_join_ack', {'received': True}, to=sid)