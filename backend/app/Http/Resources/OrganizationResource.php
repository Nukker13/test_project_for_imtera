<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class OrganizationResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'yandex_permalink' => $this->yandex_permalink,
            'url' => $this->url,
            'name' => $this->name,
            'address' => $this->address,
            'rating_avg' => $this->rating_avg,
            // Два независимых точных числа — требование ТЗ. ratings_count это
            // сколько людей поставили оценку, reviews_count — сколько написали
            // текстовый отзыв; они почти всегда различаются.
            'ratings_count' => $this->ratings_count,
            'reviews_count' => $this->reviews_count,
            // Сколько отзывов реально лежит у нас в базе. Может быть меньше
            // reviews_count: Яндекс не отдаёт больше ~600 на одну сортировку.
            'stored_reviews_count' => $this->whenCounted('reviews'),
            'last_parsed_at' => $this->last_parsed_at?->toIso8601String(),
        ];
    }
}
