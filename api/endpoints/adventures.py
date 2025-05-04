from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import AdventureSession, User
from core.security import get_current_user
from api.utils.step_generator import generate_steps

router = APIRouter()


class AdventureCreateRequest(BaseModel):
    world_id: int


@router.post("/")
async def create_adventure(
        request_data: AdventureCreateRequest,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user)
):
    """
    Создаёт новую игровую сессию, используя встроенный генератор кодов из модели.
    """
    try:
        # Используем встроенный метод create из модели
        session = AdventureSession.create(
            db,
            world_id=request_data.world_id,
            host_id=user.id
        )

        # Генерируем шаги (передаём join_code вместо session.id)
        steps = generate_steps(session.join_code, db)
        db.add_all(steps)
        db.commit()

        return {
            "join_code": session.join_code,
            "steps_count": len(steps),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))