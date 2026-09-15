<?php

namespace App\Services;

use App\Models\Organization;
use App\Models\Review;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

/**
 * Раскладывает результат парсинга по таблицам идемпотентно.
 *
 * Модель снимков здесь намеренно простая: одна актуальная версия данных плюс
 * журнал запусков в parse_runs. Повторный парсинг той же карточки обновляет
 * существующие строки, а не плодит копии — за это отвечают уникальные ключи
 * organizations.yandex_permalink и (organization_id, yandex_review_id).
 */
class ReviewsUpsertService
{
    /** Отзывы пишутся пачками: 600 строк одним запросом — лишний риск по памяти. */
    private const CHUNK = 200;

    /**
     * @param  array{organization: array, reviews: array, meta: array}  $payload
     */
    public function store(array $payload): Organization
    {
        return DB::transaction(function () use ($payload) {
            $organization = $this->upsertOrganization($payload['organization']);
            $this->upsertReviews($organization, $payload['reviews'] ?? []);

            return $organization;
        });
    }

    private function upsertOrganization(array $data): Organization
    {
        return Organization::updateOrCreate(
            ['yandex_permalink' => (string) $data['yandex_permalink']],
            [
                'url' => $data['url'],
                'name' => $data['name'] ?? null,
                'address' => $data['address'] ?? null,
                'rating_avg' => $data['rating_avg'] ?? null,
                'ratings_count' => $data['ratings_count'] ?? null,
                'reviews_count' => $data['reviews_count'] ?? null,
                'last_parsed_at' => now(),
            ],
        );
    }

    private function upsertReviews(Organization $organization, array $reviews): void
    {
        if ($reviews === []) {
            return;
        }

        $now = now();

        foreach (array_chunk($reviews, self::CHUNK) as $chunk) {
            $rows = array_map(static fn (array $review): array => [
                'organization_id' => $organization->id,
                'yandex_review_id' => (string) $review['yandex_review_id'],
                'author_name' => $review['author_name'],
                'rating' => (int) $review['rating'],
                'text' => $review['text'] ?? '',
                'reviewed_at' => Carbon::parse($review['reviewed_at']),
                'created_at' => $now,
                'updated_at' => $now,
            ], $chunk);

            // Конфликт по (organization_id, yandex_review_id) — это тот же отзыв,
            // который мог быть отредактирован автором: обновляем содержимое.
            Review::upsert(
                $rows,
                ['organization_id', 'yandex_review_id'],
                ['author_name', 'rating', 'text', 'reviewed_at', 'updated_at'],
            );
        }
    }
}
