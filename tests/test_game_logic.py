import pytest
import random
import uuid
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

# Импортируем функции и классы, которые будем тестировать
from api.sockets.events import calculate_score
from api.utils.game_generator import generate_games
from api.utils.step_generator import generate_steps
from db.models import AdventureSession, World, Word, Sentence, User, AdventureStep, QuizStep, QuizOption


class TestCalculateScore:
    """Тесты для функции подсчета очков игрока"""
    
    def test_calculate_score_correct_answer(self):
        """Тест подсчета очков при правильном ответе"""
        # Правильный ответ, минимальное время (0 секунд) - максимальные очки
        score = calculate_score(is_correct=True, time_spent=0.0)
        assert score == 100
        
        # Правильный ответ, среднее время (15 секунд) - половина очков
        score = calculate_score(is_correct=True, time_spent=15.0)
        assert score == 50
        
        # Правильный ответ, максимальное время (30 секунд) - минимальные очки
        score = calculate_score(is_correct=True, time_spent=30.0)
        assert score == 0
        
        # Правильный ответ, время больше максимального - минимальные очки
        score = calculate_score(is_correct=True, time_spent=45.0)
        assert score == 0
    
    def test_calculate_score_incorrect_answer(self):
        """Тест подсчета очков при неправильном ответе"""
        # Неправильный ответ всегда дает 0 очков, независимо от времени
        score = calculate_score(is_correct=False, time_spent=0.0)
        assert score == 0
        
        score = calculate_score(is_correct=False, time_spent=15.0)
        assert score == 0
        
        score = calculate_score(is_correct=False, time_spent=30.0)
        assert score == 0
    
    def test_calculate_score_custom_base_points(self):
        """Тест подсчета очков с пользовательским базовым значением"""
        # Правильный ответ, минимальное время, базовые очки = 200
        score = calculate_score(is_correct=True, time_spent=0.0, base_points=200)
        assert score == 200
        
        # Правильный ответ, среднее время, базовые очки = 200
        score = calculate_score(is_correct=True, time_spent=15.0, base_points=200)
        assert score == 100


class TestGameGenerator:
    """Тесты для генератора игр"""
    
    @patch('api.utils.game_generator.get_db')
    def test_generate_games(self, mock_get_db):
        """Тест генерации игр"""
        # Создаем моки для базы данных и запросов
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Создаем мок для мира и слов
        mock_world = MagicMock(spec=World)
        mock_word1 = MagicMock(spec=Word)
        mock_word1.id = 1
        mock_word1.word = "Алма"
        mock_word1.translation = "Яблоко"
        
        mock_word2 = MagicMock(spec=Word)
        mock_word2.id = 2
        mock_word2.word = "Су"
        mock_word2.translation = "Вода"
        
        mock_world.words = [mock_word1, mock_word2]
        mock_db.query.return_value.get.return_value = mock_world
        
        # Настраиваем random.choice и random.sample для предсказуемых результатов
        with patch('random.choice', side_effect=lambda x: x[0]), \
             patch('random.sample', side_effect=lambda population, k: population[:k]):
            
            # Тестируем генерацию игр
            settings = {
                "game_count": 2,
                "types": ["translate", "multiple_choice"]
            }
            
            games = generate_games(world_id=1, settings=settings, db=mock_db)
            
            # Проверяем результаты
            assert len(games) == 2
            
            # Проверяем первую игру (тип "translate")
            assert games[0]["type"] == "translate"
            assert games[0]["word"] == "Алма"
            assert games[0]["correct"] == "Яблоко"
            
            # Проверяем вторую игру (тип "multiple_choice")
            assert games[1]["type"] == "multiple_choice"
            assert games[1]["question"] == "Переведите: Алма"
            assert games[1]["correct"] == "Яблоко"
            assert "Яблоко" in games[1]["options"]


class TestAdventureSession:
    """Тесты для класса AdventureSession"""
    
    def test_generate_code(self):
        """Тест генерации кода сессии"""
        # Проверяем, что генерируется код правильной длины
        code = AdventureSession._generate_code()
        assert len(code) == 4
        
        # Проверяем, что код содержит только допустимые символы
        allowed_chars = set(AdventureSession._CODE_CHARS)
        for char in code:
            assert char in allowed_chars
    
    @patch('db.models.AdventureSession._generate_code')
    def test_create_session(self, mock_generate_code):
        """Тест создания сессии"""
        # Настраиваем мок для генерации кода
        mock_generate_code.return_value = "ABCD"
        
        # Создаем мок для базы данных
        mock_db = MagicMock()
        
        # Создаем мок для хоста и мира
        mock_host = MagicMock(spec=User)
        mock_host.id = 1
        
        mock_world = MagicMock(spec=World)
        mock_world.id = 1
        
        # Тестируем создание сессии
        session = AdventureSession.create(
            db=mock_db,
            host_id=mock_host.id,
            world_id=mock_world.id
        )
        
        # Проверяем результаты
        assert session.join_code == "ABCD"
        assert session.host_id == mock_host.id
        assert session.world_id == mock_world.id
        
        # Проверяем, что сессия была добавлена в базу данных и коммит был выполнен
        mock_db.add.assert_called_once_with(session)
        mock_db.commit.assert_called_once()


class TestStepGenerator:
    """Тесты для генератора шагов"""
    
    @patch('api.utils.step_generator.get_db')
    def test_generate_steps(self, mock_get_db):
        """Тест генерации шагов приключения"""
        # Создаем моки для базы данных и запросов
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        
        # Создаем мок для сессии, мира, слов и предложений
        mock_session = MagicMock(spec=AdventureSession)
        mock_session.id = "ABCD"
        
        mock_world = MagicMock(spec=World)
        
        mock_word1 = MagicMock(spec=Word)
        mock_word1.id = 1
        mock_word1.word = "Алма"
        mock_word1.translation = "Яблоко"
        
        mock_word2 = MagicMock(spec=Word)
        mock_word2.id = 2
        mock_word2.word = "Су"
        mock_word2.translation = "Вода"
        
        mock_sentence = MagicMock(spec=Sentence)
        mock_sentence.id = 1
        mock_sentence.sentence = "Мен алма жеймін"
        
        mock_world.words = [mock_word1, mock_word2]
        mock_world.sentences = [mock_sentence]
        mock_session.world = mock_world
        
        mock_db.query.return_value.get.return_value = mock_session
        
        # Настраиваем random.choice для предсказуемых результатов
        with patch('random.choice', side_effect=lambda x: x[0]):
            
            # Тестируем генерацию шагов
            steps = generate_steps(session_id="ABCD", db=mock_db)
            
            # Проверяем, что было создано правильное количество шагов
            assert len(steps) == 9
            
            # Проверяем, что для каждого шага были созданы соответствующие записи в базе данных
            assert mock_db.add.call_count >= 9  # Минимум 9 вызовов для AdventureStep
            assert mock_db.commit.call_count == 1  # Один коммит в конце


class TestSocketEvents:
    """Тесты для обработки событий сокетов"""
    
    @patch('api.sockets.events.sio')
    @patch('api.sockets.events.get_db')
    async def test_check_answer(self, mock_get_db, mock_sio):
        """Тест обработки ответа игрока"""
        from api.sockets.events import check_answer
        
        # Создаем моки для базы данных и запросов
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Создаем мок для сессии сокета
        mock_session_data = {
            "room_code": "ABCD",
            "username": "TestUser"
        }
        mock_sio.get_session.return_value = mock_session_data
        
        # Создаем моки для шага и опции
        mock_step = MagicMock(spec=AdventureStep)
        mock_quiz_step = MagicMock(spec=QuizStep)
        mock_step.quiz_step = mock_quiz_step
        mock_step.word_order_step = None
        
        mock_option = MagicMock(spec=QuizOption)
        mock_option.id = 1
        
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_step,  # Первый вызов для получения шага
            mock_option  # Второй вызов для получения правильного варианта
        ]
        
        # Тестируем обработку правильного ответа
        await check_answer("test_sid", {
            "step": 1,
            "answer_id": 1,  # Совпадает с ID правильного варианта
            "time_spent": 10.0
        })
        
        # Проверяем, что сессия была обновлена с правильным счетом
        assert "scores" in mock_session_data
        assert "1" in mock_session_data["scores"]
        assert mock_session_data["scores"]["1"]["score"] == 67  # 100 * (1 - 10/30) = 67
        assert mock_session_data["scores"]["1"]["is_correct"] is True
        
        # Проверяем, что был отправлен правильный ответ игроку
        mock_sio.emit.assert_any_call("answer_result", {
            "is_correct": True,
        }, to="test_sid")