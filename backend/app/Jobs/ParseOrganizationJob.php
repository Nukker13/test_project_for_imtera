<?php

namespace App\Jobs;

use App\Exceptions\ParserException;
use App\Models\ParseRun;
use App\Services\ReviewsUpsertService;
use App\Services\YandexParserClient;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;
use Throwable;

/**
 * Прогон парсинга одной карточки в фоне.
 *
 * Почему очередь. Сбор 600 отзывов — это десяток последовательных запросов к
 * Яндексу с паузами между ними, то есть минуты работы. Держать на это открытым
 * HTTP-запрос от браузера нельзя, поэтому контроллер только регистрирует
 * parse_run и ставит job, а интерфейс опрашивает статус прогона. Очередь заодно
 * даёт естественную точку регулирования нагрузки: сколько воркеров запущено,
 * столько карточек парсится одновременно.
 *
 * Ретраев нет осознанно ($tries = 1): по условию задачи при неудаче пользователь
 * видит причину и сам решает, пробовать ли снова. Автоматический повтор после
 * бана только усугубил бы блокировку.
 */
class ParseOrganizationJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;

    /** Запас над таймаутом HTTP-клиента, чтобы job не убили раньше ответа. */
    public int $timeout = 900;

    public function __construct(public readonly int $parseRunId)
    {
    }

    public function handle(YandexParserClient $client, ReviewsUpsertService $upsert): void
    {
        $run = ParseRun::find($this->parseRunId);
        if ($run === null) {
            return;
        }

        $run->update([
            'status' => ParseRun::STATUS_RUNNING,
            'started_at' => now(),
        ]);

        try {
            $payload = $client->parse($run->url, (int) config('parser.max_pages'));
            $organization = $upsert->store($payload);
            $meta = $payload['meta'] ?? [];

            $run->update([
                'status' => ParseRun::STATUS_SUCCESS,
                'organization_id' => $organization->id,
                'strategy_used' => $meta['strategy_used'] ?? null,
                'session_source' => $meta['session_source'] ?? null,
                'degraded' => (bool) ($meta['degraded'] ?? false),
                'fallback_reason' => $meta['fallback_reason'] ?? null,
                'pages_fetched' => $meta['pages_fetched'] ?? null,
                'reviews_fetched' => $meta['reviews_fetched'] ?? null,
                'total_reported' => $meta['total_reported'] ?? null,
                'finished_at' => now(),
            ]);
        } catch (ParserException $exception) {
            $this->failRun($run, $exception->errorCode, $exception->getMessage());
        } catch (Throwable $exception) {
            Log::error('Прогон парсинга упал', [
                'parse_run_id' => $run->id,
                'exception' => $exception,
            ]);
            $this->failRun($run, 'INTERNAL_ERROR', $exception->getMessage());
        }
    }

    /**
     * Job упал целиком (таймаут очереди, падение воркера) — отметить прогон,
     * иначе интерфейс будет вечно показывать «выполняется».
     */
    public function failed(?Throwable $exception): void
    {
        $run = ParseRun::find($this->parseRunId);
        if ($run === null || $run->isFinished()) {
            return;
        }

        $this->failRun(
            $run,
            'JOB_FAILED',
            $exception?->getMessage() ?? 'Прогон прерван до завершения',
        );
    }

    private function failRun(ParseRun $run, string $code, string $message): void
    {
        $run->update([
            'status' => ParseRun::STATUS_FAILED,
            'error_code' => $code,
            'error_message' => $message,
            'finished_at' => now(),
        ]);
    }
}
