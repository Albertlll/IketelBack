from pydantic import BaseModel
from typing import List, Optional

class WordPreview(BaseModel):
    """Модель для представления слова с переводом"""
    word: str
    translation: str


class MinigamePreview(BaseModel):
    minigameId: str
    title: str
    type: str

class WorldPreview(BaseModel):
    id: int
    title: str
    image: str
    

class WorldDetail(WorldPreview):
    description: Optional[str] = None
    words: List[dict] = []
    id : int
    description : str
    image : str | None = None
    

class WorldCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_public: bool = True