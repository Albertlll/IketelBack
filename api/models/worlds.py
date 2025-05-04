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
    image : Optional[str] = None
    
class SentenceSchema(BaseModel):
    sentence: str

class WorldDetail(WorldPreview):
    description: Optional[str] = None
    words: List[dict] = []
    sentences :  List[dict] = []
    is_public : bool

class WordSchema(BaseModel):
    word: str
    translation: str


class WorldCreate(BaseModel):
    title: str
    description:Optional[str] = None
    is_public: bool = True
    words: list[WordSchema]
    sentences: list[SentenceSchema]
    image : Optional[str] = None
