import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

from api.sockets.events import (
    connect, disconnect, host_join, student_join, 
    game_start, check_answer, calculate_score
)


class TestSocketEvents:
    """Тесты для событий сокетов"""
    
    @pytest.mark.asyncio
    async def test_calculate_score(self):
        """Тест функции подсчета очков"""
        # Правильный ответ, минимальное время
        score = calculate_score(is_correct=True, time_spent=0.0)
        assert score == 100
        
        # Правильный ответ, среднее время
        score = calculate_score(is_correct=True, time_spent=15.0)
        assert score == 50
        
        # Неправильный ответ
        score = calculate_score(is_correct=False, time_spent=10.0)
        assert score == 0
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.get_db')
    @patch('api.sockets.events.get_current_user_ws')
    @patch('api.sockets.events.sio')
    async def test_connect_authenticated(self, mock_sio, mock_get_current_user, mock_get_db):
        """Тест подключения аутентифицированного пользователя"""
        # Настраиваем моки
        mock_db_instance = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db_instance
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_get_current_user.return_value = mock_user
        
        mock_sio.save_session = AsyncMock()
        
        # Тестируем подключение
        await connect("test_sid", {}, {"token": "valid_token"})
        
        # Проверяем, что сессия была сохранена с правильными данными
        mock_sio.save_session.assert_called_once_with("test_sid", {
            "user_id": 1,
            "email": "test@example.com",
            "role": "host",
            "is_authenticated": True,
            "isStarted": False
        })
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.get_db')
    @patch('api.sockets.events.sio')
    async def test_connect_unauthenticated(self, mock_sio, mock_get_db):
        """Тест подключения неаутентифицированного пользователя"""
        # Настраиваем моки
        mock_db_instance = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db_instance
        
        mock_sio.save_session = AsyncMock()
        
        # Тестируем подключение без токена
        await connect("test_sid", {}, {})
        
        # Проверяем, что сессия была сохранена с ролью "student"
        mock_sio.save_session.assert_called_once_with("test_sid", {"role": "student"})
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.sio')
    async def test_disconnect_host(self, mock_sio):
        """Тест отключения хоста"""
        # Настраиваем моки
        mock_sio.get_session = AsyncMock(return_value={
            "role": "host",
            "user_id": 1,
            "room_code": "ABCD"
        })
        mock_sio.emit = AsyncMock()
        mock_sio.leave_room = AsyncMock()
        
        # Настраиваем мок для базы данных
        with patch('api.sockets.events.get_db') as mock_get_db:
            mock_db_instance = MagicMock()
            mock_get_db.return_value.__next__.return_value = mock_db_instance
            
            mock_session = MagicMock()
            mock_db_instance.query.return_value.filter_by.return_value.first.return_value = mock_session
            
            # Тестируем отключение
            await disconnect("test_sid")
            
            # Проверяем, что было отправлено сообщение о отключении хоста
            mock_sio.emit.assert_called_with(
                "host_disconnected",
                {"message": "Хост покинул игру"},
                room="ABCD"
            )
            
            # Проверяем, что сессия была удалена из базы данных
            mock_db_instance.delete.assert_called_once_with(mock_session)
            mock_db_instance.commit.assert_called_once()
            
            # Проверяем, что клиент покинул все комнаты
            mock_sio.leave_room.assert_called_once_with("test_sid", "*")
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.get_db')
    @patch('api.sockets.events.sio')
    @patch('api.sockets.events.generate_steps')
    async def test_host_join(self, mock_generate_steps, mock_sio, mock_get_db):
        """Тест присоединения хоста к игре"""
        # Настраиваем моки
        mock_db_instance = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db_instance
        
        mock_sio.get_session = AsyncMock(return_value={
            "role": "host",
            "user_id": 1
        })
        mock_sio.enter_room = AsyncMock()
        mock_sio.emit = AsyncMock()
        
        # Настраиваем мок для AdventureSession.create
        mock_session = MagicMock()
        mock_session.join_code = "ABCD"
        
        with patch('api.sockets.events.AdventureSession.create', return_value=mock_session):
            # Настраиваем мок для generate_steps
            mock_steps = [MagicMock() for _ in range(5)]
            mock_generate_steps.return_value = mock_steps
            
            # Тестируем присоединение хоста
            await host_join("test_sid", {"world_id": 1})
            
            # Проверяем, что хост вошел в комнату
            mock_sio.enter_room.assert_called_once_with("test_sid", "ABCD")
            
            # Проверяем, что было отправлено сообщение о готовности хоста
            mock_sio.emit.assert_called_with(
                "host_ready",
                {
                    "join_code": "ABCD",
                    "steps_count": 5,
                },
                to="test_sid"
            )
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.get_db')
    @patch('api.sockets.events.sio')
    async def test_student_join(self, mock_sio, mock_get_db):
        """Тест присоединения студента к игре"""
        # Настраиваем моки
        mock_db_instance = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db_instance
        
        mock_sio.save_session = AsyncMock()
        mock_sio.emit = AsyncMock()
        
        # Настраиваем мок для запроса к базе данных
        mock_session = MagicMock()
        mock_db_instance.query.return_value.filter_by.return_value.first.return_value = mock_session
        
        # Тестируем присоединение студента
        await student_join("test_sid", {"room_code": "ABCD", "username": "TestUser"})
        
        # Проверяем, что сессия была сохранена с правильными данными
        mock_sio.save_session.assert_called_once_with("test_sid", {
            "role": "student",
            "room_code": "ABCD",
            "progress": {
                "current_step": 0,
            }
        })
        
        # Проверяем, что были отправлены сообщения о присоединении студента
        mock_sio.emit.assert_any_call(
            'student_joined',
            {'message': 'Success'},
            to="test_sid"
        )
        mock_sio.emit.assert_any_call(
            'new_student_joined',
            {'sid': "test_sid", 'username': "TestUser"},
            room="ABCD"
        )
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.sio')
    async def test_game_start(self, mock_sio):
        """Тест начала игры"""
        # Настраиваем моки
        mock_sio.get_session = AsyncMock(return_value={
            "role": "host",
            "room_code": "ABCD"
        })
        mock_sio.emit = AsyncMock()
        
        # Тестируем начало игры
        await game_start("test_sid", {})
        
        # Проверяем, что было отправлено сообщение о начале игры
        mock_sio.emit.assert_called_once_with(
            "game_started",
            room="ABCD"
        )
    
    @pytest.mark.asyncio
    @patch('api.sockets.events.get_db')
    @patch('api.sockets.events.sio')
    @patch('api.sockets.events.calculate_score')
    async def test_check_answer_correct(self, mock_calculate_score, mock_sio, mock_get_db):
        """Тест проверки правильного ответа"""
        # Настраиваем моки
        mock_db_instance = MagicMock()
        mock_get_db.return_value.__next__.return_value = mock_db_instance
        
        mock_sio.get_session = AsyncMock(return_value={
            "room_code": "ABCD",
            "username": "TestUser"
        })
        mock_sio.emit = AsyncMock()
        
        # Настраиваем моки для запросов к базе данных
        mock_step = MagicMock()
        mock_quiz_step = MagicMock()
        mock_step.quiz_step = mock_quiz_step
        mock_step.word_order_step = None
        
        mock_option = MagicMock()
        mock_option.id = 1
        
        mock_db_instance.query.return_value.filter_by.return_value.first.side_effect = [
            mock_step,  # Первый вызов для получения шага
            mock_option  # Второй вызов для получения правильного варианта
        ]
        
        # Настраиваем мок для calculate_score
        mock_calculate_score.return_value = 75
        
        # Настраиваем мок для host_sessions
        with patch('api.sockets.events.host_sessions', {"ABCD": "host_sid"}):
            # Тестируем проверку правильного ответа
            await check_answer("test_sid", {
                "step": 1,
                "answer_id": 1,  # Совпадает с ID правильного варианта
                "time_spent": 10.0
            })
            
            # Проверяем, что был вызван calculate_score с правильными параметрами
            mock_calculate_score.assert_called_once_with(True, 10.0)
            
            # Проверяем, что было отправлено сообщение о результате ответа
            mock_sio.emit.assert_any_call(
                "answer_result",
                {"is_correct": True},
                to="test_sid"
            )
            
            # Проверяем, что было отправлено сообщение хосту
            mock_sio.emit.assert_any_call(
                "player_answered",
                {
                    "player_sid": "test_sid",
                    "step": 1,
                    "is_correct": True,
                    "username": "TestUser"
                },
                to="host_sid"
            )