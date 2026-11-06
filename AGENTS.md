# AGENTS.md

Рабочий контекст для ИИ-агентов (Claude Code, Codex и др.) и для людей, которые
впервые открывают репозиторий. Подробности по архитектуре — в [README.md](README.md),
требования — в [docs/requirements.md](docs/requirements.md), как шла работа с агентом —
в [docs/ai-workflow.md](docs/ai-workflow.md).

## Что это

Парсер отзывов из карточек Яндекс.Карт, тестовое задание. Laravel 13 + Sanctum
(`backend/`), Vue 3 Composition API (`frontend/`), Python-сервис на curl_cffi +
Patchright (`parser/`), PostgreSQL, Redis, Docker Compose.

## Главная граница

Всё знание о Яндексе — эндпоинты, подпись `s`, CSRF, разметка, детект поломки —
живёт **только** в `parser/`. Laravel знает один контракт: «отдай ссылку, получи
организацию, отзывы и метаданные» (`backend/app/Services/YandexParserClient.php`).
Не переносить логику парсинга в контроллеры, сервисы или джобы Laravel.

## Команды

```bash
docker compose up --build                     # всё локально: app :8000, frontend :5173, parser :8001
docker compose exec python-service python scripts/try_parse.py "https://yandex.com/maps/-/CTxMzF5W"
docker compose exec python-service python -m pytest tests/ -q
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build   # прод
```

Миграции и сид выполняются при старте `app`. Логин: `admin@imtera.test` / `password`.

## Эталон проверки

Любую правку парсера проверять на карточке `https://yandex.com/maps/-/CTxMzF5W`
(Hummus Kimchi, Ереван): рейтинг 5.0, оценок 477, отзывов 172, собирается за 4
страницы. Если числа разошлись — сначала выяснить, поменялась карточка или сломался
парсер, и только потом что-то чинить.

## Конвенции

* Комментарии, сообщения коммитов и документация — на русском. Комментарий объясняет
  «почему», а не «что».
* Запись в БД только через `ReviewsUpsertService`: upsert по внешним id организации
  и отзыва, без дублей. Каждый прогон — строка в `parse_runs`, полных снимков нет.
* Ошибки парсера — только через коды из README («Коды ошибок»). Молчаливый пустой
  результат недопустим: лучше `LAYOUT_CHANGED`, чем ноль отзывов без объяснения.
* У джобы `$tries = 1`, автоматических ретраев нет — намеренно, автоповтор после
  бана усугубляет блокировку.
* User-Agent вручную не задаётся: его выставляет `impersonate` в curl_cffi, иначе
  заголовок противоречит TLS-отпечатку.

## Сознательные упрощения

Согласованы до начала работы из-за срока, не «чинить» без запроса:

* автотестов нет, кроме теста подписи (`parser/tests/test_signature.py`);
* ротация прокси/UA и троттлинг под нагрузкой описаны в README, но не реализованы;
* версионных снимков нет — только лог прогонов `parse_runs`.

## Деплой: на что уже наступали

* Сборка не помещается в 0.5 ГБ RAM — нужен инстанс покрупнее (использовался ARM, 10 ГБ).
* Порты 80 и 443 открыть и в облачном firewall, и в firewalld на хосте, иначе
  ACME-челлендж Let's Encrypt падает с «Timeout during connect».
* `docker compose -f docker-compose.prod.yml` без `--env-file .env.prod` запустится
  с пустыми переменными.
* Секреты и ключи не коммитить: `.env*`, `*.key`, `*.pem` в `.gitignore` намеренно.
