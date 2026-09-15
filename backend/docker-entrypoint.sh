#!/usr/bin/env bash
set -e

# .env в образ не кладётся (он в .gitignore), поэтому при первом старте
# собираем его из примера — иначе artisan откажется работать.
if [ ! -f .env ]; then
    cp .env.example .env
fi

if ! grep -q '^APP_KEY=base64:' .env; then
    php artisan key:generate --force
fi

# Веб-процесс отвечает за схему БД и сид; воркер очереди этого не делает, чтобы
# два контейнера не пытались мигрировать одновременно.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    php artisan migrate --force
    php artisan db:seed --force
fi

exec "$@"
