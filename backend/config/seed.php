<?php

return [
    /*
     * Реквизиты пользователя, под которым выполняется вход (регистрации в
     * проекте нет). Вынесены в конфиг, а не читаются через env() прямо в
     * сидере: на проде выполняется `config:cache`, после которого env() всегда
     * возвращает null, и сид молча завёл бы пользователя с пустой почтой.
     */
    'user' => [
        'name' => env('SEED_USER_NAME', 'Imtera Admin'),
        'email' => env('SEED_USER_EMAIL', 'admin@imtera.test'),
        'password' => env('SEED_USER_PASSWORD', 'password'),
    ],
];
