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
steps_count_by_room = {}
started_rooms = set()


def calculate_score(is_correct: bool, time_spent: float, base_points=100) -> int:
    if not is_correct:
        return 0

    max_time = 30.0
    time_factor = min(max_time, time_spent) / max_time
    return int(base_points * (1 - time_factor))  # От 100 до 0


def _get_steps_count(room_code: str, db: Session) -> int:
    cached = steps_count_by_room.get(room_code)
    if cached:
        return cached
    count = db.query(AdventureStep).filter_by(session_id=room_code).count()
    steps_count_by_room[room_code] = count
    return count


def _sorted_leaderboard(room_code: str):
    entries = leaderboard.get(room_code, {})
    data = [
        {"sid": s, "username": d.get("username"), "score": d.get("score", 0)}
        for s, d in entries.items()
    ]
    return sorted(data, key=lambda x: x["score"], reverse=True)


def _top3(room_code: str):
    data = _sorted_leaderboard(room_code)
    return [
        {"place": idx + 1, "username": item.get("username"), "score": item.get("score", 0)}
        for idx, item in enumerate(data[:3])
    ]


async def _maybe_finish_game(room_code: str):
    entries = leaderboard.get(room_code, {})
    if not entries:
        return
    if not all(d.get("finished") for d in entries.values()):
        return

    host_sid = host_sessions.get(room_code)
    if host_sid:
        await sio.emit(
            "game_finished",
            {"top3": _top3(room_code), "total_players": len(entries)},
            to=host_sid,
        )
    leaderboard.pop(room_code, None)
    steps_count_by_room.pop(room_code, None)



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
        super().__init__("Не удалось создать сессию. Попробуйте снова")

class GameAlreadyStartedError(ConnectError):
    def __init__(self):
        super().__init__("Игра уже началась")


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
            "isStarted": False
        })

    except Exception:
        raise ConnectionRefusedError("Invalid token")

    finally:
        db.close()


@sio.event
async def disconnect(sid):
    try:
        session_data = await sio.get_session(sid)
        logger.debug(f"Client disconnected: {session_data}")

        role = session_data.get("role")
        room = session_data.get("room_code")

        if role == "host" and room:
            await sio.emit("host_disconnected", {"message": "Хост покинул игру"}, room=room)

            db = next(get_db())
            try:
                session = db.query(AdventureSession).filter_by(
                    join_code=room,
                    host_id=session_data.get("user_id")
                ).first()

                if session:
                    db.delete(session)
                    db.commit()
                    logger.info(f"Session {room} deleted")
                leaderboard.pop(room, None)
                steps_count_by_room.pop(room, None)
                started_rooms.discard(room)

            except Exception as e:
                logger.error(f"DB cleanup error: {str(e)}")
                db.rollback()
            finally:
                db.close()

        elif role == "student" and room:
            logger.info(f"Выход из комнаты {room}")
            await sio.emit("student_left", {"sid": sid}, room=room)
            if room in leaderboard:
                leaderboard[room].pop(sid, None)
                await _maybe_finish_game(room)

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

        world_id = data.get("world_id")
        if not isinstance(world_id, int):
            await sio.emit("error", {"message": "Некорректный world_id"}, to=sid)
            return

        session = AdventureSession.create(
            db,
            host_id=session_data["user_id"],
            world_id=world_id,
        )

        host_sessions[session.join_code] = sid
        session_data["room_code"] = session.join_code

        steps = generate_steps(session.join_code, db)
        steps_count_by_room[session.join_code] = len(steps)
        await sio.enter_room(sid, session.join_code)

        await sio.emit("host_ready", {
            "join_code": session.join_code,
            "steps_count": len(steps),
        }, to=sid)

    except IntegrityError as e:
        logger.error(f"Session creation conflict: {e}")
        await sio.emit("error", {"message": e.message}, to=sid)
        db.rollback()
    except HostPermissionError as e:
        await sio.emit("auth_error", {"message": e.message}, to=sid)
    except Exception as e:
        logger.error(f"Unexpected error in host_join: {e}", exc_info=True)
        await sio.emit("error", {"message": "Ошибка при создании игры"}, to=sid)
        db.rollback()
    finally:
        db.close()


@sio.on('student_join')
async def student_join(sid, data):
    db = next(get_db())
    try:
        room_code = (data or {}).get('room_code')

        if not room_code or not isinstance(room_code, str) or len(room_code) != 4:
            raise InvalidCodeError()

        session = db.query(AdventureSession).filter_by(join_code=room_code).first()
        if not session:
            raise SessionNotFoundError()

        if room_code in started_rooms:
            raise GameAlreadyStartedError()

        await sio.save_session(sid, {
            "role": "student",
            "room_code": room_code,
            "progress": {"current_step": 0}
        })

        if room_code not in leaderboard:
            leaderboard[room_code] = {}
        leaderboard[room_code][sid] = {
            "username": (data or {}).get("username"),
            "score": 0,
            "finished": False,
        }

        await sio.enter_room(sid, room_code)
        await sio.emit('student_joined', {'message': 'Success'}, to=sid)
        await sio.emit('new_student_joined', {'sid': sid, 'username': (data or {}).get('username')}, room=room_code)

    except ConnectError as e:
        await sio.emit('join_error', {'error': str(e)}, to=sid)
    except Exception as e:
        logger.error(f"Неожиданная ошибка : {e}")
        await sio.emit("error", {"message": "Внутренняя ошибка сервера"})
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

        room = session_data.get("room_code")
        if not room:
            await sio.emit("error", {"message": "Комната не найдена"}, to=sid)
            return

        steps = db.query(AdventureStep).filter_by(
            session_id=room
        ).order_by(AdventureStep.step_number).all()

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
                sentence_text = (step.word_order_step.sentence.sentence or "").lower()
                tasks.append({
                    "type": "word_order",
                    "step_id": step.id,
                    "step_number": step.step_number,
                    "sentence": sentence_text,
                    "words": sentence_text.split()
                })

        if room not in leaderboard:
            leaderboard[room] = {}
        leaderboard_list = [
            {"sid": s, "username": d.get("username"), "score": d.get("score", 0)}
            for s, d in leaderboard[room].items()
        ]

        await sio.emit("game_started", tasks, room=room)
        await sio.emit("leaderboard", leaderboard_list, to=sid)

        started_rooms.add(room)

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
    try:
        session_data = await sio.get_session(sid)
        room_code = session_data.get("room_code")
        if not room_code:
            await sio.emit("error", {"message": "Комната не найдена"}, to=sid)
            return

        step_index = (data or {}).get("step")
        if not isinstance(step_index, int):
            await sio.emit("error", {"message": "Некорректный шаг"}, to=sid)
            return

        step = db.query(AdventureStep).filter_by(
            session_id=room_code,
            step_number=step_index + 1
        ).first()

        if not step:
            await sio.emit("error", {"message": "Шаг не найден"}, to=sid)
            return

        is_correct = False
        if step.quiz_step:
            answer = (data or {}).get('answer')
            if not isinstance(answer, int):
                await sio.emit("error", {"message": "Некорректный ответ"}, to=sid)
                return
            correct_option = db.query(QuizOption).filter_by(
                quiz_step_id=step.quiz_step.id,
                is_correct=True
            ).first()
            is_correct = (answer == (correct_option.id if correct_option else None))
        else:
            expected = (step.word_order_step.sentence.sentence or "").lower().split()
            answer = (data or {}).get("answer")
            if not isinstance(answer, list):
                await sio.emit("error", {"message": "Некорректный ответ"}, to=sid)
                return
            is_correct = (answer == expected)

        time_spent = float((data or {}).get("time_spent", 0.0))
        score = calculate_score(is_correct, time_spent)

        if room_code not in leaderboard:
            leaderboard[room_code] = {}
        if sid not in leaderboard[room_code]:
            leaderboard[room_code][sid] = {"username": None, "score": 0, "finished": False}
        leaderboard[room_code][sid]["score"] += score

        host_sid = host_sessions.get(room_code)
        if host_sid:
            leaderboard_list = [
                {"sid": s, "username": d.get("username"), "score": d.get("score", 0)}
                for s, d in leaderboard[room_code].items()
            ]
            await sio.emit("leaderboard", leaderboard_list, to=host_sid)

        steps_count = _get_steps_count(room_code, db)
        if step_index + 1 >= steps_count:
            leaderboard[room_code][sid]["finished"] = True
            sorted_board = _sorted_leaderboard(room_code)
            place = next(
                (idx + 1 for idx, item in enumerate(sorted_board) if item.get("sid") == sid),
                len(sorted_board),
            )
            await sio.emit(
                "game_finished",
                {
                    "score": leaderboard[room_code][sid]["score"],
                    "place": place,
                    "total_players": len(sorted_board),
                },
                to=sid,
            )
            await _maybe_finish_game(room_code)

    except Exception as e:
        logger.error(f"check_answer error: {e}", exc_info=True)
        await sio.emit("error", {"message": "Ошибка при проверке ответа"}, to=sid)
    finally:
        db.close()
