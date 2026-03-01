<?php

declare(strict_types=1);

namespace App\Controller;

use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\GetMapping;
use Hyperf\Context\Context;
use Swoole\Http\Response as SwooleResponse;
use Psr\Http\Message\ServerRequestInterface;

use function Hyperf\Support\env;

#[Controller(prefix: 'stream')]
class StreamController
{
    #[GetMapping(path: 'chat')]
    public function chat()
    {
        /** @var SwooleResponse $response */
        $response = Context::get(SwooleResponse::class);

        if (!$response) {
            // ⚠️ 理论上不会发生
            return '';
        }

        // ✅ SSE 必须的 Header（顺序无所谓）
        $response->header('Content-Type', 'text/event-stream; charset=utf-8');
        $response->header('Cache-Control', 'no-cache');
        $response->header('Connection', 'keep-alive');
        $response->header('X-Accel-Buffering', 'no'); // nginx 必须

        /** @var ServerRequestInterface $request */
        $request = Context::get(ServerRequestInterface::class);

        $prompt = $request->query('q', '你好');

        $payload = [
            'model' => 'gpt-5-mini',
            'messages' => [
                ['role' => 'user', 'content' => $prompt],
            ],
            'temperature' => 0.7,
            'stream' => true,
        ];

        $ch = curl_init(env('API_url') . '/v1/chat/completions');

        curl_setopt_array($ch, [
            CURLOPT_HTTPHEADER => [
                'Authorization: Bearer ' . env('OPENAI_API_KEY'),
                'Content-Type: application/json',
            ],
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE),
            CURLOPT_RETURNTRANSFER => false,
            CURLOPT_TIMEOUT => 0,

            // ⭐⭐⭐ 核心：OpenAI → SSE 转发
            CURLOPT_WRITEFUNCTION => function ($ch, $chunk) use ($response) {

                foreach (explode("\n", $chunk) as $line) {
                    if (!str_starts_with($line, 'data: ')) {
                        continue;
                    }

                    $data = trim(substr($line, 6));

                    if ($data === '[DONE]') {
                        $response->write("event: end\n");
                        $response->write("data: done\n\n");
                        return strlen($chunk);
                    }

                    $json = json_decode($data, true);
                    if (!$json) {
                        continue;
                    }

                    $delta = $json['choices'][0]['delta']['content'] ?? '';

                    if ($delta !== '') {
                        // 🔥 SSE 标准格式
                        $response->write("data: {$delta}\n\n");
                    }
                }

                return strlen($chunk);
            },
        ]);

        curl_exec($ch);
        curl_close($ch);

        // ❗不要 return
        $response->end();
        return '';
    }
}
