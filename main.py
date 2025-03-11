import ssl
import socketio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Union
from pydantic import BaseModel
import uvicorn

# Создаем Socket.IO сервер с CORS
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")

# FastAPI приложение
app = FastAPI(
    title="Language Learning App API",
    description="API для обучающего приложения по языкам"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Определяем модели данных
class VocabularyGame(BaseModel):
    type: str = "vocabulary"
    vocabulary: List[dict]  # Список словарных слов и их переводов

class SelectVariantGame(BaseModel):
    type: str = "select-variant"
    question: str
    variants: List[dict]  # Список вариантов ответа

class MinigamePreview(BaseModel):
    minigameId: str
    title: str
    image: str
    type: str

class WorldPreview(BaseModel):
    id: int
    title: str
    url: str

class WorldDetail(WorldPreview):
    minigames: List[MinigamePreview]

class Card(BaseModel):
    term: str
    definition: str

# Демонстрационные данные
example_vocabulary_content = {
    "vocabulary": [
        {"word": "Алма", "translation": "Яблоко"},
        {"word": "Банан", "translation": "Банан"},
    ]
}

example_select_variant_content = {
    "question": "Выберите правильный перевод слова 'Яблоко'",
    "variants": [
        {"title": "Алма"},
        {"title": "Банан"},
        {"title": "Груша"},
    ]
}

demo_games = [
    {"minigameId": "5", **VocabularyGame(vocabulary=example_vocabulary_content["vocabulary"]).dict()},
    {"minigameId": "6", **SelectVariantGame(**example_select_variant_content).dict()}
]

demo_worlds = [
    WorldDetail(
        id=1,
        title="Морская экспедиция",
        url="https://c4.wallpaperflare.com/wallpaper/663/620/993/fantasy-ocean-hd-wallpaper-preview.jpg",
        minigames=[
            MinigamePreview(minigameId="1", title="Memory Game", image="https://picsum.photos/1920/1080", type="game"),
            MinigamePreview(minigameId="5", title="Словарь", image="https://picsum.photos/1920/1080", type="vocabulary"),
        ]
    )
]

cards_db = [
    {"term": "Алма", "definition": "Яблоко"},
    {"term": "Банан", "definition": "Банан"},
]

# Эндпоинты API
@app.get("/worlds", response_model=List[WorldPreview])
async def get_all_worlds():
    return [WorldPreview(id=w.id, title=w.title, url=w.url) for w in demo_worlds]

@app.get("/worlds/{world_id}", response_model=WorldDetail)
async def get_world(world_id: int):
    for world in demo_worlds:
        if world.id == world_id:
            return world
    raise HTTPException(status_code=404, detail="Мир не найден")

@app.get("/games/{game_id}", response_model=Union[VocabularyGame, SelectVariantGame])
async def get_game(game_id: str):
    for game in demo_games:
        if game.get("minigameId") == game_id:
            return game
    raise HTTPException(status_code=404, detail="Игра не найдена")

@app.get("/cards", response_model=List[Card])
async def get_cards():
    return cards_db

@app.post("/cards", response_model=Card)
async def add_card(card: Card):
    cards_db.append(card.dict())
    await sio.emit("new_card", card.dict())  
    return card

# Socket.IO события
@sio.event
async def connect(sid, environ):
    print(f"Клиент {sid} подключился")
    await sio.emit("welcome", {"message": "Добро пожаловать!"}, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Клиент {sid} отключился")

# Объединяем FastAPI и Socket.IO
asgi_app = socketio.ASGIApp(sio, other_asgi_app=app)

# Запуск сервера с SSL  ssl_keyfile="ssl/server-key.key",  ssl_certfile="ssl/server-cert.crt"
if __name__ == "__main__":
    uvicorn.run(asgi_app, host="0.0.0.0", port=8000)