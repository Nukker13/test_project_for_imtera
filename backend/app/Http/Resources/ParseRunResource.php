<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

class ParseRunResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'status' => $this->status,
            'url' => $this->url,
            'organization_id' => $this->organization_id,
            'strategy_used' => $this->strategy_used,
            'session_source' => $this->session_source,
            // Данные получены обходным путём — интерфейс показывает это отдельной
            // пометкой, чтобы результат не выглядел как обычный успешный прогон.
            'degraded' => (bool) $this->degraded,
            'fallback_reason' => $this->fallback_reason,
            'pages_fetched' => $this->pages_fetched,
            'reviews_fetched' => $this->reviews_fetched,
            'total_reported' => $this->total_reported,
            'error_code' => $this->error_code,
            'error_message' => $this->error_message,
            'started_at' => $this->started_at?->toIso8601String(),
            'finished_at' => $this->finished_at?->toIso8601String(),
        ];
    }
}
