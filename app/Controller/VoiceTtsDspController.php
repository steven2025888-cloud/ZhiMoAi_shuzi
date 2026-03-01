<?php

namespace App\Controller;

use App\Middleware\LicenseCardAuthDspMiddleware;
use App\Service\LicenseCardDspService;
use App\Service\LipVoiceClient;
use App\Service\VoiceService;
use App\Support\ApiResponse;
use Hyperf\DbConnection\Db;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Annotation\Middleware;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use GuzzleHttp\Client;

use function Hyperf\Support\env;

use Psr\Http\Message\ResponseInterface as Psr7ResponseInterface;
use Psr\Http\Message\StreamInterface;

#[Middleware(LicenseCardAuthDspMiddleware::class)]
class VoiceTtsDspController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected ResponseInterface $response;

    #[Inject]
    protected LipVoiceClient $lip;

    #[Inject]
    protected LicenseCardDspService $licenseCardDspService;

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
            'read_timeout' => 600,
            'http_errors' => false,
            'allow_redirects' => true,
        ]);

        /** @var Psr7ResponseInterface $upstreamResp */
        $upstreamResp = $client->request('GET', $voiceUrl, [
            'stream' => true,
            'headers' => [
                'sign' => env('LIPVOICE_SIGN'),
                'Accept' => '*/*',
                'Connection' => 'keep-alive',
                'Accept-Encoding' => 'identity',
                'User-Agent' => 'ZhiMoAI-Server/1.0',
            ],
        ]);

        $contentType = $upstreamResp->getHeaderLine('Content-Type') ?: 'application/octet-stream';
        $contentLength = $upstreamResp->getHeaderLine('Content-Length'); // 可能为空

        $resp = $this->response
            ->withHeader('Content-Type', $contentType)
            ->withHeader('X-Accel-Buffering', 'no')
            ->withHeader('Cache-Control', 'no-store')
            ->withHeader('Pragma', 'no-cache');

        // 只有上游带 Content-Length 才透传；否则走 chunked 更稳
        if ($contentLength !== '') {
            $resp = $resp->withHeader('Content-Length', $contentLength);
        }

        // 关键：不要 getContents()；使用 SwooleStream 包装，避免框架层缓冲导致变慢
        return $resp->withBody(new \Hyperf\HttpMessage\Stream\SwooleStream($upstreamResp->getBody()));
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
            'timeout' => 60,
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
     * 支持 GET 和 POST 方法
     */
    public function result(RequestInterface $request)
    {
        try {
            // 同时支持 GET 查询参数和 POST body 参数
            $taskId = $request->query('taskId')
                   ?: $request->query('task_id')
                   ?: $request->input('taskId')
                   ?: $request->input('task_id');

            if (!$taskId) {
                throw new \RuntimeException('缺少 taskId 参数');
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
     * 查询合成记录列表
     * GET /api/dsp/voice/tts/history?page=1&limit=20
     */
    public function history(RequestInterface $request)
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $page = max(1, (int)$request->query('page', 1));
            $limit = min(100, max(1, (int)$request->query('limit', 20)));
            $offset = ($page - 1) * $limit;

            // 查询总数
            $total = Db::table('tts_logs')
                ->where('license_key', $licenseKey)
                ->count();

            // 查询记录列表
            $records = Db::table('tts_logs')
                ->where('license_key', $licenseKey)
                ->orderBy('id', 'desc')
                ->offset($offset)
                ->limit($limit)
                ->get()
                ->toArray();

            // 格式化数据
            $list = [];
            foreach ($records as $record) {
                $voiceUrl = $record->voice_url;

                // 如果 voice_url 为空但有 task_id，尝试查询最新状态
                if (empty($voiceUrl) && !empty($record->task_id) && $record->status == 1) {
                    try {
                        $resp = $this->lip->ttsResult($record->task_id);
                        if (isset($resp['code']) && (int)$resp['code'] === 0) {
                            $data = $resp['data'] ?? [];
                            $voiceUrl = $data['voiceUrl'] ?? $data['voice_url'] ?? '';

                            // 更新数据库
                            if (!empty($voiceUrl)) {
                                Db::table('tts_logs')
                                    ->where('id', $record->id)
                                    ->update(['voice_url' => $voiceUrl]);
                            }
                        }
                    } catch (\Throwable $e) {
                        // 查询失败，使用原值
                    }
                }

                $list[] = [
                    'id'         => $record->id,
                    'model_id'   => $record->model_id,
                    'text_len'   => $record->text_len,
                    'task_id'    => $record->task_id,
                    'voice_url'  => $voiceUrl ?: '',
                    'status'     => $record->status, // 1=成功, 2=失败
                    'error_msg'  => $record->error_msg,
                    'created_at' => $record->created_at,
                ];
            }

            return ApiResponse::ok([
                'list'  => $list,
                'total' => $total,
                'page'  => $page,
                'limit' => $limit,
            ]);
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    /**
     * 查询单条合成记录详情
     * GET /api/dsp/voice/tts/history/:id
     */
    public function historyDetail(RequestInterface $request)
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $id = (int)$request->query('id', 0);

            if ($id <= 0) {
                throw new \RuntimeException('缺少记录 ID');
            }

            $record = Db::table('tts_logs')
                ->where('id', $id)
                ->where('license_key', $licenseKey)
                ->first();

            if (!$record) {
                throw new \RuntimeException('记录不存在');
            }

            return ApiResponse::ok([
                'id'         => $record->id,
                'model_id'   => $record->model_id,
                'text_len'   => $record->text_len,
                'task_id'    => $record->task_id,
                'voice_url'  => $record->voice_url,
                'status'     => $record->status,
                'error_msg'  => $record->error_msg,
                'created_at' => $record->created_at,
            ]);
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
            $this->licenseCardDspService->ensureDailyQuota($licenseKey, (int)$card->daily_char_limit, $len);

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
