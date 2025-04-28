from datetime import timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..models.auth import UserCreate, UserLogin, Token
from core.security import create_access_token, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from db.session import get_db
from db.models import User

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    logger.info(f"Запрос на регистрацию пользователя с email: {user_data.email}")
    
    # Проверяем, существует ли пользователь
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        logger.warning(f"Попытка повторной регистрации email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Создаем нового пользователя
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
            role='student'  # По умолчанию роль student
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Создаем токен доступа
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        logger.info(f"Пользователь успешно зарегистрирован: {user_data.email}")
        return {"access_token": access_token, "token_type": "bearer", "email" : user.email, "username": user.username}
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при регистрации пользователя"
        )

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    logger.info(f"Попытка входа пользователя с email: {user_data.email}")
    client_ip = request.client.host
    
    # Находим пользователя
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user:
        logger.warning(f"Попытка входа с несуществующим email: {user_data.email} с IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Проверяем пароль
    if not verify_password(user_data.password, user.password_hash):
        logger.warning(f"Неверный пароль для пользователя: {user_data.email} с IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаем токен доступа
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"Успешный вход пользователя: {user_data.email} с IP: {client_ip}")
    return {"access_token": access_token, "token_type": "bearer", "email" : user.email, "username": user.username} 