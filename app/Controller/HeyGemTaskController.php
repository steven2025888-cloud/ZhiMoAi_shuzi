<?php

declare(strict_types=1);

namespace App\Controller;

use App\Support\ApiResponse;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\Redis\Redis;
use Hyperf\WebSocketServer\Sender;

/**
 * HeyGem 视频合成任务控制器
 *
 * 功能：
 * 1. 接收 PC 端的视频合成任务
 * 2. GPU 在线时直接转发
 * 3. GPU 离线时入队，开机后自动执行
 */
class HeyGemTaskController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected Redis $redis;

    #[Inject]
    protected Sender $sender;

    /**
     * POST /api/heygem/task/submit
     *
     * 提交 HeyGem 视频合成任务
     *
     * body: {
     *   "audio_hash": "md5hex",
     *   "audio_ext": ".wav",
     *   "video_hash": "md5hex",
     *   "video_ext": ".mp4",
     *   "license_key": "xxx"
     * }
     *
     * 返回：
     * - GPU 在线：{ "code": 0, "data": { "task_id": "...", "status": "submitted" } }
     * - GPU 离线：{ "code": 0, "data": { "task_id": "...", "status": "queued", "msg": "..." } }
     */
    public function submit(): array
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $audioHash  = (string)$this->request->input('audio_hash', '');
            $audioExt   = (string)$this->request->input('audio_ext', '.wav');
            $videoHash  = (string)$this->request->input('video_hash', '');
            $videoExt   = (string)$this->request->input('video_ext', '.mp4');

            if (!$audioHash || !$videoHash) {
                return ApiResponse::fail('缺少 audio_hash 或 video_hash');
            }

            // 生成任务 ID
            $taskId = uniqid('heygem_');
            $requestId = $taskId;
            $payload = [
                'audio_hash' => $audioHash,
                'audio_ext'  => $audioExt,
                'video_hash' => $videoHash,
                'video_ext'  => $videoExt,
                'task_id'    => $taskId,
            ];

            // 检查 GPU 是否在线
            $workers = $this->redis->sMembers('dsp:workers');
            $gpuOnline = !empty($workers);

            if ($gpuOnline) {
                $sent = $this->_dispatchToWorkers($licenseKey, $requestId, $payload);
                if ($sent > 0) {
                    $this->_saveTaskStatus($taskId, $requestId, 'processing');
                    return ApiResponse::ok([
                        'task_id' => $taskId,
                        'status'  => 'submitted',
                        'msg'     => '任务已提交到 GPU 服务器',
                    ], '已提交');
                }
            }

            // GPU 离线或发送失败：入队并通知 GPU Manager 开机
            $this->_enqueueTask($licenseKey, $requestId, $payload);

            return ApiResponse::ok([
                'task_id' => $taskId,
                'status'  => 'queued',
                'msg'     => 'GPU 服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）',
            ], '已排队');

        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    /**
     * GET /api/heygem/task/status?task_id=xxx
     *
     * 查询任务状态
     */
    public function status(): array
    {
        try {
            $taskId = (string)$this->request->input('task_id', '');

            if (!$taskId) {
                return ApiResponse::fail('缺少 task_id');
            }

            // 从 Redis 查询任务状态
            $statusKey = "heygem:task:status:{$taskId}";
            $status = $this->redis->get($statusKey);

            if (!$status) {
                return ApiResponse::fail('任务不存在或已过期');
            }

            $data = json_decode($status, true);

            return ApiResponse::ok($data);

        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    // ─────────────────────── 私有方法 ────────────────────────────────

    private function _dispatchToWorkers(string $licenseKey, string $requestId, array $payload): int
    {
        $msg = json_encode([
            'type'       => 'gpu.job.submit',
            'task_type'  => 'heygem_submit',
            'request_id' => $requestId,
            'key'        => $licenseKey,
            'sender_fd'  => 0,
            'payload'    => $payload,
        ], JSON_UNESCAPED_UNICODE);

        $workers = $this->redis->sMembers('dsp:workers');
        $sent = 0;

        foreach ($workers as $fdStr) {
            $fd = (int)$fdStr;
            if ($fd <= 0) {
                continue;
            }
            try {
                $this->sender->push($fd, $msg);
                $sent++;
            } catch (\Throwable $e) {
                // 清理失效 fd，避免后续误判“在线”
                $this->redis->sRem('dsp:workers', (string)$fdStr);
            }
        }

        return $sent;
    }

    /**
     * 将任务入队到 Redis
     */
    private function _enqueueTask(string $licenseKey, string $requestId, array $payload): void
    {
        $msg = json_encode([
            'type'       => 'gpu.job.submit',
            'task_type'  => 'heygem_submit',
            'request_id' => $requestId,
            'key'        => $licenseKey,
            'sender_fd'  => 0,
            'payload'    => $payload,
        ], JSON_UNESCAPED_UNICODE);

        $queueKey = 'dsp:pending_tasks:' . $licenseKey;
        $len = (int)$this->redis->lLen($queueKey);
        if ($len >= 100) {
            $this->redis->lPop($queueKey);
        }
        $this->redis->rPush($queueKey, $msg);

        $this->_saveTaskStatus((string)$payload['task_id'], $requestId, 'queued');

        // 通知 GPU Monitor 有新任务（触发自动开机）
        $this->_notifyGpuMonitors([
            'type' => 'gpu.job.submit',
            'task_type' => 'heygem_submit',
            'key' => $licenseKey,
            'request_id' => $requestId,
        ]);

        echo "[HeyGemTask] 任务入队: key={$licenseKey} task_id={$payload['task_id']} request_id={$requestId}\n";
    }

    /**
     * 通知 GPU 监控器有新任务
     */
    private function _notifyGpuMonitors(array $data): void
    {
        $msg = json_encode($data, JSON_UNESCAPED_UNICODE);

        // 将通知消息存入 Redis，由 WebSocket 服务器发送
        // 因为 HTTP Controller 无法直接访问 WebSocket Server
        $notifyKey = 'dsp:gpu_monitor_notify';
        $this->redis->rPush($notifyKey, $msg);

        $monitorCount = (int)$this->redis->sCard('dsp:gpu_monitors');
        $queueLen = $this->redis->lLen($notifyKey);
        echo "[HeyGemTask] 已写入 GPU Monitor 通知队列: monitors={$monitorCount}, queue_len={$queueLen}\n";
        echo "[HeyGemTask] 通知内容: {$msg}\n";
    }

    private function _saveTaskStatus(string $taskId, string $requestId, string $status): void
    {
        $statusKey = "heygem:task:status:{$taskId}";
        $this->redis->setex($statusKey, 86400, json_encode([
            'task_id'    => $taskId,
            'status'     => $status,
            'request_id' => $requestId,
            'created_at' => time(),
        ]));
    }
}
