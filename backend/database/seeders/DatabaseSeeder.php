<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    /**
     * Единственный пользователь системы.
     *
     * По условию задания регистрации нет: вход выполняется под заранее
     * заведённым пользователем. updateOrCreate делает сидер безопасным для
     * повторного запуска.
     */
    public function run(): void
    {
        $user = config('seed.user');

        User::updateOrCreate(
            ['email' => $user['email']],
            [
                'name' => $user['name'],
                'password' => Hash::make($user['password']),
                'email_verified_at' => now(),
            ],
        );
    }
}
