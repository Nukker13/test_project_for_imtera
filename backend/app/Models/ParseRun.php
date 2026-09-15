<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ParseRun extends Model
{
    use HasFactory;

    public const STATUS_PENDING = 'pending';
    public const STATUS_RUNNING = 'running';
    public const STATUS_SUCCESS = 'success';
    public const STATUS_FAILED = 'failed';

    protected $fillable = [
        'organization_id',
        'url',
        'status',
        'strategy_used',
        'session_source',
        'degraded',
        'fallback_reason',
        'pages_fetched',
        'reviews_fetched',
        'total_reported',
        'error_code',
        'error_message',
        'started_at',
        'finished_at',
    ];

    protected function casts(): array
    {
        return [
            'degraded' => 'boolean',
            'pages_fetched' => 'integer',
            'reviews_fetched' => 'integer',
            'total_reported' => 'integer',
            'started_at' => 'datetime',
            'finished_at' => 'datetime',
        ];
    }

    public function organization(): BelongsTo
    {
        return $this->belongsTo(Organization::class);
    }

    /** Прогон завершён — фронтенду больше нет смысла опрашивать статус. */
    public function isFinished(): bool
    {
        return in_array($this->status, [self::STATUS_SUCCESS, self::STATUS_FAILED], true);
    }
}
