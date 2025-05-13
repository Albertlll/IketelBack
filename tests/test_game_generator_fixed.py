import pytest
from unittest.mock import MagicMock, patch
from api.utils.game_generator import generate_games
from db.models import World, Word

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
        
        # Настраиваем random.choice для возврата разных значений при разных вызовах
        # Первый вызов - тип игры "translate"
        # Второй вызов - тип игры "multiple_choice"
        # Третий и четвертый вызовы - выбор слова "Алма"
        with patch('random.choice', side_effect=["translate", "multiple_choice", mock_word1, mock_word1]), \
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