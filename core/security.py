from datetime import datetime, timedelta
from typing import Any, Optional
import logging
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, WebSocketException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from db.session import get_db
from db.models import User

# Настройка логирования
logger = logging.getLogger(__name__)

# Добавляем модель TokenData
class TokenData(BaseModel):
    email: Optional[str] = None

# Настройки JWT из конфигурации
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Ошибка при проверке пароля: {e}")
        # Важно - возвращаем False при ошибке, а не пропускаем
        return False

def get_password_hash(password: str) -> str:
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Ошибка при хешировании пароля: {e}")
        # Здесь мы генерируем исключение, чтобы не создавать пользователя с пустым паролем
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при обработке пароля"
        )

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=3)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user



async def get_current_user_ws(token: str, db: Session) -> User:
    """Упрощенная проверка токена для WebSocket"""
    if not token:
        logger.error("WebSocket auth: Token is missing")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            logger.error("WebSocket auth: Invalid token payload (no email)")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

        user = db.query(User).filter(User.email == email).first()
        if not user:
            logger.error(f"WebSocket auth: User not found (email: {email})")
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

        logger.debug(f"WebSocket auth success for user: {email}")
        return user

    except JWTError as e:
        logger.error(f"WebSocket auth JWT error: {str(e)}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)