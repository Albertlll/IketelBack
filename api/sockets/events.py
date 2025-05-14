from sqlalchemy.orm import Session
import logging

from db.models import AdventureSession, AdventureStep, QuizOption
from db.session import get_db
from .server import sio
from core.security import get_current_user_ws
from ..utils.step_generator import generate_steps

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

host_sessions = {}
leaderboard = {}

def calculate_score(is_correct: bool, time_spent: float, base_points=100) -> int:
    if not is_correct:
        return 0

    max_time = 30.0
    time_factor = min(max_time, time_spent) / max_time
    return int(base_points * (1 - time_factor))  # От 100 до 0




class ConnectError(Exception):
    """Базовая ошибка подключения"""
    def __init__(self, message="Ошибка подключения"):
        self.message = message
        super().__init__(self.message)

class SessionNotFoundError(ConnectError):
    def __init__(self):
        super().__init__("Сессия не найдена")

class InvalidCodeError(ConnectError):
    def __init__(self):
        super().__init__("Неверный код сессии")

class HostPermissionError(ConnectError):
    def __init__(self):
        super().__init__("Только хост может выполнить это действие")

class IntegrityError(ConnectError):
    def __init__(self):
        super().__init__("Только хост может выполнить это действие")






@sio.event
async def connect(sid, environ, auth_data=None):
    db = next(get_db())
    try:
        if not auth_data or "token" not in auth_data:
            await sio.save_session(sid, {"role": "student"})
            return

        token = auth_data["token"]
        user = await get_current_user_ws(token, db)

        await sio.save_session(sid, {
            "user_id": user.id,
            "email": user.email,
            "role": "host",
            "is_authenticated": True,
            "isStarted" : False
        })

    except Exception as e:
        raise ConnectionRefusedError("Invalid token")

    finally:
        db.close()


@sio.event
async def disconnect(sid):
    try:
        session_data = await sio.get_session(sid)
        logger.debug(f"Client disconnected: {session_data}")

        if session_data.get("role") == "host":
            room = session_data.get("room_code")

            if room:
                await sio.emit("host_disconnected",
                               {"message": "Хост покинул игру"},
                               room=room
                               )

            db = next(get_db())
            try:
                session = db.query(AdventureSession).filter_by(
                    join_code=room,
                    host_id=session_data["user_id"]
                ).first()

                if session:
                    db.delete(session)
                    db.commit()
                    logger.info(f"Session {room} deleted")

            except Exception as e:
                logger.error(f"DB cleanup error: {str(e)}")
                db.rollback()
            finally:
                db.close()

        elif session_data.get("role") == "student":
            room = session_data.get("room_code")

            logger.info(f"Выход из комнаты {room}")

            if room:
                await sio.emit("student_left",
                               {"sid": sid},

                               room=room
                               )

        await sio.leave_room(sid, "*")

    except KeyError:
        logger.warning(f"Session data not found for SID: {sid}")
    except Exception as e:
        logger.error(f"Unexpected disconnect error: {str(e)}", exc_info=True)


@sio.on("host_join")
async def host_join(sid, data):
    db = next(get_db())
    try:
        session_data = await sio.get_session(sid)
        if session_data.get("role") != "host":
            raise HostPermissionError()

        logger.info(f" Мир с айдишником {data['world_id']}")

        session = AdventureSession.create(
            db,
            host_id=session_data["user_id"],
            world_id=data["world_id"],
        )

        host_sessions[session.join_code] = sid
        session_data["room_code"] = session.join_code

        steps = generate_steps(session.join_code, db)

        await sio.enter_room(sid, session.join_code)



        await sio.emit("host_ready", {
            "join_code": session.join_code,
            "steps_count": len(steps),
        }, to=sid)

    except IntegrityError as e:
        logger.error(f"Session creation conflict: {e}")
        await sio.emit("error", {
            "message": "Не удалось создать сессию (попробуйте снова)"
        }, to=sid)
        db.rollback()
    except HostPermissionError as e:
        await sio.emit("auth_error", {"message": e.message}, to=sid)
    except Exception as e:
        logger.error(f"Unexpected error in host_join: {e}", exc_info=True)
        await sio.emit("error", {
            "message": "Ошибка при создании игры"
        }, to=sid)
        db.rollback()
    finally:
        db.close()


@sio.on('student_join')
async def student_join(sid, data):
    db = next(get_db())
    try:
        room_code = data.get('room_code')

        if not room_code or len(room_code) != 4:
            raise InvalidCodeError()

        session = db.query(AdventureSession).filter_by(join_code=room_code).first()
        if not session:
            raise SessionNotFoundError()

        await sio.save_session(sid, {
            "role": "student",
            "room_code": room_code,
            "progress": {
                "current_step": 0,
            }
        })

        leaderboard[room_code] = {}
        leaderboard[room_code][sid] = {
            "username" : data.get("username"),
            "score" : 0
        }


        await sio.enter_room(sid, room_code)
        await sio.emit('student_joined', {'message': 'Success'}, to=sid)
        await sio.emit('new_student_joined', {'sid': sid, 'username' : data.get('username')}, room=room_code)

    except ConnectError as e:
        await sio.emit('join_error', {'error': str(e)}, to=sid)
    except Exception as e:
        logger.error(f"Неожиданная ошибка : {e}")
        await sio.emit("error", {"message" : "Внутренняя ошибка сервера"})
    finally:
        db.close()


@sio.on("game_start")
async def game_start(sid, data):
    db = next(get_db())
    try:
        session_data = await sio.get_session(sid)
        if session_data.get("role") != "host":
            await sio.emit("error", {"message": "Только хост может стартовать игру"}, to=sid)
            return

        room = session_data["room_code"]

        # Получаем все шаги игры из БД
        steps = db.query(AdventureStep).filter_by(
            session_id=room
        ).order_by(AdventureStep.step_number).all()

        # Форматируем задания для клиента
        tasks = []
        for step in steps:
            if step.quiz_step:
                tasks.append({
                    "type": "quiz",
                    "step_id": step.id,
                    "step_number": step.step_number,
                    "question": step.quiz_step.question,
                    "options": [{"id": opt.id, "text": opt.text} for opt in step.quiz_step.options]
                })
            elif step.word_order_step:
                tasks.append({
                    "type": "word_order",
                    "step_id": step.id,
                    "step_number": step.step_number,
                    "sentence": step.word_order_step.sentence.sentence.lower(),
                    "words" : step.word_order_step.sentence.sentence.lower().split()
                })

        leaderboard_list = [
            {"sid": sid, "username": data["username"], "score": data["score"]}
            for sid, data in leaderboard[room].items()
        ]

        await sio.emit("game_started",
            tasks, room=room)

        await sio.emit("leaderboard", leaderboard_list, to=sid)

        session_data["isStarted"] = True
        await sio.save_session(sid, session_data)

    except Exception as e:
        logger.error(f"Game start error: {e}", exc_info=True)
        await sio.emit("error", {"message": "Ошибка при старте игры"}, to=sid)
    finally:
        db.close()


@sio.on('check_answer')
async def check_answer(sid, data):
    db = next(get_db())
    print(data)
    session_data = await sio.get_session(sid)
    room_code = session_data["room_code"]

    print([i.step_number for i in db.query(AdventureStep).filter_by(session_id=room_code)])


    step = db.query(AdventureStep).filter_by(
        session_id=room_code,
        step_number=data["step"] + 1
    ).first()

    if not step:
        raise ValueError("Шаг не найден")

    if step.quiz_step:
        correct_option = db.query(QuizOption).filter_by(
                quiz_step_id=step.quiz_step.id,
                is_correct=True
            ).first()
        is_correct = (data['answer'] == correct_option.id)

    else:
        is_correct = (data["answer"] == step.word_order_step.sentence.sentence.lower().split())


    print(is_correct)



    score = calculate_score(is_correct, data["time_spent"])

    print(score)

    leaderboard[room_code][sid]["score"] += score

    host_sid = host_sessions.get(room_code)
    if host_sid:
        leaderboard_list = [
            {"sid": sid, "username": data["username"], "score": data["score"]}
            for sid, data in leaderboard[room_code].items()
        ]
        await sio.emit("leaderboard", leaderboard_list, to=host_sessions[room_code])



    db.close()

