from pydantic import BaseModel

class Card(BaseModel):
    term: str
    definition: str