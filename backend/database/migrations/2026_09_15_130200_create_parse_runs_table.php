<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Журнал запусков парсинга.
     *
     * Полной версионной истории снимков сознательно нет: данные организации и
     * отзывов живут в одном актуальном экземпляре и обновляются через upsert, а
     * здесь остаётся след каждого прогона — когда, чем, с каким результатом.
     * Этого достаточно, чтобы отвечать на вопрос «почему данные такие» и
     * показывать пользователю ход и ошибки, но без дублирования всей выборки на
     * каждый запуск.
     */
    public function up(): void
    {
        Schema::create('parse_runs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('organization_id')->nullable()->constrained()->nullOnDelete();
            $table->text('url');
            $table->string('status')->default('pending');
            // Каким путём получены данные: прямые запросы или браузерный фолбэк.
            $table->string('strategy_used')->nullable();
            $table->string('session_source')->nullable();
            $table->boolean('degraded')->default(false);
            $table->string('fallback_reason')->nullable();
            $table->unsignedInteger('pages_fetched')->nullable();
            $table->unsignedInteger('reviews_fetched')->nullable();
            $table->unsignedInteger('total_reported')->nullable();
            $table->string('error_code')->nullable();
            $table->text('error_message')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('finished_at')->nullable();
            $table->timestamps();

            $table->index(['organization_id', 'created_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('parse_runs');
    }
};
