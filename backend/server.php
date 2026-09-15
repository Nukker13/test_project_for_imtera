<?php

/**
 * Роутер для встроенного веб-сервера PHP.
 *
 * Запускаем приложение через `php -S` напрямую, а не через `php artisan serve`:
 * artisan serve поднимает сервер дочерним процессом и передаёт ему лишь
 * ограниченный список переменных окружения, из-за чего настройки из
 * docker-compose (подключение к БД, Redis, адрес парсера) до приложения не
 * доходят и оно молча откатывается на значения из .env.
 */

$uri = urldecode(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH));

// Существующие файлы (статика) отдаём как есть, остальное — в Laravel.
if ($uri !== '/' && file_exists(__DIR__.'/public'.$uri)) {
    return false;
}

require_once __DIR__.'/public/index.php';
