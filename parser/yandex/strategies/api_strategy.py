"""Прямые подписанные запросы к fetchReviews через curl_cffi — основной путь.

Три вещи, без которых эндпоинт не отвечает данными, и каждая была установлена
экспериментально (см. README):

1. **TLS-отпечаток.** Обычный requests/httpx отсекается на рукопожатии, поэтому
   клиент только curl_cffi с impersonate="chrome".
2. **Подпись `s`** — djb2-xor по query-строке с отсортированными ключами. При
   неверной подписи Яндекс отвечает голым `Bad Request` без пояснений.
3. **Обновление csrfToken.** Токен со страницы одноразовый и просроченный: на
   первый запрос Яндекс отвечает `{"csrfToken": "<новый>"}` вместо данных, и
   запрос нужно повторить с выданным токеном. Без этого цикла прямые запросы не
   работают вообще — это и есть главное недостающее звено схемы из ТЗ.
"""

from __future__ import annotations

import logging
import os
import random
import time

from .. import signature as sig
from ..errors import BlockedError, LayoutChangedError, UpstreamTimeoutError
from ..normalizer import extract_reviews, extract_total, normalize_many
from ..session import YandexSession

log = logging.getLogger(__name__)

API_URL = "https://yandex.ru/maps/api/business/fetchReviews"
PAGE_SIZE = int(os.getenv("YANDEX_PAGE_SIZE", "50"))
MAX_PAGES = int(os.getenv("YANDEX_MAX_PAGES", "12"))
DELAY_MIN_MS = int(os.getenv("PARSER_DELAY_MIN_MS", "400"))
DELAY_MAX_MS = int(os.getenv("PARSER_DELAY_MAX_MS", "1200"))
REQUEST_TIMEOUT = int(os.getenv("PARSER_REQUEST_TIMEOUT", "30"))
LOCALE = os.getenv("YANDEX_LOCALE", "ru_RU")
#: Сортировка по времени, один проход. Добор через другие сортировки сознательно
#: не делается: потолок выдачи Яндекса всё равно ~600, а запросов втрое больше.
RANKING = os.getenv("YANDEX_RANKING", "by_time")
#: Сколько раз подряд готовы обновлять токен в рамках одной страницы.
MAX_TOKEN_REFRESH = 4

NAME = "api"


def _sleep_between_requests() -> None:
    """Пауза с джиттером: ровный интервал сам по себе является признаком бота."""
    time.sleep(random.uniform(DELAY_MIN_MS, DELAY_MAX_MS) / 1000)


def _build_params(session: YandexSession, page: int) -> dict:
    params = {
        "ajax": "1",
        "businessId": session.business_id,
        "csrfToken": session.csrf_token,
        "locale": LOCALE,
        "page": str(page),
        "pageSize": str(PAGE_SIZE),
        "ranking": RANKING,
    }
    if session.session_id:
        params["sessionId"] = session.session_id
    params[sig.SIGNATURE_KEY] = sig.sign(params, session.signature_scheme)
    return params


def _headers(session: YandexSession) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Referer": session.canonical_url,
        "X-Requested-With": "XMLHttpRequest",
    }


def fetch_page(session: YandexSession, page: int) -> dict:
    """Одна страница отзывов с прозрачным обновлением csrfToken.

    Возвращает распарсенный JSON с ключом `data`. Побочный эффект — актуализация
    session.csrf_token, чтобы следующая страница стартовала со свежим токеном.
    """
    last_status = None
    for attempt in range(MAX_TOKEN_REFRESH):
        params = _build_params(session, page)
        try:
            response = session.http.get(
                API_URL, params=params, headers=_headers(session), timeout=REQUEST_TIMEOUT
            )
        except Exception as exc:  # noqa: BLE001
            raise UpstreamTimeoutError(f"Запрос к fetchReviews не удался: {exc}") from exc

        last_status = response.status_code
        if response.status_code in (403, 429):
            raise BlockedError(
                f"Яндекс ответил {response.status_code} — сработала антибот-защита"
            )
        if response.status_code >= 500:
            raise UpstreamTimeoutError(f"Яндекс ответил {response.status_code}")

        body = response.text or ""
        if "captcha" in body[:2000].lower():
            raise BlockedError("В ответе на fetchReviews пришла капча")

        payload = _as_json(response, body)

        # Ответ вида {"csrfToken": "..."} — не данные, а выдача свежего токена.
        if isinstance(payload, dict) and "csrfToken" in payload and "data" not in payload:
            session.csrf_token = payload["csrfToken"]
            log.debug("Страница %s: получен свежий csrfToken, повтор запроса", page)
            continue

        if isinstance(payload, dict) and payload.get("data"):
            # Запрос принят Яндексом — фиксируем его как эталон подписи. Это
            # делает самопроверку осмысленной: сверяемся не с придуманным
            # примером, а с запросом, который источник реально принял.
            _remember_signature(params)

        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            raise LayoutChangedError(
                f"fetchReviews отклонил запрос: {error.get('message') or error}"
            )

        if response.status_code == 400:
            # Голый `Bad Request` без тела — признак неверной подписи: Яндекс
            # поменял алгоритм, и прямой путь дальше не пройдёт.
            raise sig.SignatureMismatchError(
                "fetchReviews отвечает Bad Request — подпись запроса больше не принимается"
            )
        if response.status_code != 200:
            raise LayoutChangedError(
                f"Неожиданный ответ fetchReviews: HTTP {response.status_code}"
            )
        return payload

    raise BlockedError(
        f"Яндекс не выдал рабочий csrfToken за {MAX_TOKEN_REFRESH} попыток "
        f"(последний статус {last_status})"
    )


def _remember_signature(params: dict) -> None:
    try:
        sig.save_fixture(params, params[sig.SIGNATURE_KEY])
    except Exception:  # noqa: BLE001 — не смогли записать эталон, не беда
        log.debug("Не удалось сохранить эталон подписи")


def _as_json(response, body: str):
    try:
        return response.json()
    except Exception as exc:  # noqa: BLE001
        if response.status_code == 400:
            raise sig.SignatureMismatchError(
                "fetchReviews отвечает Bad Request — подпись запроса больше не принимается"
            ) from exc
        raise LayoutChangedError(
            "Ответ fetchReviews перестал быть JSON — вероятно, изменился эндпоинт"
        ) from exc


def collect(session: YandexSession, max_pages: int | None = None) -> dict:
    """Проходит страницы отзывов и возвращает нормализованный результат."""
    limit = max_pages or MAX_PAGES
    seen: set[str] = set()
    reviews: list[dict] = []
    total: int | None = None
    pages_fetched = 0

    for page in range(1, limit + 1):
        payload = fetch_page(session, page)
        pages_fetched += 1
        if total is None:
            total = extract_total(payload)

        raw_batch = extract_reviews(payload)
        if not raw_batch:
            if page == 1 and total:
                raise LayoutChangedError(
                    f"Яндекс заявляет {total} отзывов, но не вернул ни одного"
                )
            break

        batch = normalize_many(raw_batch)
        fresh = [r for r in batch if r["yandex_review_id"] not in seen]
        seen.update(r["yandex_review_id"] for r in fresh)
        reviews.extend(fresh)

        if len(raw_batch) < PAGE_SIZE:
            break
        if total is not None and len(reviews) >= total:
            break
        if page < limit:
            _sleep_between_requests()

    log.info("Прямая стратегия: %d отзывов за %d страниц", len(reviews), pages_fetched)
    return {
        "reviews": reviews,
        "total_reported": total,
        "pages_fetched": pages_fetched,
        "strategy": NAME,
    }
