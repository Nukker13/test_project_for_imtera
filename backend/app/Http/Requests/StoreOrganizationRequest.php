<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Validator;

class StoreOrganizationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'url' => ['required', 'string', 'url', 'max:2048'],
        ];
    }

    /**
     * Быстрая проверка формы ссылки до постановки в очередь.
     *
     * Окончательное решение всё равно принимает парсер — только он знает,
     * существует ли организация. Смысл этой проверки в том, чтобы очевидно
     * чужая ссылка возвращала понятную ошибку сразу, а не через минуту работы
     * воркера.
     */
    public function after(): array
    {
        return [
            function (Validator $validator) {
                $url = (string) $this->input('url');
                $host = strtolower((string) parse_url($url, PHP_URL_HOST));
                $host = preg_replace('/^www\./', '', $host);
                $path = (string) parse_url($url, PHP_URL_PATH);

                $isYandex = in_array($host, ['yandex.ru', 'yandex.com'], true)
                    || str_ends_with($host, '.yandex.ru')
                    || str_ends_with($host, '.yandex.com');

                if (! $isYandex) {
                    $validator->errors()->add('url', 'Ожидается ссылка на yandex.ru или yandex.com.');

                    return;
                }

                if (! str_contains($path, '/maps')) {
                    $validator->errors()->add('url', 'Ссылка должна вести на карточку организации в Яндекс.Картах.');
                }
            },
        ];
    }

    public function messages(): array
    {
        return [
            'url.required' => 'Укажите ссылку на карточку организации.',
            'url.url' => 'Это не похоже на корректную ссылку.',
        ];
    }
}
