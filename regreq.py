import requests

# URL эндпоинта для регистрации
url = "https://iketel.ru/api/auth/register"

# Данные для регистрации нового пользователя
user_data = {
    "email": "iloveshuric@sh.ru",
    "username": "Dasha",
    "password": "shusharic"
}

# Отправляем POST-запрос
response = requests.post(url, json=user_data)

# Проверяем ответ
if response.status_code == 200:
    print("Регистрация прошла успешно!")
    print("Ответ сервера:", response.content)
else:
    print("Ошибка при регистрации:", response.status_code)
    print("Сообщение об ошибке:", response.json())