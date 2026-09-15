"""HTTP-обёртка над парсером.

Сервис синхронный и намеренно «глупый»: собственной очереди у него нет, потому
что очередь уже есть на стороне Laravel. Один POST /parse = один прогон, Laravel
job ждёт ответ с длинным таймаутом.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from yandex import parser, signature
from yandex.errors import ParserError

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("parser.api")

app = FastAPI(title="Yandex Maps Reviews Parser", version="1.0.0")


class ParseRequest(BaseModel):
    url: str = Field(..., description="Ссылка на карточку организации в Яндекс.Картах")
    max_pages: int | None = Field(None, ge=1, le=40)


@app.get("/health")
def health() -> dict:
    """Живость сервиса плюс состояние самопроверки подписи."""
    try:
        scheme = signature.self_check()
        return {"status": "ok", "signature_scheme": scheme, "signature_ok": True}
    except ParserError as exc:
        # Сломанная подпись не делает сервис нерабочим — есть фолбэк, поэтому
        # health остаётся ok, но факт отражаем честно.
        return {"status": "ok", "signature_ok": False, "detail": exc.message}


@app.post("/parse")
async def parse_endpoint(request: ParseRequest):
    log.info("Запрос на парсинг: %s", request.url)
    try:
        return await parser.parse(request.url, max_pages=request.max_pages)
    except ParserError as exc:
        log.warning("Парсинг не удался: %s — %s", exc.code, exc.message)
        return JSONResponse(status_code=422, content=exc.to_payload())
    except Exception as exc:  # noqa: BLE001
        log.exception("Непредвиденная ошибка парсера")
        return JSONResponse(status_code=500, content=parser.error_payload(exc))
