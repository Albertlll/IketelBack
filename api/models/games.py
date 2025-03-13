from pydantic import BaseModel
from typing import List, Dict

class VocabularyGame(BaseModel):
    type: str = "vocabulary"
    vocabulary: List[Dict[str, str]]

class SelectVariantGame(BaseModel):
    type: str = "select-variant"
    question: str
    variants: List[Dict[str, str]]