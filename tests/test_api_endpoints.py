import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from main import fastapi_app
from api.endpoints import worlds, game, auth, adventures


class TestGameEndpoints:
    """Тесты для эндпоинтов игры"""
    
    def test_get_game(self):
        """Тест получения игры по ID"""
        client = TestClient(fastapi_app)
        
        # Тестируем получение существующей игры
        response = client.get("/game/5")
        assert response.status_code == 200
        assert response.json()["type"] == "vocabulary"
        assert response.json()["vocabulary"][0]["word"] == "Алма"
        assert response.json()["vocabulary"][0]["translation"] == "Яблоко"
        
        # Тестируем получение несуществующей игры
        response = client.get("/game/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Игра не найдена"


class TestWorldsEndpoints:
    """Тесты для эндпоинтов миров"""
    
    @patch('api.endpoints.worlds.get_db')
    @patch('api.endpoints.worlds.get_current_user')
    def test_get_worlds(self, mock_get_current_user, mock_get_db):
        """Тест получения списка миров"""
        # Настраиваем моки
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        
        # Создаем тестовый клиент
        app = FastAPI()
        app.include_router(worlds.router, prefix="/worlds")
        client = TestClient(app)
        
        # Настраиваем мок для запроса к базе данных
        mock_world1 = MagicMock()
        mock_world1.id = 1
        mock_world1.title = "Мир 1"
        mock_world1.description = "Описание мира 1"
        mock_world1.is_public = True
        
        mock_world2 = MagicMock()
        mock_world2.id = 2
        mock_world2.title = "Мир 2"
        mock_world2.description = "Описание мира 2"
        mock_world2.is_public = False
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_world1, mock_world2]
        
        # Тестируем получение списка миров
        response = client.get("/worlds/")
        
        # Проверяем, что запрос к базе данных был выполнен
        mock_db.query.assert_called_once()
        
        # Проверяем результат
        assert response.status_code == 200
        assert len(response.json()) == 2
        assert response.json()[0]["id"] == 1
        assert response.json()[0]["title"] == "Мир 1"
        assert response.json()[1]["id"] == 2
        assert response.json()[1]["title"] == "Мир 2"


class TestAdventuresEndpoints:
    """Тесты для эндпоинтов приключений"""
    
    @patch('api.endpoints.adventures.get_db')
    @patch('api.endpoints.adventures.get_current_user')
    def test_create_adventure_session(self, mock_get_current_user, mock_get_db):
        """Тест создания сессии приключения"""
        # Настраиваем моки
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_current_user.return_value = mock_user
        
        # Создаем тестовый клиент
        app = FastAPI()
        app.include_router(adventures.router, prefix="/adventures")
        client = TestClient(app)
        
        # Настраиваем мок для AdventureSession.create
        mock_session = MagicMock()
        mock_session.join_code = "ABCD"
        
        with patch('api.endpoints.adventures.AdventureSession.create', return_value=mock_session):
            # Тестируем создание сессии
            response = client.post("/adventures/sessions", json={"world_id": 1})
            
            # Проверяем результат
            assert response.status_code == 200
            assert response.json()["join_code"] == "ABCD"


class TestAuthEndpoints:
    """Тесты для эндпоинтов аутентификации"""
    
    @patch('api.endpoints.auth.get_db')
    def test_register_user(self, mock_get_db):
        """Тест регистрации пользователя"""
        # Настраиваем моки
        mock_db = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db
        
        # Создаем тестовый клиент
        app = FastAPI()
        app.include_router(auth.router, prefix="/auth")
        client = TestClient(app)
        
        # Настраиваем мок для запроса к базе данных
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Настраиваем мок для хеширования пароля
        with patch('api.endpoints.auth.get_password_hash', return_value="hashed_password"):
            # Тестируем регистрацию пользователя
            response = client.post("/auth/register", json={
                "username": "TestUser",
                "email": "test@example.com",
                "password": "password123"
            })
            
            # Проверяем, что пользователь был добавлен в базу данных
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            
            # Проверяем результат
            assert response.status_code == 200
            assert "access_token" in response.json()
            assert response.json()["token_type"] == "bearer"