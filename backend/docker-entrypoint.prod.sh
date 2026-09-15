#!/usr/bin/env bash
set -e

# APP_KEY на проде задаётся через окружение и не должен генерироваться заново при
# каждом старте: смена ключа инвалидирует все сессии.
if [ -z "${APP_KEY}" ]; then
    echo "ОШИБКА: APP_KEY не задан. Сгенерируйте его один раз и пропишите в .env.prod:" >&2
    echo "  docker compose -f docker-compose.prod.yml run --rm app php artisan key:generate --show" >&2
    exit 1
fi

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    php artisan migrate --force
    php artisan db:seed --force
fi

# Кэши собираются на старте, а не в образе: они зависят от переменных окружения,
# которые известны только в момент запуска контейнера.
php artisan config:cache
php artisan route:cache

exec "$@"
