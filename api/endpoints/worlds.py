from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..models.worlds import WorldPreview, WorldDetail, WorldCreate, WordPreview
from db.session import get_db
from db.models import World, Word
from core.security import get_current_user
from db.models import User
from typing import List
from core.file_storage import upload_image
from pydantic import BaseModel
import json
from sqlalchemy import and_

router = APIRouter()

class PostAnsw(BaseModel):
    stri : str

@router.get("/", response_model=List[WorldPreview])
async def get_all_worlds(db: Session = Depends(get_db)):
    public_worlds =  db.query(World).all()
    
    return [
        WorldPreview(
            id=world.id,
            title=world.title,
            image=world.image
        ) 
        for world in public_worlds
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
    
    return WorldDetail(
        id=world.id,
        title=world.title,
        description=world.description,
        words=words_list,
        image=world.image
    )



@router.post("/", response_model=str)
async def create_world(
    title: str = Form(...),
    description: str = Form(None),
    is_public: bool = Form(True),
    words: str = Form(...),
    db: Session = Depends(get_db),
    # current_user: User = Depends(get_current_user)
):
    try:
        # Парсим JSON-строку в список слов
        words_data = json.loads(words)
        
        # Создаем запись в БД
        db_world = World(
            title=title,
            description=description,
            is_public=is_public,
            author_id=4
        )
        
        db.add(db_world)
        db.commit()
        db.refresh(db_world)
        
        # Создаем список для хранения объектов Word
        db_words = []
        
        
        # Добавляем слова в базу данных
        for word_data in words_data:
            db_word = Word(
                word=word_data["word"],
                translation=word_data["translation"],
                world_id=db_world.id
            )
            db.add(db_word)
            db_words.append(db_word)
        
        db.commit()
        
        return"успех успех успех"
    except Exception as e:
        db.rollback()
        print(f"Ошибка при создании мира: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось создать мир: {str(e)}"
        )