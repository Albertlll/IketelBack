import os
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Эта строка загружает все переменные из файла .env 
# и добавляет их в переменные окружения (os.environ)
load_dotenv()

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # S3 настройки
    s3_endpoint: str
    s3_bucket: str
    s3_access_key: str
    s3_secret_key: str

    class Config:
        env_file = os.getenv("ENV_FILE", ".env")

settings = Settings()