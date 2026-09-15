<?php

namespace App\Providers;

use App\Services\YandexParserClient;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        // У клиента парсера скалярные параметры конструктора, которые контейнер
        // сам разрешить не может, — собираем его из конфига явно.
        $this->app->singleton(
            YandexParserClient::class,
            static fn (): YandexParserClient => YandexParserClient::fromConfig(),
        );
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        //
    }
}
