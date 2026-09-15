<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('reviews', function (Blueprint $table) {
            $table->id();
            $table->foreignId('organization_id')->constrained()->cascadeOnDelete();
            $table->string('yandex_review_id');
            $table->string('author_name');
            $table->unsignedTinyInteger('rating');
            $table->text('text')->nullable();
            $table->timestamp('reviewed_at');
            $table->timestamps();

            // Пара (организация, отзыв) уникальна — это и есть идемпотентность
            // на уровне БД: повторный прогон делает upsert, а не вставку копий.
            $table->unique(['organization_id', 'yandex_review_id']);
            // Основной запрос страницы: отзывы одной организации, свежие сверху.
            $table->index(['organization_id', 'reviewed_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reviews');
    }
};
