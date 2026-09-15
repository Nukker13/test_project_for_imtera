<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('organizations', function (Blueprint $table) {
            $table->id();
            // Идентификатор организации в Яндексе — естественный ключ
            // идемпотентности: повторный парсинг той же карточки обновляет
            // запись, а не создаёт дубликат.
            $table->string('yandex_permalink')->unique();
            $table->text('url');
            $table->string('name')->nullable();
            $table->string('address')->nullable();
            $table->decimal('rating_avg', 2, 1)->nullable();
            // ТЗ требует показывать количество оценок и количество отзывов
            // раздельно и точными числами, поэтому это два независимых поля.
            $table->unsignedInteger('ratings_count')->nullable();
            $table->unsignedInteger('reviews_count')->nullable();
            $table->timestamp('last_parsed_at')->nullable();
            $table->jsonb('raw_meta')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('organizations');
    }
};
