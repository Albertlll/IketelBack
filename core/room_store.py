import time
from typing import List, Dict
from redis import asyncio as redis
from core.config import settings


ROOM_META = "room:{code}:meta"
ROOM_PLAYERS = "room:{code}:players"
ROOM_PLAYER = "room:{code}:player:{sid}"
ROOM_FINISHED = "room:{code}:finished"


def _meta_key(code: str) -> str:
    return ROOM_META.format(code=code)


def _players_key(code: str) -> str:
    return ROOM_PLAYERS.format(code=code)


def _player_key(code: str, sid: str) -> str:
    return ROOM_PLAYER.format(code=code, sid=sid)


def _finished_key(code: str) -> str:
    return ROOM_FINISHED.format(code=code)


async def _touch_room(r: redis.Redis, code: str) -> None:
    ttl = settings.redis_room_ttl_seconds
    await r.expire(_meta_key(code), ttl)
    await r.expire(_players_key(code), ttl)
    await r.expire(_finished_key(code), ttl)


async def ensure_room(r: redis.Redis, code: str, steps_count: int) -> None:
    meta_key = _meta_key(code)
    exists = await r.exists(meta_key)
    if not exists:
        await r.hset(
            meta_key,
            mapping={
                "started": "0",
                "steps_count": str(steps_count),
                "created_at": str(int(time.time())),
                "finished_count": "0",
            },
        )
    await _touch_room(r, code)


async def set_started(r: redis.Redis, code: str) -> None:
    await r.hset(_meta_key(code), "started", "1")
    await _touch_room(r, code)


async def is_started(r: redis.Redis, code: str) -> bool:
    value = await r.hget(_meta_key(code), "started")
    return value == "1"


async def get_steps_count(r: redis.Redis, code: str) -> int:
    value = await r.hget(_meta_key(code), "steps_count")
    try:
        return int(value or 0)
    except ValueError:
        return 0


async def upsert_player(r: redis.Redis, code: str, sid: str, username: str | None) -> None:
    player_key = _player_key(code, sid)
    await r.hset(
        player_key,
        mapping={
            "username": username or "",
            "finished": "0",
        },
    )
    await r.zadd(_players_key(code), {sid: 0}, nx=True)
    await _touch_room(r, code)


async def remove_player(r: redis.Redis, code: str, sid: str) -> None:
    script = """
    local player_key = KEYS[1]
    local meta_key = KEYS[2]
    local players_key = KEYS[3]
    local finished = redis.call("HGET", player_key, "finished")
    if finished == "1" then
        redis.call("HINCRBY", meta_key, "finished_count", -1)
    end
    redis.call("DEL", player_key)
    redis.call("ZREM", players_key, ARGV[1])
    return 1
    """
    await r.eval(script, 3, _player_key(code, sid), _meta_key(code), _players_key(code), sid)
    await _touch_room(r, code)


async def add_score(r: redis.Redis, code: str, sid: str, delta: int) -> None:
    await r.zincrby(_players_key(code), delta, sid)
    await _touch_room(r, code)


async def get_leaderboard(r: redis.Redis, code: str) -> List[Dict[str, int | str]]:
    players_key = _players_key(code)
    entries = await r.zrevrange(players_key, 0, -1, withscores=True)
    leaderboard: List[Dict[str, int | str]] = []
    for sid, score in entries:
        username = await r.hget(_player_key(code, sid), "username")
        leaderboard.append(
            {"sid": sid, "username": username, "score": int(score or 0)}
        )
    await _touch_room(r, code)
    return leaderboard


async def get_top3(r: redis.Redis, code: str) -> List[Dict[str, int | str]]:
    entries = await r.zrevrange(_players_key(code), 0, 2, withscores=True)
    result: List[Dict[str, int | str]] = []
    for idx, (sid, score) in enumerate(entries):
        username = await r.hget(_player_key(code, sid), "username")
        result.append(
            {"place": idx + 1, "username": username, "score": int(score or 0)}
        )
    await _touch_room(r, code)
    return result


async def get_player_place(r: redis.Redis, code: str, sid: str) -> int:
    rank = await r.zrevrank(_players_key(code), sid)
    if rank is None:
        return 0
    return int(rank) + 1


async def get_player_score(r: redis.Redis, code: str, sid: str) -> int:
    score = await r.zscore(_players_key(code), sid)
    return int(score or 0)


async def mark_finished_and_check_all(r: redis.Redis, code: str, sid: str) -> bool:
    script = """
    local player_key = KEYS[1]
    local meta_key = KEYS[2]
    local players_key = KEYS[3]
    if redis.call("HGET", player_key, "finished") == "1" then
        return 0
    end
    redis.call("HSET", player_key, "finished", "1")
    local finished = redis.call("HINCRBY", meta_key, "finished_count", 1)
    local total = redis.call("ZCARD", players_key)
    if total > 0 and finished >= total then
        return 1
    end
    return 0
    """
    result = await r.eval(script, 3, _player_key(code, sid), _meta_key(code), _players_key(code))
    await _touch_room(r, code)
    return bool(result)


async def finish_once(r: redis.Redis, code: str) -> bool:
    key = _finished_key(code)
    created = await r.setnx(key, "1")
    if created:
        await r.expire(key, settings.redis_room_ttl_seconds)
    return bool(created)


async def are_all_finished(r: redis.Redis, code: str) -> bool:
    finished_count = await r.hget(_meta_key(code), "finished_count")
    total = await r.zcard(_players_key(code))
    try:
        finished_value = int(finished_count or 0)
    except ValueError:
        finished_value = 0
    return total > 0 and finished_value >= total


async def cleanup_room(r: redis.Redis, code: str) -> None:
    players_key = _players_key(code)
    sids = await r.zrange(players_key, 0, -1)
    keys = [_meta_key(code), players_key, _finished_key(code)]
    keys.extend([_player_key(code, sid) for sid in sids])
    if keys:
        await r.delete(*keys)
