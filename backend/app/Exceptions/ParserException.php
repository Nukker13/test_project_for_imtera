<?php

namespace App\Exceptions;

use RuntimeException;
use Throwable;

/**
 * Ошибка парсинга с машиночитаемым кодом.
 *
 * Код приезжает из Python-сервиса (BLOCKED_CAPTCHA, LAYOUT_CHANGED и т.д.),
 * сохраняется в parse_runs и доезжает до интерфейса, где превращается в
 * понятную человеку формулировку. Благодаря этому пользователь видит «Яндекс
 * показал капчу», а не «ошибка 500».
 */
class ParserException extends RuntimeException
{
    public function __construct(
        public readonly string $errorCode,
        string $message,
        ?Throwable $previous = null,
    ) {
        parent::__construct($message, 0, $previous);
    }
}
