from datetime import timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from ..models.auth import UserCreate, UserLogin
from core.security import create_access_token, create_refresh_token, verify_password, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES, \
    get_current_user
from db.session import get_db
from db.models import User

# Настройка логирования
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register")
async def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Регистрация пользователя с немедленной выдачей пары токенов."""
    logger.info(f"Запрос на регистрацию пользователя с email: {user_data.email}")

    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        logger.warning(f"Попытка повторной регистрации email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    try:
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            email=user_data.email,
            username=user_data.username,
            password_hash=hashed_password,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(data={"sub": db_user.email})

        logger.info(f"Пользователь успешно зарегистрирован: {user_data.email}")
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "refresh_token": refresh_token,
                "email": user_data.email,
                "username": user_data.username
            }
        }
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при регистрации пользователя"
        )

@router.post("/login")
async def login(user_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Логин по email+пароль. Возвращает access и refresh токены."""
    logger.info(f"Попытка входа пользователя с email: {user_data.email}")
    client_ip = request.client.host

    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.password_hash):
        logger.warning(f"Неверные учетные данные: {user_data.email} с IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email})

    logger.info(f"Успешный вход пользователя: {user_data.email} с IP: {client_ip}")
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "email": user.email,
            "username": user.username
        }
    }


@router.post("/refresh")
async def refresh_token_endpoint(request: Request, body: dict):
    """Обновляет access токен по refresh токену."""
    from jose import jwt, JWTError
    from core.config import settings

    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token is required")

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        new_access = create_access_token({"sub": email})
        new_refresh = create_refresh_token({"sub": email})
        return {"success": True, "data": {"access_token": new_access, "refresh_token": new_refresh}}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout")
async def logout():
    """Logout-стаб (для stateless JWT можно реализовать серверный denylist позже)."""
    return {"success": True}


@router.get("/validate")
async def validate_token(
    current_user: User = Depends(get_current_user)
):
    return {"success": True, "data": {"valid": True, "user": current_user.email}}