<?php

namespace App\Service;

use Hyperf\Contract\ConfigInterface;
use Hyperf\Di\Annotation\Inject;
use Hyperf\Guzzle\ClientFactory;
use GuzzleHttp\Client;

class LipVoiceClient
{
    #[Inject]
    protected ConfigInterface $config;

    #[Inject]
    protected ClientFactory $clientFactory;

    private function client(): Client
    {
        $timeout = (float) $this->config->get('lipvoice.timeout', 20.0);
        return $this->clientFactory->create([
            'timeout' => $timeout,
            'http_errors' => false,
        ]);
    }

    private function baseUri(): string
    {
        $host = (string) $this->config->get('lipvoice.host', 'openapi.lipvoice.cn');
        return 'https://' . $host;
    }

    private function sign(): string
    {
        $sign = (string) $this->config->get('lipvoice.sign', '');
        if ($sign === '') {
            throw new \RuntimeException('服务端未配置 LIPVOICE_SIGN');
        }
        return $sign;
    }

    // 查询TTS结果
    public function ttsResult(string $taskId): array
    {
        $url = $this->baseUri() . '/api/third/tts/result?taskId=' . urlencode($taskId);

        $resp = $this->client()->get($url, [
            'headers' => [
                'sign' => $this->sign(),
            ],
        ]);

        return json_decode((string) $resp->getBody(), true) ?: [];
    }

    // 上传声纹模型
    public function uploadReference(
        string $filePath,
        string $filename,
        string $mime,
        string $name,
        string $describe = ''
    ): array {
        $url = $this->baseUri() . '/api/third/reference/upload';

        $mime = $mime ?: 'audio/wav';

        $resp = $this->client()->post($url, [
            'headers' => [
                'sign' => $this->sign(),
            ],
            'multipart' => [
                [
                    'name' => 'file',
                    'contents' => fopen($filePath, 'r'),
                    'filename' => $filename,
                    'headers' => [
                        'Content-Type' => $mime,
                    ],
                ],
                [
                    'name' => 'name',
                    'contents' => $name,
                ],
                [
                    'name' => 'describe',
                    'contents' => $describe,
                ],
            ],
        ]);

        return json_decode((string) $resp->getBody(), true) ?: [
            'code' => 7,
            'msg'  => '第三方返回非JSON',
        ];
    }

    // 创建TTS任务
    public function ttsCreate(string $audioId, string $content, array $ext = [], string $style = '2', int $genre = 0): array
    {
        $url = $this->baseUri() . '/api/third/tts/create';

        $resp = $this->client()->post($url, [
            'headers' => [
                'sign' => $this->sign(),
                'Content-Type' => 'application/json',
            ],
            'json' => [
                'content' => $content,
                'audioId' => $audioId,
                'style'   => $style,
                'ext'     => (object) $ext,
                'genre'   => $genre,
            ],
        ]);

        return json_decode((string) $resp->getBody(), true) ?: [];
    }

    // 删除第三方声纹模型（修复版）
    public function deleteReference(string $audioId): array
    {
        $url = $this->baseUri() . '/api/third/reference/delete?audioId=' . urlencode($audioId);

        $resp = $this->client()->request('DELETE', $url, [
            'headers' => [
                'sign' => $this->sign(),
            ],
        ]);

        return json_decode((string) $resp->getBody(), true) ?: [];
    }
}
