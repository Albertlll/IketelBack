from sqlalchemy import (
    Column, Integer, String, Text, Boolean, ForeignKey,
    Enum, JSON, DateTime, Identity
)
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime, timezone
import random
from sqlalchemy.exc import IntegrityError

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
    image = Column(String(255), nullable=True)
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
    sentence = Column(Text, nullable=False)
    world_id = Column(Integer, ForeignKey('worlds.id', ondelete='CASCADE'), nullable=False)

    world = relationship('World', back_populates='sentences')





class AdventureSession(Base):
    __tablename__ = 'adventure_sessions'

    # 4-символьный буквенно-цифровой код как PRIMARY KEY
    join_code = Column(String(4), primary_key=True)

    world_id = Column(Integer, ForeignKey('worlds.id'))
    host_id = Column(Integer, ForeignKey('users.id'))

    world = relationship('World', back_populates='sessions')
    host = relationship('User', back_populates='hosted_sessions')
    steps = relationship('AdventureStep', order_by='AdventureStep.step_number')
    participants = relationship('SessionParticipant', back_populates='session')

    # Алфавит для кодов (без 0/O/1/I/L)
    _CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

    @classmethod
    def _generate_code(cls) -> str:
        """Генерирует 4-символьный код (пример: 'X8FZ')"""
        return ''.join(random.choices(cls._CODE_CHARS, k=4))

    @classmethod
    def create(cls, db, **kwargs) -> 'AdventureSession':
        """Создает сессию с уникальным кодом (макс. 5 попыток)"""
        for _ in range(5):
            session = cls(
                join_code=cls._generate_code(),
                **kwargs
            )
            try:
                db.add(session)
                db.commit()
                return session
            except IntegrityError:
                db.rollback()
        raise ValueError("Не удалось создать сессию (попробуйте снова)")











class AdventureStep(Base):
    __tablename__ = 'adventure_steps'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    session_id = Column(String(4), ForeignKey('adventure_sessions.join_code'), nullable=False)
    step_number = Column(Integer, nullable=False)
    session = relationship('AdventureSession', back_populates='steps')


class QuizStep(Base):
    __tablename__ = 'quiz_steps'
    id = Column(Integer, ForeignKey('adventure_steps.id'), primary_key=True)
    question = Column(Text)
    options = relationship('QuizOption', back_populates='quiz_step')


class QuizOption(Base):
    __tablename__ = 'quiz_options'
    id = Column(Integer, primary_key=True)
    quiz_step_id = Column(Integer, ForeignKey('quiz_steps.id'))
    text = Column(String(255))
    is_correct = Column(Boolean)  # True только для одного варианта

    quiz_step = relationship('QuizStep', back_populates='options')


class WordOrderStep(Base):
    __tablename__ = 'word_order_steps'
    id = Column(Integer, ForeignKey('adventure_steps.id'), primary_key=True)
    sentence_id = Column(Integer, ForeignKey('sentences.id'))

    sentence = relationship('Sentence')


class SessionParticipant(Base):
    __tablename__ = 'player_progress'  # Сохраняем ваше имя таблицы
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_code = Column(String(4), ForeignKey('adventure_sessions.join_code'))
    nickname = Column(String(50), nullable=False)
    # avatar_id = Column(Integer)
    socket_id = Column(String(255))
    session = relationship('AdventureSession', back_populates='participants')