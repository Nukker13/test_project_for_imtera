<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Organization extends Model
{
    use HasFactory;

    protected $fillable = [
        'yandex_permalink',
        'url',
        'name',
        'address',
        'rating_avg',
        'ratings_count',
        'reviews_count',
        'last_parsed_at',
        'raw_meta',
    ];

    protected function casts(): array
    {
        return [
            'rating_avg' => 'float',
            'ratings_count' => 'integer',
            'reviews_count' => 'integer',
            'last_parsed_at' => 'datetime',
            'raw_meta' => 'array',
        ];
    }

    public function reviews(): HasMany
    {
        return $this->hasMany(Review::class);
    }

    public function parseRuns(): HasMany
    {
        return $this->hasMany(ParseRun::class);
    }
}
