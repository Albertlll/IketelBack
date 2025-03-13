from pydantic import BaseModel
from typing import List, Optional

class MinigamePreview(BaseModel):
    minigameId: str
    title: str
    image: str
    type: str

class WorldPreview(BaseModel):
    id: int
    title: str
    image: str

class WorldDetail(WorldPreview):
    description: Optional[str] = None
    minigames: List[dict] = []

class WorldCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_public: bool = True