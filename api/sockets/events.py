from sqlalchemy.orm import Session
import logging

from db.models import SessionParticipant, AdventureSession
from db.session import get_db
from .server import sio
from core.security import get_current_user_ws

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования

# Форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Обработчик для вывода в консоль
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


@sio.event
async def connect(sid, environ, auth_data=None):
    db = next(get_db())
    try:
        # Гость (студент) — нет токена
        if not auth_data or "token" not in auth_data:
            await sio.save_session(sid, {"role": "student"})
            logger.info(f"Guest connected. SID: {sid}")
            return True  # Разрешаем подключение

        # Хост — проверяем токен
        token = auth_data["token"]
        user = await get_current_user_ws(token, db)

        await sio.save_session(sid, {
            "user_id": user.id,
            "email": user.email,
            "role": "host",
            "is_authenticated": True,
        })
        logger.info(f"Host connected. User ID: {user.id}, SID: {sid}")
        return True

    except Exception as e:
        logger.error(f"Auth failed: {e}")
        raise ConnectionRefusedError("Invalid token")
    finally:
        db.close()





#
# @sio.event
# async def disconnect(sid):
#     """Обработчик отключения клиента"""
#     try:
#         logger.info(f"Client disconnected. SID: {sid}")
#
#         with get_db() as db:
#             logger.debug(f"Searching participant with SID: {sid}")
#             participant = db.query(SessionParticipant).filter_by(socket_id=sid).first()
#
#             if participant:
#                 logger.info(f"Deleting participant. ID: {participant.id}, SID: {sid}")
#                 db.delete(participant)
#                 db.commit()
#                 logger.debug("Participant deleted successfully")
#             else:
#                 logger.debug(f"No participant found for SID: {sid}")
#     except Exception as e:
#         logger.error(f"Disconnect error for SID: {sid}. Error: {str(e)}", exc_info=True)
#
#
@sio.on("host_join")
async def host_join(sid, data):
    session_data = await sio.get_session(sid)

    if session_data.get("role") != "host":
        await sio.emit("error", {"message": "Access denied"}, to=sid)
        return

    db = next(get_db())
    try:
        session = db.query(AdventureSession).filter_by(

            join_code=data["session_code"],
            host_id=session_data["user_id"]

        ).first()

        if not session:
            await sio.emit("error", {"message": "Session not found"}, to=sid)
            return

        await sio.enter_room(sid, session.join_code)
        await sio.emit("host_ready", to=sid)

    finally:
        db.close()

@sio.on('student_join')
async def student_join(sid, data):
    logger.info(f"START handling student_join. SID: {sid}, Data: {data}")

    try:
        session_code = data.get('session_code')
        username = data.get('username')

        logger.info(f"Params extracted: code={session_code}, username={username}")

        # Валидация
        if not session_code or len(session_code) != 4:
            raise ValueError("Invalid session code")

        # Проверка БД
        logger.info("Accessing DB...")
        db = next(get_db())
        session = db.query(AdventureSession).filter_by(join_code=session_code).first()
        logger.info(f"DB query result: {session}")

        if not session:
            raise ValueError("Session not found")

        # Сохраняем сессию
        logger.info("Saving session...")
        await sio.save_session(sid, {'role': 'student', 'session_code': session_code})

        # Отправка подтверждения
        logger.info(f"Emitting student_joined to {sid}")
        await sio.emit('student_joined', {'message': 'Success'}, to=sid)

        # Уведомление хоста
        logger.info(f"Emitting new_student_joined to room {session_code}")
        await sio.emit('new_student_joined', {'sid': sid, 'username' : username}, room=session_code)

        logger.info("Handler completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}", exc_info=True)
        await sio.emit('join_error', {'error': str(e)}, to=sid)
        return False