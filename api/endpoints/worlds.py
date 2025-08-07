from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from api.models.worlds import WorldPreview, WorldDetail, WorldCreate
from db.session import get_db
from db.models import World, Word, Sentence, User
from core.security import get_current_user, get_current_user_optional
from typing import List, Optional
from core.file_storage import upload_base64
from pydantic import BaseModel
from sqlalchemy import and_

router = APIRouter()

class PostAnsw(BaseModel):
    stri : str

@router.get("/", response_model=List[WorldPreview])
async def get_all_worlds(db: Session = Depends(get_db)):
    """Список всех публичных мирков"""
    public_worlds = db.query(World).filter(World.is_public == True).all()
    return [
        WorldPreview(
            id=world.id,
            title=world.title,
            image=world.image
        ) 
        for world in public_worlds
    ]


@router.get("/userWorlds", response_model=List[WorldPreview])
async def get_user_worlds(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Получить все мирки текущего пользователя"""
    user_worlds = db.query(World).filter(World.author_id == current_user.id).all()

    return [
        WorldPreview(
            id=world.id,
            title=world.title,
            image=world.image
        )
        for world in user_worlds
    ]


@router.get("/{world_id}", response_model=WorldDetail)
async def get_world(world_id: int,
                    db: Session = Depends(get_db),
                    current_user: Optional[User] = Depends(get_current_user_optional)):
    """Получить конкретный мир по ID"""
    world = db.query(World).filter(and_(
        World.id == world_id,
        World.is_public == True
    )).first()

    if not world:
        raise HTTPException(status_code=404, detail="Мир не найден")

    words_list = [
        {
            "id": word.id,
            "word": word.word,
            "translation": word.translation,
            "world_id": word.world_id
        }
        for word in world.words
    ]

    sentences_list = [
        {
            "id": sentence.id,
            "sentence": sentence.sentence,
            "world_id": sentence.world_id
        }
        for sentence in world.sentences
    ]

    is_owner = current_user is not None and world.author_id == current_user.id

    return WorldDetail(
        id=world.id,
        title=world.title,
        description=world.description,
        words=words_list,
        image=world.image,
        sentences=sentences_list,
        is_public=world.is_public,
        is_owner=is_owner
    )


@router.post("/", response_model=str)
async def create_world(
    world_data: WorldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if world_data.image and world_data.image != "None":
        image_url = await upload_base64(world_data.image)
    else:
        image_url = None

    db_world = World(
        title=world_data.title,
        description=world_data.description,
        is_public=world_data.is_public,
        author_id=current_user.id,
        image=image_url
    )
    db.add(db_world)
    db.commit()
    db.refresh(db_world)

    for word in world_data.words:
        db.add(Word(
            word=word.word,
            translation=word.translation,
            world_id=db_world.id
        ))

    for sentence in world_data.sentences:
        db.add(Sentence(
            sentence=sentence.sentence,
            world_id=db_world.id
        ))

    db.commit()

    return "Мир успешно создан!"


@router.delete("/{world_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_world(
        world_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Удаление мирка по ID"""
    db_world = db.query(World).filter(
        and_(
            World.id == world_id,
            World.author_id == current_user.id
        )
    ).first()

    if not db_world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мир не найден или у вас нет прав на его удаление"
        )

    db.query(Word).filter(Word.world_id == world_id).delete()
    db.query(Sentence).filter(Sentence.world_id == world_id).delete()

    db.delete(db_world)
    db.commit()

    return "Мир успешно удален"


@router.put("/{world_id}", response_model=str)
async def update_world(
        world_id: int,
        world_data: WorldCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """Обновить мирок"""
    world = db.query(World).filter(World.id == world_id).first()

    if not world:
        raise HTTPException(status_code=404, detail="Мир не найден")

    if world.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    world.title = world_data.title
    world.description = world_data.description
    world.is_public = world_data.is_public

    if world_data.image and world_data.image != "None":
        world.image = await upload_base64(world_data.image)

    db.query(Word).filter(Word.world_id == world_id).delete()
    db.query(Sentence).filter(Sentence.world_id == world_id).delete()

    for word in world_data.words:
        db.add(Word(
            word=word.word,
            translation=word.translation,
            world_id=world.id
        ))

    for sentence in world_data.sentences:
        db.add(Sentence(
            sentence=sentence.sentence,
            world_id=world.id
        ))

    db.commit()

    return "Мир успешно обновлен"


@router.patch(
    "/{world_id}/visibility",
    summary="Изменить публичность мира"
)
async def update_world_visibility(
        world_id: int,
        is_public: bool,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """
    Изменяет статус публичности мира (is_public)

    - world_id: ID мира для изменения
    - is_public: Новый статус публичности (True/False)
    """

    world = db.query(World).filter(World.id == world_id).first()

    if not world:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Мир не найден"
        )

    if world.author_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для изменения этого мира"
        )

    world.is_public = is_public
    db.commit()
    db.refresh(world)

    return world