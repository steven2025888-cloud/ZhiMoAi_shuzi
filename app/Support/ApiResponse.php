<?php

namespace App\Support;

class ApiResponse
{
    public static function ok(mixed $data = null, string $msg = 'ok'): array
    {
        return ['code' => 0, 'msg' => $msg, 'data' => $data];
    }

    public static function fail(string $msg, int $code = 7, mixed $data = null): array
    {
        return ['code' => $code, 'msg' => $msg, 'data' => $data];
    }
}
