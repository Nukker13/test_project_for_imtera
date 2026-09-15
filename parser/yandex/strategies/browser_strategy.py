"""Фолбэк: сбор отзывов скроллом с перехватом сетевых ответов.

Страховка на случай, когда прямые запросы невозможны: Яндекс поменял алгоритм
подписи, отбил запрос по фингерпринту или показал капчу в обход браузера. Здесь
подпись не нужна вообще — запросы формирует сам фронтенд Яндекса, а мы лишь
читаем их ответы. Платим за это скоростью: 600 отзывов набираются десятками
итераций скролла вместо двенадцати HTTP-запросов.
"""

from __future__ import annotations

import logging
import os

from patchright.async_api import async_playwright

from ..errors import BlockedError, LayoutChangedError, UpstreamTimeoutError
from ..normalizer import extract_reviews, extract_total, normalize_many
from ..session import (
    BROWSER_CHANNEL,
    CAPTCHA_MARKERS,
    NAV_TIMEOUT_MS,
    REVIEWS_API_RE,
    reviews_url_for,
)

log = logging.getLogger(__name__)

NAME = "browser"

MAX_SCROLLS = int(os.getenv("BROWSER_MAX_SCROLLS", "120"))
#: Сколько итераций подряд счётчик может не расти, прежде чем считаем ленту концом.
STALE_LIMIT = int(os.getenv("BROWSER_STALE_LIMIT", "4"))
SCROLL_PAUSE_MS = int(os.getenv("BROWSER_SCROLL_PAUSE_MS", "700"))

#: Контейнер ленты отзывов. Несколько вариантов, потому что класс — не контракт.
PANEL_SELECTORS = (
    ".scroll__container",
    ".business-reviews-card-view__reviews-container",
    "[class*='reviews-view']",
)


async def collect(business_id: str, max_reviews: int, headless: bool = True) -> dict:
    """Открывает вкладку отзывов и скроллит её, собирая перехваченные ответы."""
    async with async_playwright() as pw:
        launch_kwargs = {"headless": headless}
        if BROWSER_CHANNEL:
            launch_kwargs["channel"] = BROWSER_CHANNEL
        browser = await pw.chromium.launch(**launch_kwargs)
        try:
            context = await browser.new_context(locale="ru-RU")
            page = await context.new_page()
            return await _scroll_and_capture(page, reviews_url_for(business_id), max_reviews)
        finally:
            await browser.close()


async def _scroll_and_capture(page, url: str, max_reviews: int) -> dict:
    payloads: list = []

    async def on_response(response):
        if not REVIEWS_API_RE.search(response.url):
            return
        try:
            payloads.append(await response.json())
        except Exception:  # noqa: BLE001
            log.debug("Перехваченный ответ не разобрался как JSON")

    page.on("response", on_response)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
    except Exception as exc:  # noqa: BLE001
        raise UpstreamTimeoutError(f"Не удалось открыть страницу отзывов: {exc}") from exc

    if any(marker in page.url for marker in CAPTCHA_MARKERS):
        raise BlockedError("Яндекс показал капчу при заходе на вкладку отзывов")

    panel = await _find_panel(page)
    seen: set[str] = set()
    reviews: list[dict] = []
    total: int | None = None
    stale = 0

    for _ in range(MAX_SCROLLS):
        total = total if total is not None else _first_total(payloads)
        added = _drain(payloads, seen, reviews)
        stale = 0 if added else stale + 1

        if stale >= STALE_LIMIT:
            break
        if len(reviews) >= max_reviews:
            break
        if total is not None and len(reviews) >= total:
            break

        await _scroll(page, panel)
        await page.wait_for_timeout(SCROLL_PAUSE_MS)

    _drain(payloads, seen, reviews)

    if not reviews:
        raise LayoutChangedError(
            "Скролл ленты не дал ни одного отзыва — вероятно, изменилась разметка"
        )

    log.info("Браузерная стратегия: собрано %d отзывов", len(reviews))
    return {
        "reviews": reviews[:max_reviews],
        "total_reported": total,
        "pages_fetched": len(seen) // 50 or 1,
        "strategy": NAME,
    }


def _first_total(payloads: list) -> int | None:
    for payload in payloads:
        total = extract_total(payload)
        if total is not None:
            return total
    return None


def _drain(payloads: list, seen: set, reviews: list) -> int:
    """Переносит накопленные перехваченные ответы в результат, дедуплицируя."""
    added = 0
    while payloads:
        payload = payloads.pop(0)
        batch = normalize_many(extract_reviews(payload))
        for review in batch:
            if review["yandex_review_id"] in seen:
                continue
            seen.add(review["yandex_review_id"])
            reviews.append(review)
            added += 1
    return added


async def _find_panel(page):
    for selector in PANEL_SELECTORS:
        element = await page.query_selector(selector)
        if element:
            return element
    # Не нашли контейнер — скроллим окно целиком. Это хуже, но рабочий вариант,
    # поэтому не ошибка: настоящую поломку поймает пустой результат ниже.
    log.warning("Контейнер ленты отзывов не найден, скроллим страницу целиком")
    return None


async def _scroll(page, panel) -> None:
    if panel is not None:
        await panel.evaluate("el => el.scrollBy(0, el.scrollHeight)")
    else:
        await page.mouse.wheel(0, 3000)
