<?php

namespace App\Controller;

use App\Middleware\LicenseCardAuthMiddleware;
use App\Service\LicenseCardService;
use App\Service\LipVoiceClient;
use App\Service\VoiceService;
use App\Support\ApiResponse;
use Hyperf\DbConnection\Db;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Annotation\Middleware;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;



use Psr\Http\Message\ResponseInterface as Psr7ResponseInterface;

use function Hyperf\Support\env;

use Psr\Http\Message\StreamInterface;


#[Middleware(LicenseCardAuthMiddleware::class)]
class VoiceTtsController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected ResponseInterface $response;

    #[Inject]
    protected LipVoiceClient $lip;

    #[Inject]
    protected LicenseCardService $licenseCardService;

    #[Inject]
    protected VoiceService $voice;


public function download(RequestInterface $request)
{
    try {
        $voiceUrl = (string) $request->query('voice_url', '');
        if ($voiceUrl === '') {
            return $this->response->json(['code' => 400, 'msg' => '缺少 voice_url']);
        }

        $client = new \GuzzleHttp\Client([
            'verify' => false,
            'timeout' => 600,
            'connect_timeout' => 20,
            'http_errors' => true,
        ]);

        /** @var Psr7ResponseInterface $upstreamResp */
        $upstreamResp = $client->request('GET', $voiceUrl, [
            'stream' => true,
            'headers' => [
                'sign' => env('LIPVOICE_SIGN'),
                'Accept' => '*/*',
                'Connection' => 'keep-alive',
                'Accept-Encoding' => 'identity',
            ],
        ]);

        $contentType = $upstreamResp->getHeaderLine('Content-Type') ?: 'application/octet-stream';
        $contentLength = $upstreamResp->getHeaderLine('Content-Length'); // 可能为空

        // 让浏览器/客户端“下载保存”，而不是尝试当做页面打开
        $filename = 'tts_' . date('Ymd_His') . '.wav';
        $disposition = 'attachment; filename="' . $filename . '"';

        $resp = $this->response
            ->withHeader('Content-Type', $contentType)
            ->withHeader('Content-Disposition', $disposition)
            ->withHeader('Cache-Control', 'no-store')
            ->withHeader('Pragma', 'no-cache');

        // 只有上游带 Content-Length 才透传；否则走 chunked 更稳
        if ($contentLength !== '') {
            $resp = $resp->withHeader('Content-Length', $contentLength);
        }

        // 关键：不要 getContents()，直接把上游 stream 当 body 返回（边读边发）
        return $resp->withBody($upstreamResp->getBody());
    } catch (\Throwable $e) {
        return $this->response->json([
            'code' => 500,
            'msg' => $e->getMessage(),
        ]);
    }
}


    /**
     * 播放代理接口（不走卡密中间件）
     * ffplay 直接访问这个接口
     */
    public function play(RequestInterface $request)
{
    try {
        $voiceUrl = $request->query('voice_url');
        if (!$voiceUrl) {
            return $this->response->json(['code'=>400,'msg'=>'缺少 voice_url']);
        }

        $client = new \GuzzleHttp\Client([
            'verify' => false,
            'timeout' => 600,
        ]);

        $resp = $client->get($voiceUrl, [
            'headers' => [
                'sign' => env('LIPVOICE_SIGN'),
            ],
        ]);

        $contentType = $resp->getHeaderLine('Content-Type') ?: 'application/octet-stream';
        $body = $resp->getBody()->getContents();

        return $this->response
            ->withHeader('Content-Type', $contentType)
            ->withHeader('Content-Length', strlen($body))
            ->withBody(new \Hyperf\HttpMessage\Stream\SwooleStream($body));

    } catch (\Throwable $e) {
        return $this->response->json([
            'code' => 500,
            'msg' => $e->getMessage()
        ]);
    }
}


    /**
     * 查询合成结果
     */
    public function result(RequestInterface $request)
    {
        try {
            $taskId = $request->input('taskId');
            if (!$taskId) {
                throw new \RuntimeException('缺少 taskId');
            }

            $resp = $this->lip->ttsResult($taskId);
            if (!isset($resp['code']) || (int)$resp['code'] !== 0) {
                throw new \RuntimeException($resp['msg'] ?? '第三方查询失败');
            }

            return ApiResponse::ok($resp['data']);
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    /**
     * 创建 TTS 任务
     */
    public function create()
    {
        $licenseKey = (string) $this->request->getAttribute('license_key');
        $card = $this->request->getAttribute('license_card');

        if (!$card) {
            return ApiResponse::fail('未获取到卡密信息，请检查中间件是否生效');
        }

        $text = (string) $this->request->input('text', '');
        $modelId = (int) $this->request->input('model_id', 0);

        try {
            if ($text === '') throw new \RuntimeException('text 不能为空');
            if ($modelId <= 0) throw new \RuntimeException('model_id 不合法');

            $len = mb_strlen($text, 'UTF-8');
            $this->licenseCardService->ensureDailyQuota($licenseKey, (int)$card->daily_char_limit, $len);

            $model = $this->voice->mustOwnModel($licenseKey, $modelId);

            $resp = $this->lip->ttsCreate($model->audio_id, $text);
            if (!isset($resp['code']) || (int)$resp['code'] !== 0) {
                throw new \RuntimeException($resp['msg'] ?? '第三方合成失败');
            }

            $data = $resp['data'] ?? [];
            $taskId = $data['taskId'] ?? $data['task_id'] ?? null;
            $voiceUrl = $data['voiceUrl'] ?? $data['voice_url'] ?? null;

            Db::table('tts_logs')->insert([
                'license_key' => $licenseKey,
                'model_id'    => $modelId,
                'text_len'    => $len,
                'task_id'     => $taskId,
                'voice_url'   => $voiceUrl,
                'status'      => 1,
                'error_msg'   => null,
                'created_at'  => date('Y-m-d H:i:s'),
            ]);

            return ApiResponse::ok([
                'taskId'   => $taskId,
                'voiceUrl' => $voiceUrl,
            ]);
        } catch (\Throwable $e) {
            Db::table('tts_logs')->insert([
                'license_key' => $licenseKey,
                'model_id'    => max(0, $modelId),
                'text_len'    => max(0, mb_strlen($text, 'UTF-8')),
                'task_id'     => null,
                'voice_url'   => null,
                'status'      => 2,
                'error_msg'   => $e->getMessage(),
                'created_at'  => date('Y-m-d H:i:s'),
            ]);

            return ApiResponse::fail($e->getMessage());
        }
    }
}
