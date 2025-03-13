from fastapi import APIRouter, HTTPException
from ..models.games import VocabularyGame, SelectVariantGame
from typing import Union 

router = APIRouter()

# Демонстрационные данные
demo_games = [
    {"minigameId": "5", **VocabularyGame(vocabulary=[{"word": "Алма", "translation": "Яблоко"}]).dict()},
    {"minigameId": "6", **SelectVariantGame(question="Выберите правильный перевод слова 'Яблоко'", variants=[{"title": "Алма"}]).dict()}
]

@router.get("/{game_id}", response_model=Union[VocabularyGame, SelectVariantGame])
async def get_game(game_id: str):
    for game in demo_games:
        if game.get("minigameId") == game_id:
            return game
    raise HTTPException(status_code=404, detail="Игра не найдена")