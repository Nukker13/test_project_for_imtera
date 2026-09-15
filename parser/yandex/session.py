"""Получение рабочей сессии Яндекс.Карт: cookies, токены, метаданные карточки.

ТЗ описывало схему «Patchright открывает страницу → отдаёт cookies и токены в
curl_cffi». На практике всё оказалось наоборот, и это подтверждено замерами по
тестовой карточке (см. README, раздел про обоснование алгоритма):

* headless-браузер Яндекс отбивает — страница отвечает телом `limited`
  независимо от домена, прогрева сессии и наличия cookies;
* curl_cffi с impersonate="chrome" получает ту же страницу целиком (~1 МБ),
  вместе с блоком state-view и csrfToken, со статусом 200.

Причина в том, что под linux/arm64 нет настоящего Google Chrome, а патченный
chromium Patchright всё ещё отличим по набору признаков, тогда как curl_cffi
воспроизводит TLS/JA3-отпечаток Chrome точно. Поэтому основным путём получения
сессии сделан HTTP, а браузер сохранён как фолбэк — он включается, когда HTTP
упирается в блокировку, и остаётся страховкой на случай, если Яндекс начнёт
требовать исполнения JS.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from curl_cffi import requests as cffi_requests

from . import signature as sig
from .errors import (
    BlockedError,
    InvalidUrlError,
    LayoutChangedError,
    OrgNotFoundError,
    UpstreamTimeoutError,
)
from .state import extract_org_meta, extract_tokens, walk

log = logging.getLogger(__name__)

REVIEWS_API_RE = re.compile(r"/maps/api/business/fetchReviews")
STATE_VIEW_RE = re.compile(
    r'<script[^>]*class="state-view"[^>]*>(.*?)</script>', re.S
)
#: В карточках Яндекса идентификатор организации встречается и прямо в пути
#: (/maps/org/<slug>/<oid>/), и внутри poi-ссылки (oid=NNN или oid%3DNNN).
OID_PATH_RE = re.compile(r"/maps/org/(?:[^/]+/)?(\d+)")
OID_QUERY_RE = re.compile(r"oid(?:=|%3D)(\d+)", re.I)

CANONICAL_RE = re.compile(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"')
#: Ключи, которые есть в состоянии только у настоящей карточки организации.
ORG_STATE_MARKERS = ("seoname", "businessId")

CAPTCHA_MARKERS = ("showcaptcha", "smartcaptcha", "captcha-page")
#: Ответ антибот-защиты Яндекса на подозрительного клиента: короткое тело
#: со словом `limited` вместо страницы.
LIMITED_MARKER = "limited"

IMPERSONATE = os.getenv("CURL_IMPERSONATE", "chrome")
REQUEST_TIMEOUT = int(os.getenv("PARSER_REQUEST_TIMEOUT", "30"))
NAV_TIMEOUT_MS = int(os.getenv("PARSER_NAV_TIMEOUT_MS", "45000"))
#: Пустая строка = встроенный chromium Patchright. Под linux/arm64 настоящего
#: Google Chrome не существует; на amd64 можно выставить "chrome".
BROWSER_CHANNEL = os.getenv("PATCHRIGHT_CHANNEL", "").strip()
ACCEPT_LANGUAGE = "ru-RU,ru;q=0.9"


@dataclass
class YandexSession:
    """Всё, что нужно стратегиям сбора, независимо от способа получения."""

    canonical_url: str
    business_id: str
    csrf_token: str
    session_id: str | None
    org_meta: dict
    #: Живой HTTP-клиент с накопленными cookies. Прямая стратегия обязана
    #: переиспользовать именно его: новая сессия потеряет cookies и отпечаток.
    http: Any = None
    signature_scheme: str = sig.DEFAULT_SCHEME
    source: str = "http"
    cookies: dict = field(default_factory=dict)


def normalize_url(url: str) -> str:
    """Отсекает заведомо чужие ссылки до любых сетевых запросов."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError("Ссылка должна начинаться с http:// или https://")
    host = parsed.netloc.lower().removeprefix("www.")
    if not (
        host in ("yandex.ru", "yandex.com")
        or host.endswith((".yandex.ru", ".yandex.com"))
    ):
        raise InvalidUrlError("Ожидается ссылка на yandex.ru или yandex.com")
    if "/maps" not in parsed.path:
        raise InvalidUrlError("Ожидается ссылка на карточку организации в Яндекс.Картах")
    return url.strip()


def reviews_url_for(business_id: str) -> str:
    """Канонический адрес вкладки отзывов по идентификатору организации."""
    return f"https://yandex.ru/maps/org/{business_id}/reviews/"


def new_http_session():
    """HTTP-клиент с TLS-отпечатком Chrome.

    User-Agent намеренно не переопределяем: curl_cffi выставляет его сам под
    выбранный impersonate, и рассогласование UA с рукопожатием — первое, на чём
    палится клиент.
    """
    http = cffi_requests.Session(impersonate=IMPERSONATE)
    http.headers.update({"Accept-Language": ACCEPT_LANGUAGE})
    return http


def _guard_body(body: str, url: str) -> None:
    head = (body or "")[:4000].lower()
    if LIMITED_MARKER in head and len(body or "") < 1000:
        raise BlockedError(
            "Яндекс ограничил доступ (ответ `limited`) — сработала антибот-защита"
        )
    if any(marker in head for marker in CAPTCHA_MARKERS):
        raise BlockedError("Яндекс показал капчу вместо страницы организации")
    if not body:
        raise UpstreamTimeoutError(f"Пустой ответ от {url}")


def resolve_business_id(http, url: str) -> str:
    """Разворачивает короткую ссылку и достаёт идентификатор организации.

    Короткие ссылки вида /maps/-/CTxMzF5W приводят не к /maps/org/..., а к
    poi-адресу с параметром oid, поэтому идентификатор ищется и в пути, и в
    query конечного адреса.
    """
    match = OID_PATH_RE.search(url) or OID_QUERY_RE.search(url)
    if match:
        return match.group(1)

    try:
        response = http.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        raise UpstreamTimeoutError(f"Не удалось развернуть ссылку: {exc}") from exc

    # Идентификатор берём только из конечного адреса редиректа. Искать `oid` по
    # телу страницы нельзя: на общей странице карт в выдаче попадаются чужие
    # организации, и парсер молча возвращал бы случайную из них.
    final = response.url or url
    match = OID_PATH_RE.search(final) or OID_QUERY_RE.search(final)
    if match:
        return match.group(1)
    raise OrgNotFoundError(
        "По ссылке не удалось определить организацию — проверьте, что она ведёт на карточку"
    )


def assert_org_page(html: str, state: dict, business_id: str) -> None:
    """Проверяет, что открыта карточка организации, а не общая страница карт.

    Несуществующий идентификатор Яндекс не отдаёт ошибкой: он показывает обычные
    карты по адресу /maps/org/<id>/reviews/, и без этой проверки парсер заводил
    пустую организацию с названием «Карты» и нулями вместо отказа.

    Опорный признак — canonical: настоящая карточка канонизируется в собственный
    /maps/org/..., подменная — в корень /maps/.
    """
    canonical = CANONICAL_RE.search(html)
    if canonical and "/maps/org/" in canonical.group(1):
        return

    # Canonical может отсутствовать — тогда смотрим на состав состояния.
    if canonical is None:
        keys = {key for _, node in walk(state) if isinstance(node, dict) for key in node}
        if any(marker in keys for marker in ORG_STATE_MARKERS):
            return

    raise OrgNotFoundError(
        f"Организация с идентификатором {business_id} не найдена — "
        "Яндекс открыл общую страницу карт вместо карточки"
    )


def parse_state(html: str) -> dict:
    """Достаёт и разбирает блок состояния страницы."""
    match = STATE_VIEW_RE.search(html)
    if not match:
        raise LayoutChangedError(
            "На странице нет блока state-view — разметка Яндекс.Карт изменилась"
        )
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise LayoutChangedError(
            f"Блок state-view перестал быть валидным JSON: {exc}"
        ) from exc


def build_session(url: str) -> YandexSession:
    """Основной вход: HTTP-сессия, при блокировке — браузерный фолбэк."""
    normalize_url(url)
    http = new_http_session()
    business_id = resolve_business_id(http, url)
    canonical = reviews_url_for(business_id)

    try:
        response = http.get(canonical, timeout=REQUEST_TIMEOUT)
        _guard_body(response.text, canonical)
        html = response.text
    except BlockedError as exc:
        log.warning("HTTP-сессия заблокирована (%s), пробуем браузер", exc.message)
        return build_browser_session(url, business_id, canonical)

    return _session_from_html(html, business_id, canonical, http, source="http")


def _session_from_html(
    html: str, business_id: str, canonical: str, http, source: str
) -> YandexSession:
    state = parse_state(html)
    assert_org_page(html, state, business_id)
    tokens = extract_tokens(state)
    return YandexSession(
        canonical_url=canonical,
        business_id=business_id,
        csrf_token=tokens["csrf_token"],
        session_id=tokens["session_id"],
        org_meta=extract_org_meta(state, html),
        http=http,
        signature_scheme=sig.self_check(),
        source=source,
        cookies=_cookie_snapshot(http),
    )


def _cookie_snapshot(http) -> dict:
    """Снимок cookies для диагностики.

    Одно и то же имя приезжает и с .yandex.ru, и с .yandex.com, поэтому прямое
    приведение к dict падает на конфликте — обходим через сырые объекты jar.
    """
    if http is None:
        return {}
    snapshot: dict[str, str] = {}
    try:
        for cookie in http.cookies.jar:
            snapshot.setdefault(cookie.name, cookie.value or "")
    except Exception:  # noqa: BLE001 — снимок не критичен для работы парсера
        return {}
    return snapshot


def build_browser_session(url: str, business_id: str, canonical: str) -> YandexSession:
    """Фолбэк по ТЗ: страницу открывает Patchright, cookies уезжают в curl_cffi.

    Смысл ровно тот, что описан в задании: браузер исполняет JS-челленджи и
    формирует сессию, а дальше работает HTTP-клиент с теми же cookies.
    """
    import asyncio

    html, cookies, user_agent = asyncio.run(_browser_fetch(canonical))
    http = new_http_session()
    for name, value in cookies.items():
        http.cookies.set(name, value)
    if user_agent:
        http.headers.update({"User-Agent": user_agent})
    return _session_from_html(html, business_id, canonical, http, source="browser")


async def _browser_fetch(canonical: str) -> tuple[str, dict, str]:
    from patchright.async_api import async_playwright

    async with async_playwright() as pw:
        launch_kwargs: dict = {"headless": True}
        if BROWSER_CHANNEL:
            launch_kwargs["channel"] = BROWSER_CHANNEL
        browser = await pw.chromium.launch(**launch_kwargs)
        try:
            context = await browser.new_context(locale="ru-RU")
            page = await context.new_page()
            try:
                await page.goto(
                    canonical, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS
                )
                await page.wait_for_timeout(2500)
            except Exception as exc:  # noqa: BLE001
                raise UpstreamTimeoutError(
                    f"Браузер не смог открыть страницу: {exc}"
                ) from exc
            html = await page.content()
            _guard_body(html, canonical)
            cookies = {c["name"]: c["value"] for c in await context.cookies()}
            user_agent = await page.evaluate("() => navigator.userAgent")
            return html, cookies, user_agent
        finally:
            await browser.close()
