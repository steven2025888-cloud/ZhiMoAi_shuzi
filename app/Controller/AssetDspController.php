<?php

declare(strict_types=1);

namespace App\Controller;

use App\Support\ApiResponse;
use App\WebSocket\DspTaskDispatcher;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\Redis\Redis;
use function Hyperf\Support\env;
/**
 * 资产管理（手机/PC端通过 PHP API 端操作）
 *
 * list  → 直接转发给 GPU 服务器 HTTP，GPU 离线则返回错误
 * delete → 先删 DB（Redis 缓存的积压队列中的文件路径记录），
 *           再通过 WebSocket 通知 GPU 删除物理文件（GPU 离线则入队，开机后执行）
 *
 * 注意：资产的"数据库"是 GPU 服务器上的 SQLite（assets.db）。
 * 由于 GPU 按需开机，list/delete 需要穿透到 GPU HTTP 接口或走 WS 队列。
 *
 * list 接口处理策略：
 *   - GPU 在线 → 直接代理 /api/asset/list
 *   - GPU 离线 → 返回 gpu.power.offline 错误，让前端提示用户
 *
 * delete 接口处理策略：
 *   - 通过 WS gpu.job.submit 下发 delete_asset 任务
 *   - GPU 在线 → 立即执行，返回成功
 *   - GPU 离线 → 入队，返回 queued 状态，前端提示"已排队，开机后执行"
 */
class AssetDspController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected Redis $redis;

    /**
     * GET /api/asset/list?asset_type=voice
     * （兼容 /api/dsp/asset/list）
     * 代理到 GPU 服务器的 /api/asset/list
     */
    public function list(): array
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $assetType  = (string)$this->request->input('asset_type', '');

            $synthUrl = $this->_getSynthUrl();
            if (!$synthUrl) {
                return ApiResponse::fail('GPU服务器地址未配置');
            }

            $url = rtrim($synthUrl, '/') . '/api/asset/list?license_key=' . urlencode($licenseKey);
            if ($assetType !== '') {
                $url .= '&asset_type=' . urlencode($assetType);
            }

            $result = $this->_httpGet($url);
            if ($result === null) {
                return ApiResponse::fail('GPU服务器未上线，请稍后重试');
            }

            return $result;
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    /**
     * POST /api/asset/delete
     * （兼容 /api/dsp/asset/delete）
     * body: { "id": 123 }
     *
     * 流程：
     * 1. 先通过 HTTP 代理请求 GPU 删除（在线时立即删除）
     * 2. GPU 离线时，通过 WS gpu.job.submit 下发 delete_asset 任务入队
     */
    public function delete(): array
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $assetId    = (int)$this->request->input('id', 0);

            if ($assetId <= 0) {
                return ApiResponse::fail('缺少 id');
            }

            $synthUrl = $this->_getSynthUrl();
            if (!$synthUrl) {
                return ApiResponse::fail('GPU服务器地址未配置');
            }

            // ── 优先直接 HTTP 调用 GPU 删除 ─────────────────────────
            $result = $this->_httpPost(
                rtrim($synthUrl, '/') . '/api/asset/delete',
                ['id' => $assetId, 'license_key' => $licenseKey]
            );

            if ($result !== null) {
                // GPU 在线，直接返回结果
                return $result;
            }

            // ── GPU 离线：通过 WS gpu.job.submit 入队 ────────────────────
            $requestId = uniqid('del_asset_');
            $this->_enqueueGpuTask($licenseKey, $requestId, 'delete_asset', [
                'id'          => $assetId,
                'license_key' => $licenseKey,
            ]);

            return ApiResponse::ok([
                'queued'     => true,
                'request_id' => $requestId,
                'msg'        => 'GPU服务器未上线，删除任务已排队，服务器启动后自动执行（约2分钟）',
            ], '已排队');

        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    // ─────────────────────── 私有方法 ────────────────────────────────

    /**
     * 获取 GPU 服务器地址（从配置或固定值）
     */
    private function _getSynthUrl(): string
    {
        return (string)(env('HEYGEM_SERVER_URL', 'http://117.50.91.129:8383'));
    }

    /**
     * HTTP GET，超时3秒，失败返回 null
     */
    private function _httpGet(string $url): ?array
    {
        $ctx = stream_context_create([
            'http' => [
                'method'  => 'GET',
                'timeout' => 3,
                'ignore_errors' => true,
            ],
        ]);
        try {
            $body = @file_get_contents($url, false, $ctx);
            if ($body === false) return null;
            $data = json_decode($body, true);
            return is_array($data) ? $data : null;
        } catch (\Throwable) {
            return null;
        }
    }

    /**
     * HTTP POST JSON，超时3秒，失败返回 null
     */
    private function _httpPost(string $url, array $payload): ?array
    {
        $body = json_encode($payload);
        $ctx  = stream_context_create([
            'http' => [
                'method'        => 'POST',
                'header'        => "Content-Type: application/json\r\nContent-Length: " . strlen($body),
                'content'       => $body,
                'timeout'       => 3,
                'ignore_errors' => true,
            ],
        ]);
        try {
            $resp = @file_get_contents($url, false, $ctx);
            if ($resp === false) return null;
            $data = json_decode($resp, true);
            return is_array($data) ? $data : null;
        } catch (\Throwable) {
            return null;
        }
    }

    /**
     * 将 gpu.job.submit 消息存入 Redis pending 队列
     * （Dsp.php WebSocket 开机后会批量取出下发给 worker）
     */
    private function _enqueueGpuTask(string $licenseKey, string $requestId, string $taskType, array $payload): void
    {
        $msg = json_encode([
            'type'       => 'gpu.job.submit',
            'task_type'  => $taskType,
            'request_id' => $requestId,
            'key'        => $licenseKey,
            'sender_fd'  => 0, // HTTP 触发，无 WS fd
            'payload'    => $payload,
        ], JSON_UNESCAPED_UNICODE);

        $queueKey = 'dsp:pending_tasks:' . $licenseKey;
        $len = (int)$this->redis->lLen($queueKey);
        if ($len >= 100) {
            $this->redis->lPop($queueKey);
        }
        $this->redis->rPush($queueKey, $msg);
        echo "[AssetDsp] 任务入队: key={$licenseKey} task_type={$taskType} request_id={$requestId}\n";
    }
}
