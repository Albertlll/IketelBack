import random
from db.models import World
from db.session import get_db
from sqlalchemy.orm import Session
from fastapi import  Depends

def generate_games(world_id: int, settings: dict,  db: Session = Depends(get_db)):
    """Генерирует последовательность игр"""
    world = db.query(World).get(world_id)
    words = world.words
    
    games = []
    for _ in range(settings["game_count"]):
        game_type = random.choice(settings["types"])
        
        if game_type == "translate":
            word = random.choice(words)
            games.append({
                "type": "translate",
                "word": word.word,
                "correct": word.translation
            })
            
        elif game_type == "multiple_choice":
            word = random.choice(words)
            other_words = random.sample(
                [w for w in words if w.id != word.id], 3
            )
            games.append({
                "type": "multiple_choice",
                "question": f"Переведите: {word.word}",
                "correct": word.translation,
                "options": [
                    word.translation,
                    *[w.translation for w in other_words]
                ]
            })
    
    return games