<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Validation\ValidationException;

/**
 * Вход под заранее заведённым (seed) пользователем.
 *
 * Регистрации и восстановления пароля нет — по условию задания реальная
 * аутентификация не требуется. Но сам вход сделан честно: сессионная
 * SPA-аутентификация Sanctum с проверкой пароля через хэш, а не заглушка,
 * поэтому поведение интерфейса неотличимо от настоящего логина.
 */
class AuthController extends Controller
{
    public function login(Request $request): JsonResponse
    {
        $credentials = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required', 'string'],
        ], [
            'email.required' => 'Укажите email.',
            'email.email' => 'Некорректный email.',
            'password.required' => 'Укажите пароль.',
        ]);

        if (! Auth::attempt($credentials, true)) {
            throw ValidationException::withMessages([
                'email' => 'Неверный email или пароль.',
            ]);
        }

        // Смена идентификатора сессии после входа — защита от фиксации сессии.
        $request->session()->regenerate();

        return response()->json(['user' => $request->user()]);
    }

    public function logout(Request $request): JsonResponse
    {
        Auth::guard('web')->logout();
        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return response()->json(['message' => 'Вы вышли из системы.']);
    }

    public function me(Request $request): JsonResponse
    {
        return response()->json(['user' => $request->user()]);
    }
}
