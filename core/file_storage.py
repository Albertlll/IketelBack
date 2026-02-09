import base64
from PIL import Image
from io import BytesIO

import boto3
import uuid
from fastapi import UploadFile, HTTPException, status
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

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB
ALLOWED_FORMATS = {"jpeg": "image/jpeg", "png": "image/png"}

async def upload_image(file: UploadFile, folder: str = "worlds") -> str:
    """
    Загружает изображение в Object Storage и возвращает его URL
    """
    contents = await file.read()
    if len(contents) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large")

    try:
        with Image.open(BytesIO(contents)) as img:
            detected = img.format.lower()
    except Exception:
        detected = None

    if detected not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    file_extension = ".jpg" if detected == "jpeg" else ".png"
    new_filename = f"{folder}/{uuid.uuid4()}{file_extension}"

    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=new_filename,
        Body=contents,
        ContentType=ALLOWED_FORMATS[detected]
    )

    return f"{S3_ENDPOINT}/{S3_BUCKET_NAME}/{new_filename}"


async def upload_base64(base64_str: str, folder: str = "worlds") -> str:
    """
    Загружает base64 изображение в S3 и возвращает URL.
    Выполняет проверку размера и формата (jpeg/png).
    """
    try:
        if not base64_str:
            return None
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        image_data = base64.b64decode(base64_str)

        if len(image_data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image too large")

        try:
            with Image.open(BytesIO(image_data)) as img:
                detected = img.format.lower()
        except Exception:
            detected = None

        if detected not in ALLOWED_FORMATS:
            raise HTTPException(status_code=400, detail="Unsupported image format")

        file_extension = ".jpg" if detected == "jpeg" else ".png"
        filename = f"{folder}/{uuid.uuid4()}{file_extension}"

        s3_client.put_object(
            Bucket=settings.s3_bucket,
            Key=filename,
            Body=image_data,
            ContentType=ALLOWED_FORMATS[detected]
        )

        return f"{settings.s3_endpoint}/{settings.s3_bucket}/{filename}"

    except HTTPException:
        raise
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return None
