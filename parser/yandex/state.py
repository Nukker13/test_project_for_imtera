"""Извлечение данных организации из состояния страницы Яндекс.Карт.

Страница отдаёт своё начальное состояние в блоке `<script class="state-view">` — большой
вложенный JSON без стабильного публичного контракта. Точные пути до нужных полей
меняются вместе с бандлом, поэтому здесь сознательно не используются жёсткие
пути вида `data.ctx.business.rating.score`: вместо них — поиск по дереву с
набором известных синонимов ключей. Это переживает перестановку блоков и ломается
только при реальном переименовании полей, что и есть настоящая смена разметки.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator

from .errors import LayoutChangedError

#: Синонимы ключей, под которыми Яндекс в разных версиях отдаёт одно и то же.
CSRF_KEYS = ("csrfToken", "csrf_token", "csrf")
SESSION_KEYS = ("sessionId", "session_id", "sid")
BUSINESS_KEYS = ("businessId", "business_id", "permalink", "oid")
SCORE_KEYS = ("score", "ratingValue", "averageRating", "rating")
RATINGS_COUNT_KEYS = ("ratings", "ratingCount", "ratingsCount", "votes")
REVIEWS_COUNT_KEYS = ("reviews", "reviewCount", "reviewsCount", "count")
NAME_KEYS = ("name", "title", "displayName")
ADDRESS_KEYS = ("address", "fullAddress", "addressLine")


def walk(node: Any, path: tuple = ()) -> Iterator[tuple[tuple, Any]]:
    """Обходит вложенные dict/list, отдавая (путь, значение) для каждого узла."""
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk(value, path + (index,))


def find_first(root: Any, keys: tuple[str, ...], predicate=None) -> Any:
    """Первое значение по любому из ключей `keys`, удовлетворяющее predicate."""
    for path, node in walk(root):
        if not isinstance(node, dict):
            continue
        for key in keys:
            if key not in node:
                continue
            value = node[key]
            if predicate is None or predicate(value):
                return value
    return None


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def extract_tokens(state: Any) -> dict:
    """Достаёт csrfToken / sessionId / businessId из состояния страницы.

    csrfToken обязателен: без него прямые запросы невозможны в принципе.
    sessionId и businessId могут прийти позже из перехваченного запроса, поэтому
    их отсутствие здесь ошибкой не считается.
    """
    csrf = find_first(state, CSRF_KEYS, _is_nonempty_str)
    if not csrf:
        raise LayoutChangedError(
            "В состоянии страницы не найден csrfToken — разметка Яндекс.Карт изменилась"
        )
    business = find_first(state, BUSINESS_KEYS, lambda v: _is_nonempty_str(v) or _is_count(v))
    return {
        "csrf_token": csrf,
        "session_id": find_first(state, SESSION_KEYS, _is_nonempty_str),
        "business_id": str(business) if business is not None else None,
    }


def extract_org_meta(state: Any, html: str | None = None) -> dict:
    """Собирает витрину организации: название, адрес, рейтинг, оба счётчика.

    ТЗ требует показывать количество оценок и количество отзывов раздельно и
    точными числами, поэтому они ищутся как два независимых поля, а не выводятся
    одно из другого.
    """
    rating_node = _find_rating_node(state)
    meta = {
        "name": extract_name(html) or find_first(state, NAME_KEYS, _is_nonempty_str),
        "address": find_first(state, ADDRESS_KEYS, _is_nonempty_str),
        "rating_avg": None,
        "ratings_count": None,
        "reviews_count": None,
    }
    if rating_node:
        meta["rating_avg"] = _first_of(rating_node, SCORE_KEYS, _is_number)
        meta["ratings_count"] = _first_of(rating_node, RATINGS_COUNT_KEYS, _is_count)
        meta["reviews_count"] = _first_of(rating_node, REVIEWS_COUNT_KEYS, _is_count)
    return meta


#: Хлебные крошки и og:title — куда более надёжные источники названия, чем поиск
#: ключа `name` по внутреннему состоянию: там это слово встречается десятки раз в
#: несвязанных узлах (счётчики, эксперименты, конфиги).
BREADCRUMB_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)
OG_TITLE_RE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]+)"')
#: Заголовок вкладки отзывов: Отзывы о «Название» на ... — Яндекс Карты
QUOTED_NAME_RE = re.compile(r"[«\"]([^»\"]{2,120})[»\"]")


def extract_name(html: str | None) -> str | None:
    """Название организации из хлебных крошек, иначе из og:title."""
    if not html:
        return None
    for block in BREADCRUMB_RE.findall(html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "BreadcrumbList":
            continue
        items = data.get("itemListElement") or []
        # Последняя крошка — сама организация.
        for entry in reversed(items):
            name = (entry.get("item") or {}).get("name") if isinstance(entry, dict) else None
            if _is_nonempty_str(name):
                return name.strip()
    og = OG_TITLE_RE.search(html)
    if og:
        quoted = QUOTED_NAME_RE.search(og.group(1))
        if quoted:
            return quoted.group(1).strip()
    return None


def _first_of(node: dict, keys: tuple[str, ...], predicate) -> Any:
    for key in keys:
        if key in node and predicate(node[key]):
            return node[key]
    return None


def _find_rating_node(state: Any) -> dict | None:
    """Ищет узел, где рейтинг и счётчики лежат вместе.

    Якорь — совместное присутствие оценки и хотя бы одного счётчика: отдельно
    взятый ключ `score` или `reviews` в этом JSON встречается в десятке
    несвязанных мест, а их пара практически однозначно указывает на блок рейтинга
    организации.
    """
    best = None
    for _, node in walk(state):
        if not isinstance(node, dict):
            continue
        score = _first_of(node, SCORE_KEYS, _is_number)
        if score is None or not (0 < score <= 5):
            continue
        ratings = _first_of(node, RATINGS_COUNT_KEYS, _is_count)
        reviews = _first_of(node, REVIEWS_COUNT_KEYS, _is_count)
        if ratings is None and reviews is None:
            continue
        # Предпочитаем узел, где есть оба счётчика сразу.
        if ratings is not None and reviews is not None:
            return node
        best = best or node
    return best
