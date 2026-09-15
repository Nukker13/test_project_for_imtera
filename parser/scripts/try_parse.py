#!/usr/bin/env python
"""Автономный прогон парсера по одной ссылке — без Laravel, очереди и БД.

Главный инструмент проверки всего задания: показывает, действительно ли связка
браузер → подпись → прямые запросы пробивает защиту Яндекса.

    python scripts/try_parse.py "https://yandex.com/maps/-/CTxMzF5W"
    python scripts/try_parse.py <url> --json > out.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yandex import parser  # noqa: E402
from yandex.errors import ParserError  # noqa: E402


def print_human(result: dict) -> None:
    org = result["organization"]
    meta = result["meta"]
    reviews = result["reviews"]

    print("\n=== Организация ===")
    print(f"Название:          {org.get('name') or '—'}")
    print(f"Адрес:             {org.get('address') or '—'}")
    print(f"Средний рейтинг:   {org.get('rating_avg') or '—'}")
    print(f"Оценок:            {org.get('ratings_count') if org.get('ratings_count') is not None else '—'}")
    print(f"Отзывов:           {org.get('reviews_count') if org.get('reviews_count') is not None else '—'}")
    print(f"permalink:         {org.get('yandex_permalink')}")

    print("\n=== Прогон ===")
    print(f"Стратегия:         {meta['strategy_used']}{' (фолбэк)' if meta['degraded'] else ''}")
    if meta.get("fallback_reason"):
        print(f"Причина фолбэка:   {meta['fallback_reason']}")
    print(f"Источник сессии:   {meta['session_source']}")
    print(f"Схема подписи:     {meta.get('signature_scheme') or '—'}")
    print(f"Страниц:           {meta['pages_fetched']}")
    print(f"Собрано отзывов:   {meta['reviews_fetched']}")
    print(f"Заявлено Яндексом: {meta.get('total_reported') if meta.get('total_reported') is not None else '—'}")
    if meta.get("source_cap_reached"):
        print("Упёрлись в потолок выдачи источника (~600).")

    print(f"\n=== Первые 5 отзывов из {len(reviews)} ===")
    for review in reviews[:5]:
        text = (review["text"] or "").replace("\n", " ")
        if len(text) > 120:
            text = text[:120] + "…"
        print(f"  [{review['rating']}★] {review['reviewed_at'][:10]} "
              f"{review['author_name']}: {text or '(без текста)'}")


async def main() -> int:
    ap = argparse.ArgumentParser(description="Автономный прогон парсера Яндекс.Карт")
    ap.add_argument("url", help="Ссылка на карточку организации")
    ap.add_argument("--max-pages", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="Вывести сырой JSON результата")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        result = await parser.parse(args.url, max_pages=args.max_pages)
    except ParserError as exc:
        print(f"\nОШИБКА [{exc.code}]: {exc.message}", file=sys.stderr)
        if exc.context:
            print(f"Контекст: {exc.context}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
