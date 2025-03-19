from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..models.worlds import WorldPreview, WorldDetail, WorldCreate
from db.session import get_db
from db.models import World
from core.security import get_current_user
from db.models import User
from typing import List
from core.file_storage import upload_image

router = APIRouter()

# Демонстрационные данные
demo_worlds = [
    WorldDetail(
        id=1,
        title="Морская экспедиция",
        image="https://c4.wallpaperflare.com/wallpaper/663/620/993/fantasy-ocean-hd-wallpaper-preview.jpg",
        description="Описание морской экспедиции",
        minigames=[
            {"minigameId": "1", "title": "Memory Game", "image": "https://picsum.photos/1920/1080", "type": "game"},
            {"minigameId": "5", "title": "Словарь", "image": "https://picsum.photos/1920/1080", "type": "vocabulary"},
        ]
    )
]

@router.get("/", response_model=List[WorldPreview])
async def get_all_worlds(db: Session = Depends(get_db)):
    # Получаем все публичные миры из базы данных
    public_worlds =  db.query(World).filter(World.is_public == True).all()
    
    # Преобразуем в формат WorldPreview
    return [
        WorldPreview(
            id=world.id,
            title=world.title,
            image=world.image  # Используем image вместо url
        ) 
        for world in public_worlds
    ]

@router.get("/{world_id}", response_model=WorldDetail)
async def get_world(world_id: int, db: Session = Depends(get_db)):
    # Получаем мир из базы данных
    world = db.query(World).filter(
        World.id == world_id,
        World.is_public == True
    ).first()
    
    if not world:
        raise HTTPException(status_code=404, detail="Мир не найден")
    
    # Преобразуем в формат WorldDetail
    return WorldDetail(
        id=world.id,
        title=world.title,
        image=world.image,  # Используем image вместо url
        description=world.description,
        minigames=[]  # Здесь нужно будет добавить загрузку игр из базы данных
    )

@router.post("/", response_model=WorldDetail)
async def create_world(
    title: str = Form(...),
    description: str = Form(None),
    is_public: bool = Form(True),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        # Загружаем изображение
        image_url = await upload_image(image)
        
        # Создаем запись в БД
        db_world = World(
            title=title,
            description=description,
            image=image_url,
            is_public=is_public,
            author_id=current_user.id
        )
        
        db.add(db_world)
        db.commit()
        db.refresh(db_world)
        
        return WorldDetail(
            id=db_world.id,
            title=db_world.title,
            image=image_url,
            description=db_world.description,
            minigames=[]
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось создать мир: {str(e)}"
        )