"""Подпись запросов к внутреннему API Яндекс.Карт (параметр `s`).

Запросы к `/maps/api/business/fetchReviews` подписаны: помимо csrfToken и
sessionId в query уезжает `s` — хэш от самих параметров запроса. Алгоритм —
djb2 в xor-варианте, снятый с фронтенд-бандла Яндекса, а не документированный
контракт. Отсюда два следствия, определяющих устройство этого модуля:

1. Точная канонизация (порядок ключей, кодирование, участвует ли сам `s`)
   достоверно не известна и может отличаться между версиями бандла. Поэтому
   вместо одной жёстко зашитой схемы здесь список кандидатов CANDIDATES и
   калибровка `calibrate()` по реальному запросу, снятому из живого браузера.
2. Алгоритм может поменяться в любой момент. `self_check()` ловит это на старте
   и при каждом прогоне, превращая «молчаливо неверная подпись» в явный
   SignatureMismatchError, по которому оркестратор уходит на браузерный фолбэк.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode

from .errors import SignatureMismatchError

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "real_request.json"

#: Параметр подписи никогда не участвует в вычислении самого себя.
SIGNATURE_KEY = "s"


def djb2_xor(text: str) -> int:
    """djb2 в xor-варианте, семантика JS `h = h * 33 ^ c` с приведением к uint32.

    В JS умножение идёт в double, а `^` приводит операнд к int32 — то есть
    перенос за 32-й бит теряется именно на шаге xor. Маска после xor даёт тот же
    результат, что маска после умножения, так как второй операнд всегда
    укладывается в младшие 32 бита.
    """
    h = 5381
    for char in text:
        h = ((h * 33) ^ ord(char)) & 0xFFFFFFFF
    return h


def _canon_sorted_urlencoded(params: dict) -> str:
    """`a=1&b=2` с сортировкой по ключу и обычным percent-кодированием."""
    items = sorted((k, str(v)) for k, v in params.items() if k != SIGNATURE_KEY)
    return urlencode(items)


def _canon_sorted_raw(params: dict) -> str:
    """То же, но без кодирования значений (кириллица и скобки как есть)."""
    items = sorted((k, str(v)) for k, v in params.items() if k != SIGNATURE_KEY)
    return "&".join(f"{k}={v}" for k, v in items)


def _canon_sorted_values_only(params: dict) -> str:
    """Конкатенация только значений в порядке сортировки ключей."""
    items = sorted((k, str(v)) for k, v in params.items() if k != SIGNATURE_KEY)
    return "".join(v for _, v in items)


def _canon_sorted_quoted(params: dict) -> str:
    """Сортировка по ключу, кодирование через quote (пробел как %20, не '+')."""
    items = sorted((k, str(v)) for k, v in params.items() if k != SIGNATURE_KEY)
    return "&".join(f"{k}={quote(v, safe='')}" for k, v in items)


#: Кандидаты канонизации, по которым идёт калибровка. Порядок — от самого
#: вероятного к наименее; первый совпавший с реальной подписью и используется.
CANDIDATES: dict[str, Callable[[dict], str]] = {
    "sorted_urlencoded": _canon_sorted_urlencoded,
    "sorted_raw": _canon_sorted_raw,
    "sorted_quoted": _canon_sorted_quoted,
    "sorted_values_only": _canon_sorted_values_only,
}

DEFAULT_SCHEME = "sorted_urlencoded"


def sign(params: dict, scheme: str = DEFAULT_SCHEME) -> str:
    """Возвращает значение параметра `s` для набора параметров запроса."""
    if scheme not in CANDIDATES:
        raise SignatureMismatchError(f"Неизвестная схема подписи: {scheme}")
    return str(djb2_xor(CANDIDATES[scheme](params)))


def calibrate(params: dict, expected_signature: str) -> str:
    """Определяет схему канонизации по реальному запросу из браузера.

    Возвращает имя совпавшей схемы. Если не совпала ни одна — значит Яндекс
    поменял алгоритм подписи, и прямые запросы работать не будут.
    """
    expected = str(expected_signature)
    for name, canon in CANDIDATES.items():
        if str(djb2_xor(canon(params))) == expected:
            return name
    raise SignatureMismatchError(
        "Ни одна известная схема подписи не воспроизвела реальный `s`. "
        "Алгоритм Яндекса изменился — нужен фолбэк на браузерную стратегию.",
        expected=expected,
        tried=list(CANDIDATES),
    )


def load_fixture() -> dict | None:
    """Читает снятый из браузера реальный запрос, если он есть."""
    if not FIXTURE_PATH.exists():
        return None
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def save_fixture(params: dict, signature: str) -> None:
    """Сохраняет живой подписанный запрос как эталон для самопроверки."""
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(
        json.dumps({"params": params, "s": str(signature)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def self_check() -> str:
    """Сверяет алгоритм с эталоном. Возвращает имя рабочей схемы.

    Без эталона проверить нечего — возвращаем схему по умолчанию и полагаемся на
    то, что ошибку поймает уже сам ответ Яндекса.
    """
    fixture = load_fixture()
    if not fixture:
        return DEFAULT_SCHEME
    return calibrate(fixture["params"], fixture["s"])
