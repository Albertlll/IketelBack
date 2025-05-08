from sqlalchemy.orm import Session
import logging

from db.models import SessionParticipant, AdventureSession
from db.session import get_db
from server import sio
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

@sio.on("connect")
async def handle_connect(sid, environ, auth_data=None):

    print("Подключаемся к сокету")
    db = next(get_db())  # Получаем сессию БД вручную
    try:
        token = (
            auth_data.get("token") if auth_data
            else environ.get("HTTP_AUTHORIZATION", "").replace("Bearer ", "")
        )
        if not token:
            logger.error("No token provided")
            raise ConnectionRefusedError("Token is required")

        user = await get_current_user_ws(token, db)

        await sio.save_session(sid, {
            "user_id": user.id,
            "email": user.email
        })
        logger.info(f"User {user.email} connected successfully")
        return True

    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        raise ConnectionRefusedError("Authentication failed")
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


@sio.on('student_join', namespace='/')
async def handle_student_join(sid, data):
    """
    Обработчик подключения ученика
    Не требует JWT, только session_code
    """
    try:
        session_code = data.get('session_code')
        username = data.get('session_code')


        # Валидация кода сессии
        if not session_code or len(session_code) != 4:
            raise ValueError("Invalid session code")

        logger.info(f"Student joined. SID: {sid}, Session: {session_code} Username {username}")

        # Проверяем существование сессии в БД
        db = next(get_db())
        session = db.query(AdventureSession).filter_by(join_code=session_code).first()
        if not session:
            raise ValueError("Session not found")

        # Сохраняем данные ученика
        await sio.save_session(sid, {
             'role': 'student',
             'session_code': session_code
        })
        #
        # # Добавляем в комнату сессии
        # await sio.enter_room(sid, f'session_{session_code}')

        # Отправляем подтверждение
        await sio.emit('student_joined', {
            'message': 'Successfully joined session',
        }, to=sid)

        # Уведомляем хост о новом ученике
        await sio.emit('new_student_joined', {
            'student_sid': sid,
        }, room=session_code)

    except Exception as e:
        logger.error(f"Student join error: {str(e)}")
        await sio.emit('join_error', {
            'message': str(e)
        }, to=sid)