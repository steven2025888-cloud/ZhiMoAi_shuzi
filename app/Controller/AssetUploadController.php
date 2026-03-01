<?php

declare(strict_types=1);

namespace App\Controller;

use App\Support\ApiResponse;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\Redis\Redis;
use function Hyperf\Support\env;

/**
 * 资产上传控制器
 *
 * 处理手机端/PC端的资产上传（音色、数字人）
 * - GPU 在线：直接转发到 GPU 服务器
 * - GPU 离线：暂存文件到 API 服务器，任务入队，GPU 上线后自动处理
 */
class AssetUploadController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected Redis $redis;

    /**
     * POST /api/asset/upload
     *
     * 表单参数：
     * - file: 上传的文件
     * - asset_type: 资产类型 (voice/avatar)
     * - name: 资产名称
     * - license_key: 授权密钥
     */
    public function upload(): array
    {
        try {
            $licenseKey = (string)$this->request->getAttribute('license_key');
            $assetType = (string)$this->request->input('asset_type', '');
            $name = (string)$this->request->input('name', '');

            if (!$assetType || !$name) {
                return ApiResponse::fail('缺少 asset_type 或 name 参数');
            }

            $file = $this->request->file('file');
            if (!$file || !$file->isValid()) {
                return ApiResponse::fail('文件上传失败');
            }

            $synthUrl = $this->_getSynthUrl();
            if (!$synthUrl) {
                return ApiResponse::fail('GPU服务器地址未配置');
            }

            // ── 尝试直接转发到 GPU 服务器 ──
            $gpuOnline = $this->_checkGpuHealth($synthUrl);

            if ($gpuOnline) {
                // GPU 在线，直接转发
                return $this->_forwardToGpu($synthUrl, $file, $assetType, $name, $licenseKey);
            }

            // ── GPU 离线，暂存文件并入队 ──
            return $this->_queueUpload($file, $assetType, $name, $licenseKey);

        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    /**
     * 检查 GPU 健康状态
     */
    private function _checkGpuHealth(string $synthUrl): bool
    {
        $url = rtrim($synthUrl, '/') . '/api/heygem/health';
        $ctx = stream_context_create([
            'http' => [
                'method' => 'GET',
                'timeout' => 2,
                'ignore_errors' => true,
            ],
        ]);

        try {
            $body = @file_get_contents($url, false, $ctx);
            if ($body === false) return false;

            $data = json_decode($body, true);
            return is_array($data) && ($data['code'] ?? -1) === 0 && ($data['data']['initialized'] ?? false);
        } catch (\Throwable) {
            return false;
        }
    }

    /**
     * 直接转发到 GPU 服务器
     */
    private function _forwardToGpu(string $synthUrl, $file, string $assetType, string $name, string $licenseKey): array
    {
        $url = rtrim($synthUrl, '/') . '/api/asset/upload';
        $secret = env('HEYGEM_API_SECRET', '');

        $boundary = '----WebKitFormBoundary' . uniqid();
        $body = '';

        // 添加表单字段
        $body .= "--{$boundary}\r\n";
        $body .= "Content-Disposition: form-data; name=\"license_key\"\r\n\r\n";
        $body .= "{$licenseKey}\r\n";

        $body .= "--{$boundary}\r\n";
        $body .= "Content-Disposition: form-data; name=\"asset_type\"\r\n\r\n";
        $body .= "{$assetType}\r\n";

        $body .= "--{$boundary}\r\n";
        $body .= "Content-Disposition: form-data; name=\"name\"\r\n\r\n";
        $body .= "{$name}\r\n";

        // 添加文件
        $body .= "--{$boundary}\r\n";
        $body .= "Content-Disposition: form-data; name=\"file\"; filename=\"{$file->getClientFilename()}\"\r\n";
        $body .= "Content-Type: {$file->getClientMediaType()}\r\n\r\n";
        $body .= file_get_contents($file->getRealPath());
        $body .= "\r\n";

        $body .= "--{$boundary}--\r\n";

        $headers = "Content-Type: multipart/form-data; boundary={$boundary}\r\n";
        if ($secret) {
            $headers .= "Authorization: Bearer {$secret}\r\n";
        }

        $ctx = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => $headers,
                'content' => $body,
                'timeout' => 300,
                'ignore_errors' => true,
            ],
        ]);

        try {
            $resp = @file_get_contents($url, false, $ctx);
            if ($resp === false) {
                return ApiResponse::fail('转发到 GPU 服务器失败');
            }

            $data = json_decode($resp, true);
            return is_array($data) ? $data : ApiResponse::fail('GPU 服务器返回格式错误');
        } catch (\Throwable $e) {
            return ApiResponse::fail('转发失败: ' . $e->getMessage());
        }
    }

    /**
     * GPU 离线时，暂存文件并入队
     */
    private function _queueUpload($file, string $assetType, string $name, string $licenseKey): array
    {
        // 创建临时存储目录
        $uploadDir = BASE_PATH . '/runtime/asset_uploads';
        if (!is_dir($uploadDir)) {
            mkdir($uploadDir, 0755, true);
        }

        // 保存文件
        $ext = pathinfo($file->getClientFilename(), PATHINFO_EXTENSION);
        $filename = uniqid('asset_') . '.' . $ext;
        $savePath = $uploadDir . '/' . $filename;

        $file->moveTo($savePath);

        // 将任务入队
        $requestId = uniqid('upload_asset_');
        $this->_enqueueGpuTask($licenseKey, $requestId, 'upload_asset', [
            'file_path' => $savePath,
            'asset_type' => $assetType,
            'name' => $name,
            'license_key' => $licenseKey,
            'original_filename' => $file->getClientFilename(),
        ]);

        return ApiResponse::ok([
            'queued' => true,
            'request_id' => $requestId,
            'msg' => 'GPU 服务器未上线，上传任务已排队，服务器启动后自动处理（约2分钟）',
        ], '已排队');
    }

    /**
     * 获取 GPU 服务器地址
     */
    private function _getSynthUrl(): string
    {
        return (string)(env('HEYGEM_SERVER_URL', 'http://117.50.91.129:8383'));
    }

    /**
     * 将任务存入 Redis 队列
     */
    private function _enqueueGpuTask(string $licenseKey, string $requestId, string $taskType, array $payload): void
    {
        $msg = json_encode([
            'type' => 'gpu.job.submit',
            'task_type' => $taskType,
            'request_id' => $requestId,
            'key' => $licenseKey,
            'sender_fd' => 0,
            'payload' => $payload,
        ], JSON_UNESCAPED_UNICODE);

        $queueKey = 'dsp:pending_tasks:' . $licenseKey;
        $len = (int)$this->redis->lLen($queueKey);
        if ($len >= 100) {
            $this->redis->lPop($queueKey);
        }
        $this->redis->rPush($queueKey, $msg);
        echo "[AssetUpload] 任务入队: key={$licenseKey} task_type={$taskType} request_id={$requestId}\n";
    }
}
