from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey,
    Enum, JSON, DateTime, Identity
)
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime,  default=lambda: datetime.now(timezone.utc))

    worlds = relationship('World', back_populates='author')
    hosted_sessions = relationship('AdventureSession', back_populates='host')


class World(Base):
    __tablename__ = 'worlds'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime,  default=lambda: datetime.now(timezone.utc))
    image = Column(String(255), nullable=False)

    author = relationship('User', back_populates='worlds')
    words = relationship('Word', back_populates='world')
    sentences = relationship('Sentence', back_populates='world')
    sessions = relationship('AdventureSession', back_populates='world')


class Word(Base):
    __tablename__ = 'words'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    word = Column(String(255), nullable=False)
    translation = Column(String(255), nullable=False)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)

    world = relationship('World', back_populates='words')


class Sentence(Base):
    __tablename__ = 'sentences'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    text = Column(Text, nullable=False)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)
    tokens = Column(JSON)  # ["The", "quick", "brown", ...]

    world = relationship('World', back_populates='sentences')


class AdventureSession(Base):
    __tablename__ = 'adventure_sessions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID как строка
    world_id = Column(Integer, ForeignKey('worlds.id'), nullable=False)
    host_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    join_code = Column(String(6), unique=True)  # ABC123
    settings = Column(JSON)  # {"max_players": 20, "difficulty": "medium"}
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    world = relationship('World', back_populates='sessions')
    host = relationship('User', back_populates='hosted_sessions')
    steps = relationship('AdventureStep', order_by='AdventureStep.step_number')
    participants = relationship('SessionParticipant', back_populates='session')


class AdventureStep(Base):
    __tablename__ = 'adventure_steps'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    session_id = Column(String(36), ForeignKey('adventure_sessions.id'), nullable=False)
    step_number = Column(Integer, nullable=False)
    game_type = Column(String(50), nullable=False)  # 'memory', 'word_order', 'quiz'
    content = Column(JSON, nullable=False)  # {"word_ids": [1,2,3], "sentence_id": 5}

    session = relationship('AdventureSession', back_populates='steps')


class SessionParticipant(Base):
    __tablename__ = 'player_progress'  # Сохраняем ваше имя таблицы
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey('adventure_sessions.id'), nullable=False)
    nickname = Column(String(50), nullable=False)
    avatar_id = Column(Integer)
    socket_id = Column(String(255))
    joined_at = Column(DateTime, default=datetime.utcnow)

    session = relationship('AdventureSession', back_populates='participants')