"""Нормализация сырых отзывов Яндекса в контракт сервиса.

Второй из трёх уровней детекта поломки: каждый отзыв обязан дать id, оценку,
автора и дату. Единичные кривые записи — нормальная жизнь (у отзыва может не
быть текста), но если схему не проходит существенная доля выборки, значит формат
поехал целиком, и это уже LayoutChangedError, а не «просто мало данных».
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .errors import LayoutChangedError

log = logging.getLogger(__name__)

ID_KEYS = ("id", "reviewId", "uid")
TEXT_KEYS = ("text", "reviewText", "body", "comment")
RATING_KEYS = ("rating", "score", "stars", "ratingValue")
DATE_KEYS = ("updatedTime", "createdTime", "time", "date", "publicationDate")
AUTHOR_KEYS = ("author", "user", "profile")
AUTHOR_NAME_KEYS = ("name", "displayName", "publicName", "title")

#: Доля успешно разобранных записей, ниже которой считаем формат сломанным.
MIN_VALID_RATIO = 0.6


def _first(node: dict, keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in node and node[key] not in (None, ""):
            return node[key]
    return None


def _parse_date(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Яндекс отдаёт и секунды, и миллисекунды — различаем по порядку величины.
        seconds = value / 1000 if value > 1e11 else value
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            return _parse_date(int(raw))
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _author_name(node: dict) -> str | None:
    author = _first(node, AUTHOR_KEYS)
    if isinstance(author, dict):
        name = _first(author, AUTHOR_NAME_KEYS)
        return name if isinstance(name, str) else None
    return author if isinstance(author, str) else None


def normalize_review(raw: Any) -> dict | None:
    """Приводит один сырой отзыв к контракту. None — запись не распознана."""
    if not isinstance(raw, dict):
        return None
    review_id = _first(raw, ID_KEYS)
    rating = _first(raw, RATING_KEYS)
    if review_id is None or rating is None:
        return None
    try:
        rating = int(float(rating))
    except (TypeError, ValueError):
        return None
    if not 1 <= rating <= 5:
        return None
    reviewed_at = _parse_date(_first(raw, DATE_KEYS))
    if reviewed_at is None:
        return None
    text = _first(raw, TEXT_KEYS)
    return {
        "yandex_review_id": str(review_id),
        "author_name": _author_name(raw) or "Аноним",
        "rating": rating,
        "text": text if isinstance(text, str) else "",
        "reviewed_at": reviewed_at.isoformat(),
    }


def normalize_many(raws: list) -> list[dict]:
    """Нормализует пачку и проверяет, что формат в целом жив."""
    if not raws:
        return []
    result = [r for r in (normalize_review(raw) for raw in raws) if r]
    ratio = len(result) / len(raws)
    if ratio < MIN_VALID_RATIO:
        raise LayoutChangedError(
            f"Формат отзывов изменился: распознано {len(result)} из {len(raws)} записей"
        )
    if ratio < 1:
        log.warning("Пропущено %d записей из %d", len(raws) - len(result), len(raws))
    return result


def extract_reviews(payload: Any) -> list:
    """Вытаскивает список сырых отзывов из ответа fetchReviews."""
    if not isinstance(payload, dict):
        return []
    data = payload.get("data", payload)
    if isinstance(data, dict):
        for key in ("reviews", "items", "list"):
            if isinstance(data.get(key), list):
                return data[key]
    return []


def extract_total(payload: Any) -> int | None:
    """Заявленное Яндексом общее число отзывов, если оно есть в ответе."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return None
    params = data.get("params")
    if isinstance(params, dict) and isinstance(params.get("count"), int):
        return params["count"]
    return data["count"] if isinstance(data.get("count"), int) else None
