<?php

declare(strict_types=1);

namespace App\Service;

use GuzzleHttp\Client;
use Hyperf\Guzzle\ClientFactory;
use function Hyperf\Support\env;

class Check51Client
{
    private Client $client;

    private string $baseUri;
    private string $token;
    private string $signCode;
    private float $timeout;

    public function __construct(ClientFactory $clientFactory)
    {
        $this->baseUri = rtrim((string) env('CHECK51_BASE_URI', 'https://www.check51.com'), '/');
        $this->token = (string) env('CHECK51_TOKEN', '');
        $this->signCode = (string) env('CHECK51_SIGN_CODE', '');
        $this->timeout = (float) env('CHECK51_TIMEOUT', 20);

        $this->client = $clientFactory->create([
            'base_uri' => $this->baseUri,
            'timeout' => $this->timeout,
            'http_errors' => false,
        ]);
    }

   public function extractResContent(string $content, int $queryType = 0, ?string $guid = null): array
{
    $guid = $guid ?: $this->makeGuid();

    $headers = [
        'Accept' => 'application/json, text/plain, */*',
        'Content-Type' => 'application/json;charset=UTF-8',

        // 尽量模拟你原来的 cURL 请求头（避免风控/返回HTML）
        'Pragma' => 'no-cache',
        'Cache-Control' => 'no-cache',
        'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
        'sec-ch-ua' => '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile' => '?0',
        'sec-ch-ua-platform' => '"Windows"',
        'Sec-Fetch-Site' => 'same-origin',
        'Sec-Fetch-Mode' => 'cors',
        'Sec-Fetch-Dest' => 'empty',

        // 注意：host 这种通常不要手动设置，交给 HTTP 客户端
        // 'host' => 'www.check51.com',
    ];

    if ($this->token !== '') {
        $headers['Authorization'] = str_starts_with($this->token, 'Bearer ')
            ? $this->token
            : ('Bearer ' . $this->token);
    }
    if ($this->signCode !== '') {
        $headers['signCode'] = $this->signCode;
    }

    $resp = $this->client->post('/api/video-recognition/batch-video-link-extract', [
        'headers' => $headers,
        'json' => [
            'content' => $content,
            'queryType' => $queryType,
            'guid' => $guid,
        ],
        // 关键：让 Guzzle 自动处理 gzip/deflate（默认一般就行，但这里显式开）
        'decode_content' => true,
    ]);

    $status = $resp->getStatusCode();
    $ctype = $resp->getHeaderLine('Content-Type');
    $body = (string) $resp->getBody();

    // 先做“像不像JSON”的快速判断
    $trim = ltrim($body);
    $looksJson = $trim !== '' && ($trim[0] === '{' || $trim[0] === '[');

    $json = null;
    if ($looksJson) {
        $json = json_decode($body, true);
    }

    if (!is_array($json)) {
        // 返回诊断信息：你一看就知道是 403 HTML 还是其它
        return [
            'ok' => false,
            'guid' => $guid,
            'status' => $status,
            'contentType' => $ctype,
            'msg' => '非JSON返回',
            'body_snippet' => mb_substr($body, 0, 400), // 关键：把前几百字符带回来看
        ];
    }

    $resContent = $json['ResList'][0]['ExtractResult']['ResContent'] ?? null;

    return [
        'ok' => is_string($resContent) && $resContent !== '',
        'guid' => $guid,
        'status' => $status,
        'contentType' => $ctype,
        'msg' => (string)($json['Msg'] ?? ''),
        'code' => (string)($json['Code'] ?? ''),
        'resContent' => is_string($resContent) ? $resContent : null,
        // 'raw' => $json, // 需要调试再开
    ];
}

    private function makeGuid(): string
    {
        $data = random_bytes(16);
        $data[6] = chr((ord($data[6]) & 0x0f) | 0x40);
        $data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
        $hex = bin2hex($data);

        return sprintf('%s-%s-%s-%s-%s',
            substr($hex, 0, 8),
            substr($hex, 8, 4),
            substr($hex, 12, 4),
            substr($hex, 16, 4),
            substr($hex, 20, 12)
        );
    }
}