import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from db.models import User, World, Word, Sentence, AdventureSession


class TestUserModel:
    """Тесты для модели пользователя"""
    
    def test_user_relationships(self, mock_db):
        """Тест отношений пользователя с другими моделями"""
        # Создаем пользователя
        user = User(
            username="TestUser",
            email="test@example.com",
            password_hash="hashed_password"
        )
        
        # Создаем мир, связанный с пользователем
        world = World(
            title="Тестовый мир",
            description="Описание тестового мира",
            author=user
        )
        
        # Создаем сессию, связанную с пользователем
        session = AdventureSession(
            join_code="ABCD",
            host=user,
            world=world
        )
        
        # Проверяем отношения
        assert user in world.author.worlds
        assert session in user.hosted_sessions
        
        # Проверяем атрибуты пользователя
        assert user.username == "TestUser"
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password"
        assert isinstance(user.created_at, datetime)


class TestWorldModel:
    """Тесты для модели мира"""
    
    def test_world_relationships(self, mock_db, mock_user):
        """Тест отношений мира с другими моделями"""
        # Создаем мир
        world = World(
            title="Тестовый мир",
            description="Описание тестового мира",
            author=mock_user,
            is_public=True,
            image="world.jpg"
        )
        
        # Создаем слова, связанные с миром
        word1 = Word(
            word="Алма",
            translation="Яблоко",
            world=world
        )
        
        word2 = Word(
            word="Су",
            translation="Вода",
            world=world
        )
        
        # Создаем предложения, связанные с миром
        sentence = Sentence(
            sentence="Мен алма жеймін",
            world=world
        )
        
        # Проверяем отношения
        assert word1 in world.words
        assert word2 in world.words
        assert sentence in world.sentences
        assert world in mock_user.worlds
        
        # Проверяем атрибуты мира
        assert world.title == "Тестовый мир"
        assert world.description == "Описание тестового мира"
        assert world.is_public is True
        assert world.image == "world.jpg"
        assert isinstance(world.created_at, datetime)


class TestAdventureSessionModel:
    """Тесты для модели сессии приключения"""
    
    def test_session_code_generation(self):
        """Тест генерации кода сессии"""
        # Проверяем, что генерируется код правильной длины
        code = AdventureSession._generate_code()
        assert len(code) == 4
        
        # Проверяем, что код содержит только допустимые символы
        allowed_chars = set(AdventureSession._CODE_CHARS)
        for char in code:
            assert char in allowed_chars
    
    @patch('db.models.AdventureSession._generate_code')
    def test_session_creation(self, mock_generate_code, mock_db, mock_user, mock_world):
        """Тест создания сессии"""
        # Настраиваем мок для генерации кода
        mock_generate_code.return_value = "ABCD"
        
        # Тестируем создание сессии
        session = AdventureSession.create(
            db=mock_db,
            host_id=mock_user.id,
            world_id=mock_world.id
        )
        
        # Проверяем результаты
        assert session.join_code == "ABCD"
        assert session.host_id == mock_user.id
        assert session.world_id == mock_world.id
        
        # Проверяем, что сессия была добавлена в базу данных и коммит был выполнен
        mock_db.add.assert_called_once_with(session)
        mock_db.commit.assert_called_once()
    
    @patch('db.models.AdventureSession._generate_code')
    def test_session_creation_with_conflict(self, mock_generate_code, mock_db):
        """Тест создания сессии с конфликтом"""
        from sqlalchemy.exc import IntegrityError
        
        # Настраиваем мок для генерации кода
        mock_generate_code.side_effect = ["ABCD", "EFGH"]
        
        # Настраиваем мок для базы данных, чтобы первый вызов add вызывал IntegrityError
        mock_db.add.side_effect = [IntegrityError("", "", ""), None]
        
        # Тестируем создание сессии
        session = AdventureSession.create(
            db=mock_db,
            host_id=1,
            world_id=1
        )
        
        # Проверяем результаты
        assert session.join_code == "EFGH"
        assert mock_db.rollback.call_count == 1
        assert mock_db.commit.call_count == 1