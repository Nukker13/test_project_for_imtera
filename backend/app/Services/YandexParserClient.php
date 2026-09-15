<?php

namespace App\Services;

use App\Exceptions\ParserException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;

/**
 * Тонкий HTTP-клиент к Python-сервису парсера.
 *
 * Здесь сознательно нет ни одной детали про Яндекс: ни адресов эндпоинтов, ни
 * подписи, ни разбора разметки. Всё это живёт в Python-сервисе, а Laravel знает
 * только контракт «отдай ссылку — получи организацию, отзывы и метаданные».
 * Благодаря этому логика работы с внешним источником вынесена из контроллеров и
 * сервисов приложения, как того требует ТЗ.
 */
class YandexParserClient
{
    public function __construct(
        private readonly string $baseUrl,
        private readonly int $timeout,
    ) {
    }

    public static function fromConfig(): self
    {
        return new self(
            rtrim((string) config('parser.url'), '/'),
            (int) config('parser.timeout'),
        );
    }

    /**
     * Запускает разбор одной карточки.
     *
     * @return array{organization: array, reviews: array, meta: array}
     *
     * @throws ParserException
     */
    public function parse(string $url, ?int $maxPages = null): array
    {
        try {
            $response = Http::timeout($this->timeout)
                ->acceptJson()
                ->post("{$this->baseUrl}/parse", array_filter([
                    'url' => $url,
                    'max_pages' => $maxPages,
                ], static fn ($value) => $value !== null));
        } catch (ConnectionException $exception) {
            throw new ParserException(
                'PARSER_UNAVAILABLE',
                'Сервис парсинга недоступен. Проверьте, что контейнер python-service запущен.',
                previous: $exception,
            );
        }

        if ($response->successful()) {
            return $response->json();
        }

        // Сервис отдаёт свои ошибки структурировано — сохраняем код как есть,
        // чтобы UI мог показать осмысленный текст вместо HTTP-статуса.
        $payload = $response->json();
        if (is_array($payload) && isset($payload['error_code'])) {
            throw new ParserException(
                (string) $payload['error_code'],
                (string) ($payload['message'] ?? 'Парсер вернул ошибку без описания'),
            );
        }

        throw new ParserException(
            'PARSER_ERROR',
            "Сервис парсинга ответил HTTP {$response->status()}",
        );
    }
}
