<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\ParseRunResource;
use App\Models\ParseRun;

class ParseRunController extends Controller
{
    /**
     * Статус прогона — это же и есть источник прогресса для интерфейса.
     *
     * Фронтенд опрашивает эндпоинт, пока статус не станет терминальным, и
     * показывает по нему либо индикатор загрузки, либо текст ошибки.
     */
    public function show(ParseRun $parseRun): ParseRunResource
    {
        return new ParseRunResource($parseRun);
    }
}
