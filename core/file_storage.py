import boto3
import uuid
from fastapi import UploadFile
import os
from core.config import settings

# Настройки для Yandex Object Storage
S3_ENDPOINT = settings.s3_endpoint
S3_BUCKET_NAME = settings.s3_bucket
S3_ACCESS_KEY = settings.s3_access_key
S3_SECRET_KEY = settings.s3_secret_key

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)

async def upload_image(file: UploadFile, folder: str = "worlds") -> str:
    """
    Загружает изображение в Object Storage и возвращает его URL
    """
    # Генерируем уникальное имя файла
    file_extension = os.path.splitext(file.filename)[1]
    new_filename = f"{folder}/{uuid.uuid4()}{file_extension}"
    
    # Загружаем файл в бакет
    contents = await file.read()
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=new_filename,
        Body=contents,
        ContentType=file.content_type
    )
    
    # Возвращаем публичный URL
    file_url = f"{S3_ENDPOINT}/{S3_BUCKET_NAME}/{new_filename}"
    return file_url 