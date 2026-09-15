"""Оркестратор парсинга: сессия → прямые запросы → при неудаче браузерный скролл.

Единственное место, где принимается решение о деградации. Правило простое:
ошибки из RECOVERABLE (подпись, бан, таймаут) означают «этим способом не вышло,
попробуем другим», а LayoutChangedError означает «источник изменился» — от этого
браузерный скролл не спасёт, поэтому такая ошибка пробрасывается сразу.

Деградация двухступенчатая и происходит на двух разных уровнях:
  1. session.build_session сам уходит на браузер, если HTTP-запрос страницы
     упёрся в блокировку (браузер отдаёт cookies обратно в curl_cffi — ровно
     схема из ТЗ);
  2. если не работают уже сами прямые запросы, подключается browser_strategy,
     которая собирает отзывы скроллом и подпись не использует вовсе.
"""

from __future__ import annotations

import asyncio
import logging
import os

from .errors import RECOVERABLE, LayoutChangedError, OrgNotFoundError, ParserError
from .session import YandexSession, build_session, normalize_url
from .strategies import api_strategy, browser_strategy

log = logging.getLogger(__name__)

MAX_PAGES = int(os.getenv("YANDEX_MAX_PAGES", "12"))
PAGE_SIZE = int(os.getenv("YANDEX_PAGE_SIZE", "50"))


async def parse(url: str, max_pages: int | None = None) -> dict:
    """Полный прогон по одной карточке организации."""
    normalize_url(url)
    limit_pages = max_pages or MAX_PAGES
    max_reviews = limit_pages * PAGE_SIZE

    # build_session синхронный (curl_cffi), уводим его с event loop, чтобы не
    # блокировать обработчик FastAPI на время сетевых запросов.
    session = await asyncio.to_thread(build_session, url)

    degraded = session.source == "browser"
    fallback_reason = "PAGE_BLOCKED" if degraded else None

    try:
        result = await asyncio.to_thread(api_strategy.collect, session, limit_pages)
    except LayoutChangedError:
        raise
    except RECOVERABLE as exc:
        log.warning("Прямая стратегия не сработала (%s), уходим на фолбэк", exc.code)
        degraded = True
        fallback_reason = exc.code
        result = await browser_strategy.collect(session.business_id, max_reviews=max_reviews)

    organization = _build_organization(session, result)
    _sanity_check(organization, result)

    return {
        "organization": organization,
        "reviews": result["reviews"],
        "meta": {
            "strategy_used": result["strategy"],
            "session_source": session.source,
            "degraded": degraded,
            "fallback_reason": fallback_reason,
            "pages_fetched": result["pages_fetched"],
            "reviews_fetched": len(result["reviews"]),
            "total_reported": result.get("total_reported"),
            "signature_scheme": session.signature_scheme,
            "source_cap_reached": len(result["reviews"]) >= max_reviews,
        },
    }


def _build_organization(session: YandexSession, result: dict) -> dict:
    meta = dict(session.org_meta)
    reported = result.get("total_reported")
    return {
        "yandex_permalink": session.business_id,
        "url": session.canonical_url,
        "name": meta.get("name"),
        "address": meta.get("address"),
        "rating_avg": meta.get("rating_avg"),
        # Количество оценок и количество отзывов — два независимых числа, как
        # требует ТЗ. reviews_count берём из ответа API, когда он его вернул:
        # это самое точное из доступных значений.
        "ratings_count": meta.get("ratings_count"),
        "reviews_count": reported if reported is not None else meta.get("reviews_count"),
    }


def _sanity_check(organization: dict, result: dict) -> None:
    """Третий уровень детекта: результат, который не может быть правдой."""
    reported = result.get("total_reported") or organization.get("reviews_count")
    if reported and not result["reviews"]:
        raise LayoutChangedError(
            f"Яндекс сообщает о {reported} отзывах, но собрать не удалось ни одного"
        )
    if not organization.get("yandex_permalink"):
        raise LayoutChangedError("Не удалось определить идентификатор организации")

    # Полностью пустая витрина при нуле отзывов — это не «организация без
    # отзывов», а признак того, что открыта не та страница. У настоящей карточки
    # хотя бы адрес, рейтинг или счётчик оценок заполнен.
    has_profile = any(
        organization.get(key) is not None
        for key in ("address", "rating_avg", "ratings_count")
    )
    if not has_profile and not result["reviews"]:
        raise OrgNotFoundError(
            "По ссылке не нашлось карточки организации: нет ни рейтинга, ни адреса, "
            "ни отзывов"
        )


def error_payload(exc: Exception) -> dict:
    """Приводит любое исключение к контракту ошибки сервиса."""
    if isinstance(exc, ParserError):
        return exc.to_payload()
    return {
        "error_code": "PARSER_ERROR",
        "message": f"Непредвиденная ошибка парсера: {exc}",
        "context": {},
    }
