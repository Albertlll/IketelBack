import json
import logging
import re
import time
from typing import Any

from gigachat import GigaChat
from pydantic import BaseModel, Field, ValidationError

from core.config import settings
from db.models import World

logger = logging.getLogger(__name__)


class StudyGenerationError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class StudyTask(BaseModel):
    title: str = Field(min_length=1)
    variants: list[str] = Field(min_length=2)
    answer: int
    state: int = 0


class StudyBlock(BaseModel):
    replika: str = Field(min_length=1)
    image_url: str | None = None
    tasks: list[StudyTask] = Field(min_length=1)


class StudyGameSchema(BaseModel):
    game: list[StudyBlock] = Field(min_length=1)


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def _extract_json_payload(text: str) -> Any:
    if not text:
        raise StudyGenerationError("Пустой ответ от GigaChat", status_code=502)

    stripped = text.strip()

    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)

    fenced_match = _JSON_BLOCK_RE.search(stripped)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    left_brace = stripped.find("{")
    left_bracket = stripped.find("[")
    start_positions = [pos for pos in (left_brace, left_bracket) if pos != -1]
    if not start_positions:
        raise StudyGenerationError("Ответ GigaChat не содержит JSON", status_code=502)

    start = min(start_positions)
    return json.loads(stripped[start:])


def _normalize_answer(answer: int, variants_count: int) -> int:
    if variants_count <= 0:
        return 0
    if 0 <= answer < variants_count:
        return answer
    if 1 <= answer <= variants_count:
        return answer - 1
    return 0


def _build_fallback_task(world: World, idx: int) -> StudyTask:
    words = world.words or []
    if words:
        word = words[idx % len(words)]
        wrong_words = [w.translation for w in words if w.id != word.id][:3]
        options = [word.translation, *wrong_words]
        while len(options) < 4:
            options.append(f"Вариант {len(options) + 1}")
        return StudyTask(
            title=f"Переведите слово: {word.word}",
            variants=options,
            answer=0,
            state=0,
        )

    return StudyTask(
        title=f"Вопрос {idx + 1}",
        variants=["Ответ 1", "Ответ 2", "Ответ 3", "Ответ 4"],
        answer=0,
        state=0,
    )


def _normalize_game(
    game_blocks: list[StudyBlock],
    world: World,
    blocks_count: int,
    quiz_count: int,
) -> list[dict[str, Any]]:
    if not game_blocks:
        raise StudyGenerationError("GigaChat вернул пустую игру", status_code=502)

    normalized_blocks = list(game_blocks)

    while len(normalized_blocks) < blocks_count:
        normalized_blocks.append(
            StudyBlock(
                replika=f"Блок {len(normalized_blocks) + 1}",
                tasks=[_build_fallback_task(world, len(normalized_blocks))],
            )
        )

    normalized_blocks = normalized_blocks[:blocks_count]

    total_tasks_needed = quiz_count
    base_tasks_per_block = total_tasks_needed // blocks_count
    extra = total_tasks_needed % blocks_count

    task_counter = 0
    out: list[dict[str, Any]] = []

    for block_index, block in enumerate(normalized_blocks):
        expected_count = base_tasks_per_block + (1 if block_index < extra else 0)
        expected_count = max(1, expected_count)

        tasks = list(block.tasks)
        while len(tasks) < expected_count:
            tasks.append(_build_fallback_task(world, task_counter))
            task_counter += 1

        tasks = tasks[:expected_count]

        normalized_tasks: list[dict[str, Any]] = []
        for task in tasks:
            answer = _normalize_answer(task.answer, len(task.variants))
            normalized_tasks.append(
                {
                    "title": task.title,
                    "variants": task.variants,
                    "answer": answer,
                    "state": 0,
                }
            )

        out.append(
            {
                "replika": block.replika,
                "image_url": block.image_url,
                "tasks": normalized_tasks,
            }
        )

    return out


def _build_prompt(world: World, prompt: str, blocks_count: int, quiz_count: int) -> str:
    words = world.words or []
    sentences = world.sentences or []

    words_str = "\n".join(
        [f"- {word.word} -> {word.translation}" for word in words[:80]]
    ) or "- нет слов"
    sentence_str = "\n".join([f"- {sentence.sentence}" for sentence in sentences[:40]]) or "- нет предложений"

    return (
        "Сгенерируй структуру обучающей текстовой игры и верни ТОЛЬКО JSON.\\n"
        f"Нужно блоков: {blocks_count}.\\n"
        f"Нужно суммарно quiz-вопросов: {quiz_count}.\\n"
        "Формат строго:\\n"
        "{\\n"
        '  "game": [\\n'
        "    {\\n"
        '      "replika": "текст вступления блока",\\n'
        '      "image_url": "необязательно, может быть null",\\n'
        '      "tasks": [\\n'
        "        {\\n"
        '          "title": "вопрос",\\n'
        '          "variants": ["вариант1", "вариант2", "вариант3", "вариант4"],\\n'
        '          "answer": 0,\\n'
        '          "state": 0\\n'
        "        }\\n"
        "      ]\\n"
        "    }\\n"
        "  ]\\n"
        "}\\n"
        "answer должен быть индексом правильного ответа, предпочтительно 0-based (0..N-1).\\n"
        "Не добавляй markdown, комментарии или пояснения.\\n\\n"
        f"Тема от пользователя:\\n{prompt}\\n\\n"
        "Материал мира (используй его лексику и контекст):\\n"
        f"Слова:\\n{words_str}\\n\\n"
        f"Предложения:\\n{sentence_str}"
    )


def _extract_llm_text(response: Any) -> str:
    if isinstance(response, str):
        return response

    if isinstance(response, dict):
        choices = response.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
        content = response.get("content")
        if isinstance(content, str):
            return content

    if hasattr(response, "choices") and response.choices:
        first = response.choices[0]
        if hasattr(first, "message") and hasattr(first.message, "content"):
            return first.message.content

    if hasattr(response, "content"):
        return str(response.content)

    return str(response)


def _call_gigachat(prompt: str) -> str:
    if not settings.gigachat_api_key:
        raise StudyGenerationError("Не настроен GIGACHAT_API_KEY", status_code=502)

    start_time = time.perf_counter()

    try:
        with GigaChat(
            credentials=settings.gigachat_api_key,
            verify_ssl_certs=settings.gigachat_verify_ssl_certs,
            timeout=settings.gigachat_timeout_sec,
        ) as giga:
            response = giga.chat(
                {
                    "model": settings.gigachat_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты сервис генерации JSON. Отвечай строго валидным JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.2,
                }
            )

        llm_text = _extract_llm_text(response)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000)
        logger.info("study_generation: gigachat response received in %sms", elapsed_ms)
        return llm_text

    except TimeoutError as exc:
        raise StudyGenerationError("Таймаут GigaChat", status_code=504) from exc
    except Exception as exc:
        logger.exception("study_generation: gigachat request failed")
        raise StudyGenerationError(f"Ошибка GigaChat: {exc}", status_code=502) from exc


def generate_study_game(
    world: World,
    prompt: str,
    blocks_count: int,
    quiz_count: int,
) -> list[dict[str, Any]]:
    full_prompt = _build_prompt(world, prompt, blocks_count, quiz_count)
    raw_text = _call_gigachat(full_prompt)

    try:
        payload = _extract_json_payload(raw_text)
    except json.JSONDecodeError as exc:
        logger.exception("study_generation: invalid JSON from gigachat")
        raise StudyGenerationError("Невалидный JSON от GigaChat", status_code=502) from exc

    if isinstance(payload, list):
        payload = {"game": payload}

    try:
        parsed = StudyGameSchema.model_validate(payload)
    except ValidationError as exc:
        logger.exception("study_generation: schema validation failed")
        raise StudyGenerationError(
            f"Неверная структура JSON от GigaChat: {exc}",
            status_code=502,
        ) from exc

    normalized = _normalize_game(parsed.game, world, blocks_count, quiz_count)

    logger.info(
        "study_generation: normalized output blocks=%s quizzes=%s",
        len(normalized),
        sum(len(block["tasks"]) for block in normalized),
    )

    return normalized
