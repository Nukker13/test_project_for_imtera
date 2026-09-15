<?php

use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\OrganizationController;
use App\Http\Controllers\Api\ParseRunController;
use Illuminate\Support\Facades\Route;

Route::post('/login', [AuthController::class, 'login'])->name('login');

/*
 * Всё остальное — только для вошедшего пользователя. Guard `web` здесь не
 * случайность: Sanctum в режиме SPA аутентифицирует по сессионной куке, а не по
 * bearer-токену, поэтому запросы фронтенда проходят обычной сессией.
 */
Route::middleware('auth:sanctum')->group(function () {
    Route::get('/user', [AuthController::class, 'me']);
    Route::post('/logout', [AuthController::class, 'logout']);

    Route::get('/organizations', [OrganizationController::class, 'index']);
    Route::post('/organizations', [OrganizationController::class, 'store']);
    Route::get('/organizations/{organization}', [OrganizationController::class, 'show']);
    Route::get('/organizations/{organization}/reviews', [OrganizationController::class, 'reviews']);

    Route::get('/parse-runs/{parseRun}', [ParseRunController::class, 'show']);
});
