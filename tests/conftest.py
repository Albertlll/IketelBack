import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Добавляем корневую директорию проекта в sys.path для корректного импорта модулей
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import User, World, Word, Sentence, AdventureSession, AdventureStep, QuizStep, QuizOption


@pytest.fixture
def mock_db():
    """Фикстура для мокирования базы данных"""
    db = MagicMock()
    return db


@pytest.fixture
def mock_user():
    """Фикстура для мокирования пользователя"""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "TestUser"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_world():
    """Фикстура для мокирования мира"""
    world = MagicMock(spec=World)
    world.id = 1
    world.title = "Тестовый мир"
    world.description = "Описание тестового мира"
    return world


@pytest.fixture
def mock_words():
    """Фикстура для мокирования слов"""
    word1 = MagicMock(spec=Word)
    word1.id = 1
    word1.word = "Алма"
    word1.translation = "Яблоко"
    
    word2 = MagicMock(spec=Word)
    word2.id = 2
    word2.word = "Су"
    word2.translation = "Вода"
    
    word3 = MagicMock(spec=Word)
    word3.id = 3
    word3.word = "Нан"
    word3.translation = "Хлеб"
    
    return [word1, word2, word3]


@pytest.fixture
def mock_sentences():
    """Фикстура для мокирования предложений"""
    sentence1 = MagicMock(spec=Sentence)
    sentence1.id = 1
    sentence1.sentence = "Мен алма жеймін"
    
    sentence2 = MagicMock(spec=Sentence)
    sentence2.id = 2
    sentence2.sentence = "Мен су ішемін"
    
    return [sentence1, sentence2]


@pytest.fixture
def mock_session():
    """Фикстура для мокирования сессии приключения"""
    session = MagicMock(spec=AdventureSession)
    session.join_code = "ABCD"
    return session


@pytest.fixture
def mock_step():
    """Фикстура для мокирования шага приключения"""
    step = MagicMock(spec=AdventureStep)
    step.id = 1
    step.session_id = "ABCD"
    step.step_number = 1
    return step


@pytest.fixture
def mock_quiz_step(mock_step):
    """Фикстура для мокирования шага викторины"""
    quiz_step = MagicMock(spec=QuizStep)
    quiz_step.id = mock_step.id
    quiz_step.question = "Переведите: Алма"
    
    # Создаем варианты ответов
    correct_option = MagicMock(spec=QuizOption)
    correct_option.id = 1
    correct_option.text = "Яблоко"
    correct_option.is_correct = True
    
    wrong_option1 = MagicMock(spec=QuizOption)
    wrong_option1.id = 2
    wrong_option1.text = "Вода"
    wrong_option1.is_correct = False
    
    wrong_option2 = MagicMock(spec=QuizOption)
    wrong_option2.id = 3
    wrong_option2.text = "Хлеб"
    wrong_option2.is_correct = False
    
    quiz_step.options = [correct_option, wrong_option1, wrong_option2]
    
    # Связываем с шагом
    mock_step.quiz_step = quiz_step
    
    return quiz_step