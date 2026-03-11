BEGIN;

DO $$
DECLARE
    v_user_id  INTEGER;
    v_world_id INTEGER;
BEGIN
    SELECT u.id
    INTO v_user_id
    FROM users u
    WHERE u.username = 'mkm'
    ORDER BY u.id
    LIMIT 1;

    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Пользователь с ником "%" не найден', 'mkm';
    END IF;

    SELECT w.id
    INTO v_world_id
    FROM worlds w
    WHERE w.author_id = v_user_id
      AND w.title = 'Звёздные войны'
    ORDER BY w.id
    LIMIT 1;

    IF v_world_id IS NULL THEN
        INSERT INTO worlds (title, description, author_id, is_public)
        VALUES (
            'Звёздные войны',
            'Мирок по вселенной Star Wars: базовые термины и фразы для изучения перевода.',
            v_user_id,
            TRUE
        )
        RETURNING id INTO v_world_id;
    ELSE
        UPDATE worlds
        SET description = 'Мирок по вселенной Star Wars: базовые термины и фразы для изучения перевода.',
            is_public = TRUE
        WHERE id = v_world_id;
    END IF;

    DELETE FROM words WHERE world_id = v_world_id;
    DELETE FROM sentences WHERE world_id = v_world_id;

    INSERT INTO words (word, translation, world_id)
    VALUES
        ('Джедай', 'Jedi', v_world_id),
        ('Ситх', 'Sith', v_world_id),
        ('Сила', 'Force', v_world_id),
        ('Световой меч', 'lightsaber', v_world_id),
        ('Повстанцы', 'Rebels', v_world_id),
        ('Империя', 'Empire', v_world_id),
        ('Галактика', 'galaxy', v_world_id),
        ('Космический корабль', 'starship', v_world_id),
        ('Дроид', 'droid', v_world_id),
        ('Гиперпрыжок', 'hyperspace jump', v_world_id),
        ('Пилот', 'pilot', v_world_id),
        ('Планета', 'planet', v_world_id);

    INSERT INTO sentences (sentence, world_id)
    VALUES
        ('Джедай использует Силу.', v_world_id),
        ('Повстанцы сражаются против Империи.', v_world_id),
        ('Пилот ведёт космический корабль через галактику.', v_world_id),
        ('Дроид помогает команде во время гиперпрыжка.', v_world_id);

    RAISE NOTICE 'Готово. user_id=%, world_id=%', v_user_id, v_world_id;
END $$;

COMMIT;
