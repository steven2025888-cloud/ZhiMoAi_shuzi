<?php

declare(strict_types=1);

namespace App\Controller;

use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\PostMapping;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Hyperf\Redis\Redis;
use Hyperf\WebSocketServer\Sender;

/**
 * HeyGem 任务代理控制器
 *
 * 接收 PC 端的 HTTP 请求，转发到 WebSocket (GPU Worker)
 */
#[Controller(prefix: '/api/heygem')]
class HeyGemProxyController
{
    public function __construct(
        private Redis $redis,
        private Sender $sender
    ) {}

    /**
     * 健康检查代理
     *
     * PC 端调用此接口检查 GPU 状态
     * 如果 GPU 离线，返回离线状态，触发 GPU Manager 开机
     */
    #[PostMapping(path: 'health/proxy')]
    public function healthProxy(RequestInterface $request, ResponseInterface $response)
    {
        $licenseKey = $request->input('license_key', '');

        // 检查是否有在线的 Worker
        $workers = $this->redis->sMembers('dsp:workers');
        $hasWorker = count($workers) > 0;

        if (!$hasWorker) {
            // GPU 离线，通知 GPU Monitor
            $this->notifyGpuMonitors([
                'type' => 'gpu.job.submit',
                'task_type' => 'heygem_health_check',
                'key' => $licenseKey,
            ]);

            return $response->json([
                'code' => -1,
                'msg' => 'GPU 服务器离线，正在启动...',
                'initialized' => false,
                'gpu_status' => 'offline',
            ]);
        }

        // GPU 在线，返回正常状态
        return $response->json([
            'code' => 0,
            'msg' => 'GPU 服务器在线',
            'initialized' => true,
            'gpu_status' => 'online',
        ]);
    }

    /**
     * 任务提交代理
     *
     * PC 端调用此接口提交任务
     */
    #[PostMapping(path: 'task/proxy')]
    public function taskProxy(RequestInterface $request, ResponseInterface $response)
    {
        $licenseKey = $request->input('license_key', '');
        $audioHash = $request->input('audio_hash', '');
        $videoHash = $request->input('video_hash', '');
        $audioExt = $request->input('audio_ext', '.wav');
        $videoExt = $request->input('video_ext', '.mp4');

        if (!$licenseKey || !$audioHash || !$videoHash) {
            return $response->json([
                'code' => -1,
                'msg' => '参数错误',
            ]);
        }

        // 生成任务 ID
        $taskId = uniqid('heygem_');
        $requestId = uniqid('req_');

        // 通过 WebSocket 提交任务
        $taskData = [
            'type' => 'gpu.job.submit',
            'task_type' => 'heygem_submit',
            'request_id' => $requestId,
            'key' => $licenseKey,
            'payload' => [
                'task_id' => $taskId,
                'audio_hash' => $audioHash,
                'audio_ext' => $audioExt,
                'video_hash' => $videoHash,
                'video_ext' => $videoExt,
            ],
        ];

        // 检查是否有在线的 Worker
        $workers = $this->redis->sMembers('dsp:workers');

        if (count($workers) === 0) {
            // GPU 离线，通知 GPU Monitor 并入队
            $this->notifyGpuMonitors($taskData);

            // 任务入队
            $queueKey = 'dsp:pending_tasks:' . $licenseKey;
            $this->redis->rPush($queueKey, json_encode($taskData, JSON_UNESCAPED_UNICODE));

            return $response->json([
                'code' => 0,
                'msg' => 'GPU 服务器离线，任务已排队',
                'task_id' => $taskId,
                'request_id' => $requestId,
                'status' => 'queued',
            ]);
        }

        // GPU 在线，直接转发
        $sent = $this->dispatchToWorker($taskData);

        if ($sent > 0) {
            // 通知 GPU Monitor
            $this->notifyGpuMonitors($taskData);

            return $response->json([
                'code' => 0,
                'msg' => '任务已提交',
                'task_id' => $taskId,
                'request_id' => $requestId,
                'status' => 'processing',
            ]);
        }

        return $response->json([
            'code' => -1,
            'msg' => '任务提交失败',
        ]);
    }

    /**
     * 转发任务到 Worker
     */
    private function dispatchToWorker(array $taskData): int
    {
        $workers = $this->redis->sMembers('dsp:workers');
        $sent = 0;

        foreach ($workers as $fdStr) {
            $fd = (int)$fdStr;
            if ($fd > 0) {
                try {
                    $this->sender->push($fd, json_encode($taskData, JSON_UNESCAPED_UNICODE));
                    $sent++;
                } catch (\Throwable $e) {
                    // Worker 可能已断开
                    $this->redis->sRem('dsp:workers', $fdStr);
                }
            }
        }

        return $sent;
    }

    /**
     * 通知 GPU 监控器
     */
    private function notifyGpuMonitors(array $data): void
    {
        $notifyKey = 'dsp:gpu_monitor_notify';
        $msg = json_encode($data, JSON_UNESCAPED_UNICODE);
        $this->redis->rPush($notifyKey, $msg);

        $monitorCount = (int)$this->redis->sCard('dsp:gpu_monitors');
        $queueLen = (int)$this->redis->lLen($notifyKey);
        echo "[HeyGemProxy] GPU Monitor 通知入队: monitors={$monitorCount}, queue_len={$queueLen}\n";
    }
}
