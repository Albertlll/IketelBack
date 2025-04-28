from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import World, Word

DATABASE_URL = "postgresql://postgres:mysecretpassword@localhost:5432/mydatabase"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def seed_words(db: Session):
    """Добавляем тематические слова в конкретные миры (id 1, 2, 3)"""
    worlds_words = {
        # Фэнтези Земли (id=1)
        1: [
            ("Волшебник", "Сихерче"),
            ("Дракон", "Аждаһа"),
            ("Замок", "Сарай"),
            ("Меч", "Кылыч"),
            ("Карта", "Харита"),
            ("Легенда", "Риваять"),
            ("Принцесса", "Хан кызы"),
            ("Тайна", "Сер"),
            ("Книга заклинаний", "Дога китабы"),
            ("Рыцарь", "Батыр")
        ],
        # Кибер Город (id=2)
        2: [
            ("Робот", "Робот"),
            ("Компьютер", "Санак"),
            ("Голограмма", "Голограмма"),
            ("Неон", "Неон"),
            ("Дрон", "Дрон"),
            ("Вирус", "Вирус"),
            ("Киберпанк", "Киберпанк"),
            ("Гаджет", "Гаджет"),
            ("Искусственный интеллект", "Ясалма интеллект"),
            ("Технология", "Технология")
        ],
        # Древнее Королевство (id=3)
        3: [
            ("Король", "Падишаһ"),
            ("Крепость", "Ныгытма"),
            ("Сражение", "Сугыш"),
            ("Деревня", "Авыл"),
            ("Кузнец", "Тимерче"),
            ("Щит", "Капка"),
            ("Трон", "Тахет"),
            ("Доспехи", "Сакларгыч"),
            ("Корона", "Таҗ"),
            ("Свиток", "Чыганак")
        ]
    }

    try:
        for world_id, words in worlds_words.items():
            for russian, tatar in words:
                # Проверка на существование слова
                if not db.query(Word).filter_by(word=russian, world_id=world_id).first():
                    db.add(Word(
                        word=russian,
                        translation=tatar,
                        world_id=world_id
                    ))

        db.commit()
        print(f"✅ Успешно добавлены слова в миры 1, 2 и 3!")
        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {str(e)}")
        return False



seed_words(session)