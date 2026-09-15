"""Типизированные ошибки парсера.

Коды из ERROR_CODES уезжают без изменений в Laravel (parse_runs.error_code) и
дальше в UI, поэтому они часть публичного контракта сервиса: переименование кода
ломает текст ошибки, который видит пользователь.
"""


class ParserError(Exception):
    """База для всех ошибок парсера. `code` попадает в HTTP-ответ."""

    code = "PARSER_ERROR"
    message = "Не удалось разобрать карточку организации"

    def __init__(self, message: str | None = None, **context):
        self.message = message or self.message
        self.context = context
        super().__init__(self.message)

    def to_payload(self) -> dict:
        return {"error_code": self.code, "message": self.message, "context": self.context}


class InvalidUrlError(ParserError):
    code = "INVALID_URL"
    message = "Ссылка не похожа на карточку организации в Яндекс.Картах"


class OrgNotFoundError(ParserError):
    code = "ORG_NOT_FOUND"
    message = "Организация по этой ссылке не найдена"


class BlockedError(ParserError):
    """Яндекс показал капчу либо ответил 403/429."""

    code = "BLOCKED_CAPTCHA"
    message = "Яндекс заблокировал запрос (капча или ограничение по частоте)"


class SignatureMismatchError(ParserError):
    """Самопроверка подписи не сошлась — Яндекс поменял алгоритм."""

    code = "SIGNATURE_MISMATCH"
    message = "Алгоритм подписи запросов Яндекса изменился"


class LayoutChangedError(ParserError):
    """Не нашли ожидаемый блок/ключи или данные не прошли схему."""

    code = "LAYOUT_CHANGED"
    message = "Разметка страницы Яндекс.Карт изменилась, парсер требует обновления"


class UpstreamTimeoutError(ParserError):
    code = "UPSTREAM_TIMEOUT"
    message = "Яндекс не ответил за отведённое время"


#: Ошибки, при которых имеет смысл деградировать на браузерную стратегию.
#: LayoutChangedError сюда сознательно не входит: если поехала разметка
#: state-view, браузерный скролл упрётся ровно в ту же проблему.
RECOVERABLE = (SignatureMismatchError, BlockedError, UpstreamTimeoutError)
