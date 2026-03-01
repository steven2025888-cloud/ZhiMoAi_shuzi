<?php

declare(strict_types=1);

namespace App\Controller;

use Hyperf\Contract\OnOpenInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnCloseInterface;
use function Hyperf\Support\env;


/**
 * @WebSocketController(server="ws")
 */
 
class WebSocketController implements OnOpenInterface, OnMessageInterface, OnCloseInterface
{
    public function onOpen($server, $request): void
    {
        // 连接成功提示
        $server->push($request->fd, json_encode([
            'event' => 'open',
            'message' => 'ws connected1'
        ], JSON_UNESCAPED_UNICODE));
    }

    public function onMessage($server, $frame): void
{
    $data = json_decode($frame->data, true);
    if (!is_array($data)) {
        return;
    }

    $payload = [
        'model' => $data['model'] ?? 'gpt-5-mini',
        'messages' => $data['messages'] ?? [],
        'temperature' => $data['temperature'] ?? 1.0,
        'stream' => true,
        
        "group"=> "default",

          "temperature"=> 0.7,
          "top_p"=> 1,
          "frequency_penalty"=> 0,
          "presence_penalty"=> 0
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
        CURLOPT_CONNECTTIMEOUT => 10,

        // ⭐ 关键：拿到 header 以便判断 HTTP 状态
        CURLOPT_HEADER => false,

        CURLOPT_WRITEFUNCTION => function ($ch, $chunk) use ($server, $frame) {

            foreach (explode("\n", $chunk) as $line) {
                if (!str_starts_with($line, 'data: ')) {
                    continue;
                }

                $content = trim(substr($line, 6));

                // 流结束
                if ($content === '[DONE]') {
                    $server->push($frame->fd, json_encode([
                        'event' => 'end'
                    ], JSON_UNESCAPED_UNICODE));
                    continue;
                }

                $json = json_decode($content, true);
                if (!$json) {
                    continue;
                }

                // ⭐ 处理第三方 error
                if (isset($json['error'])) {
                    $server->push($frame->fd, json_encode([
                        'event' => 'error',
                        'message' => $json['error']['message'] ?? 'AI error'
                    ], JSON_UNESCAPED_UNICODE));
                    continue;
                }

                // 正常流式 token
                $delta = $json['choices'][0]['delta']['content'] ?? '';
                if ($delta !== '') {
                    $server->push($frame->fd, json_encode([
                        'content' => $delta
                    ], JSON_UNESCAPED_UNICODE));
                }
            }

            return strlen($chunk);
        }
    ]);

    // ⭐ 执行
    $result = curl_exec($ch);

    // ⭐ curl 层错误（最重要）
    if ($result === false) {
        $server->push($frame->fd, json_encode([
            'event' => 'error',
            'message' => curl_error($ch),
        ], JSON_UNESCAPED_UNICODE));
    }

    // ⭐ HTTP 状态码错误
    $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    if ($httpCode >= 400) {
        $server->push($frame->fd, json_encode([
            'event' => 'error',
            'message' => 'HTTP Error: ' . $httpCode,
        ], JSON_UNESCAPED_UNICODE));
    }

    curl_close($ch);
}


    public function onClose($server, $fd, $reactorId): void
    {
        // 可记录日志
    }
}
