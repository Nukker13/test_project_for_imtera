<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\StoreOrganizationRequest;
use App\Http\Resources\OrganizationResource;
use App\Http\Resources\ParseRunResource;
use App\Http\Resources\ReviewResource;
use App\Jobs\ParseOrganizationJob;
use App\Models\Organization;
use App\Models\ParseRun;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class OrganizationController extends Controller
{
    /** Сколько отзывов на страницу — зафиксировано в ТЗ. */
    private const PER_PAGE = 50;

    /**
     * Принять ссылку и запустить парсинг в фоне.
     *
     * Контроллер сознательно не делает ничего тяжёлого: регистрирует прогон,
     * ставит job и сразу отвечает. Всё общение с Яндексом происходит в воркере
     * через Python-сервис.
     */
    public function store(StoreOrganizationRequest $request): JsonResponse
    {
        $run = ParseRun::create([
            'url' => $request->validated('url'),
            'status' => ParseRun::STATUS_PENDING,
        ]);

        ParseOrganizationJob::dispatch($run->id);

        return response()->json([
            'parse_run' => new ParseRunResource($run),
        ], 202);
    }

    /** Список разобранных организаций — свежие сверху. */
    public function index(): AnonymousResourceCollection
    {
        $organizations = Organization::query()
            ->withCount('reviews')
            ->orderByDesc('last_parsed_at')
            ->get();

        return OrganizationResource::collection($organizations);
    }

    public function show(Organization $organization): OrganizationResource
    {
        return new OrganizationResource($organization->loadCount('reviews'));
    }

    /** Отзывы организации постранично, по 50 штук. */
    public function reviews(Request $request, Organization $organization): AnonymousResourceCollection
    {
        $reviews = $organization->reviews()
            ->orderByDesc('reviewed_at')
            ->orderByDesc('id')
            ->paginate(self::PER_PAGE)
            ->withQueryString();

        return ReviewResource::collection($reviews);
    }
}
