<?php

declare(strict_types=1);

namespace App\Controller;

use App\Service\Check51Client;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;

class VideoExtractController
{
    public function __construct(
        private readonly Check51Client $client,
        private readonly ResponseInterface $response
    ) {}

    // POST /api/video/extract-rescontent
    public function extract(RequestInterface $request)
    {
        $content = (string) $request->input('content', '');
        $queryType = (int) $request->input('queryType', 0);

        if (trim($content) === '') {
            return $this->response->json(['code' => 400, 'msg' => 'content 不能为空'])->withStatus(400);
        }

        $ret = $this->client->extractResContent($content, $queryType);
        
        // 你要的：只返回 ResContent 信息（拿不到就返回 msg）
       if ($ret['ok'] ?? false) {
            return $this->response->json([
                'code' => 0,
                'msg' => 'ok',
                'guid' => $ret['guid'] ?? null,
                'resContent' => $ret['resContent'],
            ]);
        }

       return $this->response->json([
            'code' => 1,
            'msg' => $ret['msg'] ?? 'failed',
            'guid' => $ret['guid'] ?? null,
            'status' => $ret['status'] ?? null,
            'contentType' => $ret['contentType'] ?? null,
            'body_snippet' => $ret['body_snippet'] ?? null,
        ]);
    }
}