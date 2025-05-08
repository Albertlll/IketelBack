from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from api.models.worlds import WorldPreview, WorldDetail, WorldCreate
from db.session import get_db
from db.models import World, Word, Sentence
from core.security import get_current_user
from db.models import User
from typing import List
from core.file_storage import upload_image, upload_base64
from pydantic import BaseModel
import json
from sqlalchemy import and_

router = APIRouter()

class PostAnsw(BaseModel):
    stri : str

@router.get("/", response_model=List[WorldPreview])
async def get_all_worlds(db: Session = Depends(get_db)):
    """Список всех публичных мирков"""
    public_worlds =  db.query(World).all()
    
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
async def get_world(world_id: int, db: Session = Depends(get_db)):
    """Получить конкретный мир по ID"""
    world = db.query(World).filter(  and_(
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

    print(world.sentences)

    return WorldDetail(
        id=world.id,
        title=world.title,
        description=world.description,
        words=words_list,
        image=world.image,
        sentences=sentences_list,
        is_public=world.is_public
    )


@router.post("/", response_model=str)
async def create_world(
    world_data: WorldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):


    image_url = await upload_base64(world_data.image)
    # Создаем мир
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

    # Добавляем слова
    for word in world_data.words:
        db.add(Word(
            word=word.word,
            translation=word.translation,
            world_id=db_world.id
        ))

    # Добавляем предложения
    for sentence in world_data.sentences:
        db.add(Sentence(
            sentence=sentence.sentence,
            world_id=db_world.id
        ))

    db.commit()

    return "имба"