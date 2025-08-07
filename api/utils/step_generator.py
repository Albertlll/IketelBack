import random
from db.models import AdventureSession, AdventureStep, QuizStep, WordOrderStep, QuizOption
from db.session import get_db
from sqlalchemy.orm import Session
from fastapi import Depends


def generate_steps(session_id: str, db: Session = Depends(get_db)):
    """
    Генерирует шаги приключения для указанной сессии.
    """
    # Получаем сессию и связанный мир
    session = db.get(AdventureSession, session_id)
    if not session:
        raise ValueError("Сессия не найдена")

    world = session.world
    words = world.words
    sentences = world.sentences

    steps = []

    has_sentences = bool(sentences)

    for step_number in range(1, 10):  # 9 шагов - магическое число!
        if has_sentences:
            step_type = random.choice(["quiz", "word_order"])
        else:
            step_type = "quiz"

        if step_type == "quiz":
            # Создаём шаг викторины
            word = random.choice(words)

            # Основной шаг
            step = AdventureStep(
                session_id=session_id,
                step_number=step_number
            )
            db.add(step)
            db.flush()  # Чтобы получить ID для связи

            # Детали викторины
            quiz = QuizStep(
                id=step.id,
                question=f"Переведите: {word.word}"
            )
            db.add(quiz)

            # Варианты ответов
            correct_option = QuizOption(
                quiz_step_id=quiz.id,
                text=word.translation,
                is_correct=True
            )
            db.add(correct_option)

            # 3 случайных неправильных варианта
            candidates = [w for w in words if w.id != word.id]
            for wrong_word in random.sample(candidates, k=min(3, len(candidates))):
                db.add(QuizOption(
                    quiz_step_id=quiz.id,
                    text=wrong_word.translation,
                    is_correct=False
                ))

            steps.append(step)

        elif step_type == "word_order":
            # Создаём шаг сбора предложения
            sentence = random.choice(sentences)

            # Основной шаг
            step = AdventureStep(
                session_id=session_id,
                step_number=step_number
            )
            db.add(step)
            db.flush()

            # Детали шага
            db.add(WordOrderStep(
                id=step.id,
                sentence_id=sentence.id,
            ))

            steps.append(step)

    db.commit()
    return steps