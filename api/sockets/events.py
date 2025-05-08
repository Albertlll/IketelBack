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
    print("SOCKET CONNECT TRIGGERED")
    logger.info(f"[CONNECT] SID: {sid}")

    db = next(get_db())

    try:
        token = (
            auth_data.get("token") if auth_data
            else environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        )

        if token:
            try:
                user = await get_current_user_ws(token, db)
                await sio.save_session(sid, {
                    "user_id": user.id,
                    "email": user.email,
                    "role": "host",
                })
                logger.info(f"[CONNECT] Authenticated host: {user.email}")
            except Exception as e:
                logger.warning(f"[CONNECT] Invalid token, rejecting. Error: {str(e)}")
                raise ConnectionRefusedError("Invalid token")
        else:
            # Гость (студент) — разрешаем подключение без токена
            await sio.save_session(sid, {
                "role": "student",
            })
            logger.info(f"[CONNECT] Guest connected: SID={sid}")

        return True

    except Exception as e:
        logger.error(f"[CONNECT] Failed: {str(e)}", exc_info=True)
        raise ConnectionRefusedError("Connection error")

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
@sio.on('host_join', namespace='/')
async def host_join(sid, data):
    """Обработчик подключения хоста к сессии"""
    try:
        logger.info(f"Host join attempt. SID: {sid}, Data: {data}")

        # Проверка наличия обязательных полей
        if 'token' not in data or 'session_code' not in data:
            error_msg = "Missing required fields: token or session_code"
            logger.error(f"{error_msg}. Data: {data}")
            await sio.emit('error', {'message': error_msg}, to=sid)
            return

        logger.debug("Authenticating user...")
        user = await get_current_user_ws(data['token'], get_db())
        if not user:
            error_msg = "User authentication failed"
            logger.error(f"{error_msg}. Token: {data['token']}")
            await sio.emit('error', {'message': error_msg}, to=sid)
            return

        logger.info(f"User authenticated. User ID: {user.id}, Email: {user.email}")
        session_code = data['session_code']
        logger.debug(f"Session code: {session_code}")

        with get_db() as db:
            logger.debug(f"Searching session. Code: {session_code}, Host ID: {user.id}")
            session = db.query(AdventureSession).filter_by(
                join_code=session_code,
                host_id=user.id
            ).first()

            if not session:
                error_msg = f"Session not found or access denied. Code: {session_code}"
                logger.error(f"{error_msg}. User ID: {user.id}")
                raise Exception(error_msg)

            logger.info(f"Session found. Session ID: {session.id}, Code: {session_code}")

            session_data = {
                'role': 'host',
                'session_code': session_code,
                'user_id': user.id
            }
            logger.debug(f"Saving session data: {session_data}")
            await sio.save_session(sid, session_data)

            logger.debug(f"Entering room: {session_code}")
            await sio.enter_room(sid, session_code)

            logger.info(f"Host successfully joined. SID: {sid}, Room: {session_code}")
            await sio.emit('host_ready', to=sid)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Host join error. SID: {sid}. Error: {error_msg}", exc_info=True)
        await sio.emit('error', {'message': error_msg}, to=sid)


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
        await sio.emit('new_student_joined', {'sid': sid}, room=session_code)

        logger.info("Handler completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}", exc_info=True)
        await sio.emit('join_error', {'error': str(e)}, to=sid)
        return False