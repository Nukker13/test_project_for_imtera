# Laravel 13 тянет Symfony 8, которому нужен PHP >= 8.4.1.
FROM php:8.4-cli

# pdo_pgsql — для Postgres, остальное нужно самому Laravel и composer.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git unzip libpq-dev libzip-dev libicu-dev \
    && docker-php-ext-install pdo_pgsql pgsql zip intl opcache \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# Зависимости ставятся отдельным слоем от кода, чтобы правка приложения не
# приводила к повторной установке всего вендора.
COPY composer.json composer.lock ./
RUN composer install --no-interaction --no-scripts --no-autoloader --prefer-dist

COPY . .
RUN composer dump-autoload --optimize

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && chmod -R 777 storage bootstrap/cache

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
# Напрямую через php -S: artisan serve фильтрует окружение дочернего процесса
# и переменные из docker-compose не доезжают до приложения.
CMD ["php", "-S", "0.0.0.0:8000", "-t", "public", "server.php"]
