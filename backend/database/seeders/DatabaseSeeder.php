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
        User::updateOrCreate(
            ['email' => env('SEED_USER_EMAIL', 'admin@imtera.test')],
            [
                'name' => 'Imtera Admin',
                'password' => Hash::make(env('SEED_USER_PASSWORD', 'password')),
                'email_verified_at' => now(),
            ],
        );
    }
}
