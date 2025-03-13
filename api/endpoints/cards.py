from fastapi import APIRouter
from ..models.cards import Card

router = APIRouter()

cards_db = [
    {"term": "Алма", "definition": "Яблоко"},
    {"term": "Банан", "definition": "Банан"},
]

@router.get("/", response_model=list[Card])
async def get_cards():
    return cards_db

@router.post("/", response_model=Card)
async def add_card(card: Card):
    cards_db.append(card.dict())
    return card