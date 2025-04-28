import random
from db.models import World, AdventureStep
from db.session import get_db
from sqlalchemy.orm import Session
from fastapi import  Depends
def generate_steps(session_id: str, world_id: int, settings: dict, db: Session = Depends(get_db)):
    world = db.query(World).get(world_id)
    words = world.words
    steps = []
    
    for i in range(1, settings["game_count"] + 1):
        step_type = random.choice(["word_translation", "multiple_choice"])
        word = random.choice(words)
        
        if step_type == "word_translation":
            steps.append(
                AdventureStep(
                    session_id=session_id,
                    step_number=i,
                    type="word_translation",
                    content={
                        "word": word.word,
                        "correct": word.translation
                    }
                )
            )
        
        elif step_type == "multiple_choice":
            other_words = random.sample(
                [w for w in words if w.id != word.id], 3
            )
            steps.append(
                AdventureStep(
                    session_id=session_id,
                    step_number=i,
                    type="multiple_choice",
                    content={
                        "question": f"Переведите: {word.word}",
                        "options": [
                            {"id": 1, "text": word.translation},
                            *[{"id": i+2, "text": w.translation} for i, w in enumerate(other_words)]
                        ],
                        "correct_id": 1
                    }
                )
            )
    
    return steps