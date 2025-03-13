from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey, Enum, JSON, DateTime, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from datetime import datetime

# Базовый класс для моделей
Base = declarative_base()

# Тип для ролей пользователей
UserRole = PGEnum('teacher', 'student', 'admin', name='user_role')

# Модель пользователя
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(UserRole, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    worlds = relationship('World', back_populates='author')
    games = relationship('Game', back_populates='author')

# Модель мира
class World(Base):
    __tablename__ = 'worlds'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    image = Column(String(255))
    author_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    author = relationship('User', back_populates='worlds')
    games = relationship('Game', back_populates='world')

# Модель типа игры
class GameType(Base):
    __tablename__ = 'game_types'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

# Модель игры
class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    type_id = Column(Integer, ForeignKey('game_types.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    author = relationship('User', back_populates='games')
    world = relationship('World', back_populates='games')
    card_memory_game = relationship('CardMemoryGame', back_populates='game', uselist=False)
    multiple_choice_game = relationship('MultipleChoiceGame', back_populates='game', uselist=False)

# Модель игры с карточками
class CardMemoryGame(Base):
    __tablename__ = 'card_memory_games'

    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    word = Column(Text, nullable=False)
    translation = Column(Text, nullable=False)

    # Связь
    game = relationship('Game', back_populates='card_memory_game')

# Модель игры с выбором вариантов
class MultipleChoiceGame(Base):
    __tablename__ = 'multiple_choice_games'

    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), primary_key=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_answer = Column(String(1), nullable=False)
    explanation = Column(Text)

    # Связь
    game = relationship('Game', back_populates='multiple_choice_game')

