
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User, AdventureSession
from core.security import get_current_user
import uuid
from api.utils.step_generator import generate_steps

router = APIRouter()


@router.post("/api/adventures")
async def create_adventure(
    world_id: int,
    settings: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    session = AdventureSession(
        id=str(uuid.uuid4()),
        world_id=world_id,
        host_id=user.id,
        settings=settings
    )
    db.add(session)
    db.flush()  # Чтобы получить session.id

    # Генерируем шаги
    steps = generate_steps(session.id, world_id, settings, db)
    db.add_all(steps)
    db.commit()
    
    return {"session_id": session.id}
