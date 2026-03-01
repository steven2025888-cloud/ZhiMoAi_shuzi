<?php
declare(strict_types=1);

namespace App\Controller;

use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\GetMapping;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use function Hyperf\Support\env;
#[Controller(prefix: "api")]
class RecordingController
{
    #[GetMapping(path: "recording_download")]
    public function download(RequestInterface $request, ResponseInterface $response)
    {
        $file = trim((string)$request->query('file', ''));
        $ts = (int)$request->query('ts', 0);
        $token = trim((string)$request->query('token', ''));

        if (!$file || !$ts || !$token) return $response->withStatus(403)->raw('Forbidden');

        $ttl = (int)env('recording.ttl', 120);
        if (abs(time() - $ts) > $ttl) return $response->withStatus(403)->raw('Expired');

        if (!$this->verify($file, $ts, $token)) return $response->withStatus(403)->raw('Forbidden');

        // ✅ 防目录穿越
        if (str_contains($file, '..') || str_contains($file, '/')) return $response->withStatus(403)->raw('Forbidden');

        $path = BASE_PATH . '/storage/recordings/' . $file;
        if (!is_file($path)) return $response->withStatus(404)->raw('Not Found');

        // 直接输出文件
        return $response->download($path, $file);
    }

    private function verify(string $file, int $ts, string $token): bool
    {
        $secret = env('recording.secret', 'change-me');
        $payload = $file . '|' . $ts;
        $expect = hash_hmac('sha256', $payload, $secret);
        return hash_equals($expect, $token);
    }
}
