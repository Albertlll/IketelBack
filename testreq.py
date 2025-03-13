import requests
import json

# URL базовый
base_url = "http://localhost:8000"  # Измените на ваш адрес сервера

# 1. Сначала авторизуемся
login_url = f"{base_url}/auth/login"
login_data = {
  "email": "iloveshurik@mail.com",
  "password": "string"
}

print("Отправляем запрос авторизации...")
login_response = requests.post(login_url, json=login_data)

# Проверяем статус
if login_response.status_code != 200:
    print(f"Ошибка авторизации: {login_response.status_code}")
    print(f"Текст ответа: {login_response.text}")
    exit(1)

# Получаем токен
token = login_response.json()["access_token"]
print(f"Получен токен: {token[:10]}...")

# 2. Создаем мир
worlds_url = f"{base_url}/worlds/"
headers = {
    "Authorization": f"Bearer {token}"
}

# Подготовка данных и файла
data = {
    "title": "Тестовый мир",
    "description": "Это тестовый мир, созданный через API",
    "is_public": "true"
}

# Замените путь на реальный путь к изображению
image_path = "8nn5aa7d5vgd1.jpeg"  # ← ЗАМЕНИТЕ ЭТО!

try:
    with open(image_path, "rb") as img_file:
        files = {"image": (image_path.split("/")[-1], img_file, "image/jpeg")}
        
        print("Отправляем запрос на создание мира...")
        response = requests.post(
            worlds_url, 
            headers=headers, 
            data=data, 
            files=files
        )
        
        # Печатаем статус и ответ
        print(f"Статус: {response.status_code}")
        print(f"Текст ответа: {response.text}")
        
        # Пробуем распарсить JSON только если статус успешный
        if response.status_code == 200 or response.status_code == 201:
            print("Результат JSON:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Произошла ошибка: {e}")