<?php

declare(strict_types=1);

namespace App\WebSocket;

use Hyperf\Contract\OnCloseInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnOpenInterface;
use Hyperf\Redis\Redis;
use Swoole\Timer;

/**
 * WebSocket 中转 (Redis 存储，跨实例共享)
 *
 * ── GPU 服务器开机协议（统一）────────────────────────────────────────
 * GPU 服务器启动后连接 WS，发送：
 *   { "type": "register", "role": "worker" }
 * 服务端回复：
 *   { "type": "registered", "role": "worker" }
 * 服务端立即广播给所有在线客户端：
 *   { "type": "gpu.power.online", "msg": "GPU服务器已上线，可以开始处理任务" }
 * 同时将 Redis 中积压的 pending_tasks 队列批量推送给 GPU：
 *   { "type": "gpu.job.dispatch.batch", "data": { "jobs": [...] } }
 *
 * ── 客户端/手机端任务提交流程（统一）─────────────────────────────────
 * 当客户端提交任务（url / chatglm_video / gpu.job.submit）时：
 *   - 若有在线 worker → 直接转发，回复 ack
 *   - 若无在线 worker → 缓存到 Redis List `dsp:pending_tasks:{key}`
 *     并回复：
 *       { "type": "gpu.power.offline", "request_id": "...", "msg": "GPU服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）" }
 *
 * ── GPU 通用任务消息格式（统一）──────────────────────────────────────
 * 客户端发送：
 *   {
 *     "type": "gpu.job.submit",
 *     "task_type": "delete_asset" | "heygem_submit" | ...,
 *     "request_id": "唯一ID（可选，不传则自动生成）",
 *     "payload": { ...任务参数... }
 *   }
 * GPU 完成后回复（发给原始发送者）：
 *   {
 *     "type": "gpu.job.result",
 *     "task_type": "delete_asset",
 *     "request_id": "...",
 *     "error": false,
 *     "result": { ...结果... }
 *   }
 *
 * ── 删除资产场景示例 ─────────────────────────────────────────────────
 * 手机/PC端 → API（PHP）：POST /api/asset/delete（兼容 /api/dsp/asset/delete）
 *   API 通过 WS 向 GPU 发送 gpu.job.submit:
 *   { "type":"gpu.job.submit", "task_type":"delete_asset", "payload":{"file_path":"..."} }
 *   若 GPU 在线 → 立即执行删文件
 *   若 GPU 离线 → 入队，开机后自动执行
 *
 * 兼容说明：
 *   - 仍兼容旧类型：gpu_task / gpu_task_result / gpu_online / gpu_offline
 *   - 新接入统一使用：gpu.power.* 与 gpu.job.*
 */
class Dsp implements OnMessageInterface, OnOpenInterface, OnCloseInterface
{
    private const KEY_WORKERS      = 'dsp:workers';       // set(fd)
    private const KEY_GPU_MONITORS = 'dsp:gpu_monitors';  // set(fd) GPU 电源监控器
    private const KEY_FD_TO_KEY    = 'dsp:fdToKey';       // hash(fd => key)
    private const KEY_FD_TO_ROLE   = 'dsp:fdToRole';      // hash(fd => 'pc'|'mobile'|'worker'|'gpu_monitor')

    // 每个 license_key 的积压任务队列前缀（List，元素为完整 JSON 字符串）
    private const KEY_PENDING_PFX    = 'dsp:pending_tasks:';
    private const KEY_PENDING_GLOBAL = 'dsp:pending_tasks:__global__';
    // 单 key 积压上限
    private const PENDING_MAX  = 100;
    // GPU 上线后批量下发条数上限
    private const FLUSH_BATCH  = 50;

    // 任务状态跟踪（防止重复提交）
    private const KEY_TASK_STATUS_PFX = 'dsp:task_status:';  // hash(key => {task_type, request_id, status, start_time})
    private const TASK_TIMEOUT = 600;  // 任务超时时间（秒）- 10分钟

    public function __construct(private Redis $redis) {}

    // 静态变量，确保定时器只创建一次
    private static bool $timerStarted = false;

    // ─────────────────────────── 事件 ────────────────────────────────

    public function onOpen($server, $request): void
    {
        $fd = $request->fd;
        echo "[WS] 新连接 fd={$fd} pid=" . getmypid() . "\n";
        $server->push($fd, json_encode(['type' => 'connected', 'fd' => $fd]));

        // 首次连接时启动定时器（只启动一次）
        if (!self::$timerStarted) {
            self::$timerStarted = true;
            echo "[WS] 启动 GPU Monitor 通知检查定时器 (每2秒)\n";

            Timer::tick(2000, function () use ($server) {
                try {
                    $this->_checkAndSendGpuMonitorNotifications($server);
                } catch (\Throwable $e) {
                    echo "[WS] GPU Monitor 通知检查失败: {$e->getMessage()}\n";
                }
            });
        }
    }

    public function onMessage($server, $frame): void
    {
        $fd  = $frame->fd;
        $raw = $frame->data;
        echo "[WS] fd={$fd} 消息: " . mb_substr($raw, 0, 200) . "\n";

        // 检查并发送待处理的 GPU Monitor 通知
        $this->_checkAndSendGpuMonitorNotifications($server);

        $data = json_decode($raw, true);
        if (!is_array($data)) {
            $raw = trim($raw);
            if (str_starts_with($raw, 'http://') || str_starts_with($raw, 'https://')) {
                $data = ['type' => 'url', 'url' => $raw];
            } else {
                return;
            }
        }

        $type = $data['type'] ?? '';

        // ── ping ──────────────────────────────────────────────────────
        if ($type === 'ping') {
            $server->push($fd, json_encode(['type' => 'pong']));
            return;
        }

        // ── 注册 worker (GPU 服务器) ──────────────────────────────────
        if ($type === 'register' && ($data['role'] ?? '') === 'worker') {
            $this->redis->sAdd(self::KEY_WORKERS, (string)$fd);
            $this->redis->hSet(self::KEY_FD_TO_ROLE, (string)$fd, 'worker');
            $server->push($fd, json_encode(['type' => 'registered', 'role' => 'worker']));
            $workers = $this->redis->sMembers(self::KEY_WORKERS);
            echo "[WS] Worker 注册: fd={$fd}  workers=" . json_encode($workers) . "\n";

            // ① 广播 gpu.power.online 给所有在线客户端（兼容旧协议 gpu_online）
            $this->_broadcastGpuOnline($server, [
                'source'    => 'worker',
                'worker_fd' => $fd,
            ]);

            // ② 批量下发 Redis 积压任务给 worker
            $this->_flushPendingTasks($server, $fd);

            return;
        }

        // ── 注册 GPU 电源监控器 ──────────────────────────────────────
        if ($type === 'register' && ($data['role'] ?? '') === 'gpu_monitor') {
            $this->redis->sAdd(self::KEY_GPU_MONITORS, (string)$fd);
            $this->redis->hSet(self::KEY_FD_TO_ROLE, (string)$fd, 'gpu_monitor');
            $server->push($fd, json_encode(['type' => 'registered', 'role' => 'gpu_monitor']));
            echo "[WS] GPU Monitor 注册: fd={$fd}\n";
            return;
        }

        // ── 注册客户端 (PC 或 Mobile) ─────────────────────────────────
        if ($type === 'register' && ($data['key'] ?? '') !== '') {
            $key        = $data['key'];
            $deviceRole = $data['device_type'] ?? 'pc';
            $this->redis->sAdd("dsp:client_fds:{$key}", (string)$fd);
            $this->redis->hSet(self::KEY_FD_TO_KEY, (string)$fd, (string)$key);
            $this->redis->hSet(self::KEY_FD_TO_ROLE, (string)$fd, $deviceRole);
            $this->redis->hSet("dsp:device_fd:{$key}", $deviceRole, (string)$fd);
            $server->push($fd, json_encode([
                'type'        => 'registered',
                'key'         => $key,
                'device_type' => $deviceRole,
            ]));
            $fds = $this->redis->sMembers("dsp:client_fds:{$key}");
            echo "[WS] 客户端注册: fd={$fd} key={$key} device_type={$deviceRole} 当前连接数=" . count($fds) . "\n";
            return;
        }

        $senderKey = (string)($this->redis->hGet(self::KEY_FD_TO_KEY, (string)$fd) ?: '');

        // ── 客户端发链接 → 提取视频文案 ───────────────────────────────
        if ($senderKey !== '' && $type === 'url') {
            $msg  = json_encode(['type' => 'url', 'url' => $data['url'] ?? '', 'key' => $senderKey]);
            $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
            // 同时通知 GPU 监控器有任务
            $this->_notifyGpuMonitors($server, ['type' => 'url', 'key' => $senderKey]);
            if ($sent === 0) {
                $this->_enqueuePending($senderKey, $msg);
                $server->push($fd, json_encode([
                    'type'       => 'gpu.power.offline',
                    'version'    => '1.0',
                    'source'     => 'api',
                    'target'     => 'client',
                    'ts'         => time(),
                    'request_id' => uniqid('gpu_offline_'),
                    'trace_id'   => uniqid('trace_'),
                    'msg'        => 'GPU服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）',
                    'data'       => [
                        'status' => 'offline',
                    ],
                ], JSON_UNESCAPED_UNICODE));
            } else {
                $server->push($fd, json_encode(['type' => 'ack', 'msg' => '已提交']));
            }
            return;
        }

        // ── 客户端发 chatglm_video → 视频生成 ─────────────────────────
        if ($senderKey !== '' && $type === 'chatglm_video') {
            $requestId = $data['request_id'] ?? '';
            $msg = json_encode([
                'type'       => 'chatglm_video',
                'content'    => $data['content'] ?? '',
                'key'        => $senderKey,
                'request_id' => $requestId,
                'sender_fd'  => $fd,
            ]);
            $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
            // 同时通知 GPU 监控器有任务
            $this->_notifyGpuMonitors($server, ['type' => 'chatglm_video', 'key' => $senderKey]);
            if ($sent === 0) {
                $this->_enqueuePending($senderKey, $msg);
                $reply = [
                    'type'       => 'gpu.power.offline',
                    'version'    => '1.0',
                    'source'     => 'api',
                    'target'     => 'client',
                    'ts'         => time(),
                    'request_id' => $requestId !== '' ? $requestId : uniqid('gpu_offline_'),
                    'trace_id'   => uniqid('trace_'),
                    'msg'        => 'GPU服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）',
                    'data'       => [
                        'status' => 'offline',
                    ],
                ];
                $server->push($fd, json_encode($reply, JSON_UNESCAPED_UNICODE));
            } else {
                $ack = ['type' => 'ack', 'msg' => '已提交'];
                if ($requestId !== '') $ack['request_id'] = $requestId;
                $server->push($fd, json_encode($ack));
            }
            return;
        }

        // ── 通用 GPU 任务（delete_asset / heygem_submit 等）───────────
        // 格式: { "type":"gpu.job.submit", "task_type":"...", "request_id":"...", "payload":{} }
        if ($senderKey !== '' && ($type === 'gpu_task' || $type === 'gpu.job.submit')) {
            $requestId = $data['request_id'] ?? uniqid('gt_');
            $taskType  = $data['task_type'] ?? '';

            // 检查是否有进行中的任务（防止重复提交）
            $checkResult = $this->_checkTaskStatus($senderKey, $taskType);

            if (!$checkResult['can_submit']) {
                // 不能提交，返回错误
                $server->push($fd, json_encode([
                    'type'       => 'error',
                    'request_id' => $requestId,
                    'task_type'  => $taskType,
                    'msg'        => $checkResult['reason'],
                    'old_request_id' => $checkResult['old_request_id'],
                ], JSON_UNESCAPED_UNICODE));
                echo "[WS] gpu.job.submit 拒绝: key={$senderKey} task_type={$taskType} reason={$checkResult['reason']}\n";
                return;
            }

            // 如果是替换队列中的任务，先取消旧任务
            if ($checkResult['reason'] === 'replace_queued' && $checkResult['old_request_id'] !== '') {
                $this->_cancelQueuedTask($senderKey, $checkResult['old_request_id']);
                echo "[WS] 替换队列任务: key={$senderKey} old={$checkResult['old_request_id']} new={$requestId}\n";
            }

            $msg = json_encode([
                'type'       => 'gpu.job.submit',
                'task_type'  => $taskType,
                'request_id' => $requestId,
                'key'        => $senderKey,
                'sender_fd'  => $fd,
                'payload'    => $data['payload'] ?? [],
            ], JSON_UNESCAPED_UNICODE);

            $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
            // 同时通知 GPU 监控器有任务
            $this->_notifyGpuMonitors($server, ['type' => 'gpu.job.submit', 'task_type' => $taskType, 'key' => $senderKey]);

            if ($sent === 0) {
                // GPU 离线，任务入队
                $this->_enqueuePending($senderKey, $msg);
                // 设置任务状态为 queued
                $this->_setTaskStatus($senderKey, $taskType, $requestId, 'queued');
                $server->push($fd, json_encode([
                    'type'       => 'gpu.power.offline',
                    'version'    => '1.0',
                    'source'     => 'api',
                    'target'     => 'client',
                    'ts'         => time(),
                    'request_id' => $requestId,
                    'trace_id'   => uniqid('trace_'),
                    'task_type'  => $taskType,
                    'msg'        => 'GPU服务器未上线，任务已排队，服务器启动后自动执行（约2分钟）',
                    'data'       => [
                        'status'    => 'offline',
                        'task_type' => $taskType,
                    ],
                ], JSON_UNESCAPED_UNICODE));
            } else {
                // GPU 在线，任务已提交
                // 设置任务状态为 processing
                $this->_setTaskStatus($senderKey, $taskType, $requestId, 'processing');
                $server->push($fd, json_encode([
                    'type'       => 'ack',
                    'request_id' => $requestId,
                    'task_type'  => $taskType,
                    'msg'        => '已提交到GPU服务器',
                ]));
            }
            echo "[WS] gpu.job.submit: key={$senderKey} task_type={$taskType} request_id={$requestId} sent={$sent}\n";
            return;
        }

        // ── Worker 返回任务结果（新协议兼容旧协议）─────────────────────
        if ($type === 'gpu_task_result' || $type === 'gpu.job.result') {
            if (!$this->redis->sIsMember(self::KEY_WORKERS, (string)$fd)) {
                echo "[WS] gpu.job.result 忽略: fd={$fd} 不是 worker\n";
                return;
            }
            $key       = $data['key'] ?? '';
            $requestId = $data['request_id'] ?? '';
            $senderFd  = (int)($data['sender_fd'] ?? 0);
            $isError   = $data['error'] ?? false;
            $taskType  = $data['task_type'] ?? '';
            $payload   = [
                'type'       => 'gpu.job.result',
                'task_type'  => $taskType,
                'request_id' => $requestId,
            ];
            if ($isError) {
                $payload['error']     = true;
                $payload['error_msg'] = $data['error_msg'] ?? '未知错误';
            } else {
                $payload['result'] = $data['result'] ?? [];
            }
            $payloadJson = json_encode($payload, JSON_UNESCAPED_UNICODE);
            $this->_replyToClient($server, $key, $senderFd, $payloadJson);

            // 兼容旧客户端：额外再发一份旧类型
            $legacyPayload = $payload;
            $legacyPayload['type'] = 'gpu_task_result';
            $this->_replyToClient($server, $key, $senderFd, json_encode($legacyPayload, JSON_UNESCAPED_UNICODE));

            // 清除任务状态（任务已完成）
            if ($key !== '' && $taskType !== '') {
                $this->_clearTaskStatus($key, $taskType);
                echo "[WS] 清除任务状态: key={$key} task_type={$taskType}\n";
            }

            $tag = $isError ? '错误' : '成功';
            echo "[WS] gpu.job.result {$tag}: key={$key} task_type={$taskType} request_id={$requestId}\n";
            return;
        }

        // ── 电源在线消息（worker 或 gpu_monitor 均可发送）───────────
        if ($type === 'gpu.power.online') {
            $isWorker = $this->redis->sIsMember(self::KEY_WORKERS, (string)$fd);
            $isGpuMonitor = $this->redis->sIsMember(self::KEY_GPU_MONITORS, (string)$fd);
            if (!$isWorker && !$isGpuMonitor) {
                echo "[WS] gpu.power.online 忽略: fd={$fd} 不是 worker 或 gpu_monitor\n";
                return;
            }

            $from = $isWorker ? 'worker' : 'gpu_monitor';
            echo "[WS] gpu.power.online 来自 {$from}: fd={$fd}\n";

            // 广播在线通知（老协议 + 新协议）
            $this->_broadcastGpuOnline($server, [
                'status' => 'online',
                'from'   => $from,
                'request_id' => $data['request_id'] ?? '',
            ]);

            // Worker 上线时，把 pending 队列打包后推给 worker
            if ($isWorker) {
                $this->_flushPendingTasks($server, $fd);
            }
            return;
        }

        // ── GPU 开机请求（PC端发起）──────────────────────────────────────
        if ($type === 'gpu.power.boot') {
            echo "[WS] 收到 GPU 开机请求: fd={$fd}\n";
            // 转发给所有 GPU 监控器
            $this->_notifyGpuMonitors($server, [
                'type' => 'gpu.power.boot',
                'source' => 'client',
                'fd' => $fd,
                'request_id' => $data['request_id'] ?? uniqid('boot_'),
                'msg' => $data['msg'] ?? '请求启动GPU',
            ]);
            return;
        }

        // ── GPU 状态查询（PC端发起 → 转发给 gpu_monitor）─────────────────
        if ($type === 'gpu.status.query') {
            echo "[WS] 收到 GPU 状态查询: fd={$fd}\n";
            $this->_notifyGpuMonitors($server, [
                'type' => 'gpu.status.query',
                'source' => 'client',
                'sender_fd' => $fd,
                'request_id' => $data['request_id'] ?? uniqid('sq_'),
            ]);
            return;
        }

        // ── GPU 状态响应（gpu_monitor 返回 → 转发给请求方客户端）──────────
        if ($type === 'gpu.status.response' && $this->redis->sIsMember(self::KEY_GPU_MONITORS, (string)$fd)) {
            $requestId = $data['request_id'] ?? '';
            $status = $data['status'] ?? 'unknown';
            $state = (string)($data['State'] ?? $data['state'] ?? '');

            // 兼容云厂商状态字段：State=Initializing 视为启动中
            if ($state !== '' && strcasecmp($state, 'Initializing') === 0) {
                $status = 'starting';
            }
            echo "[WS] GPU 状态响应: status={$status}, request_id={$requestId}\n";
            // 广播给所有客户端（让所有在线客户端都知道当前状态）
            $this->_broadcastToClients($server, json_encode([
                'type' => 'gpu.status.response',
                'status' => $status,
                'State' => $state,
                'request_id' => $requestId,
                'fresh' => $data['fresh'] ?? false,
            ], JSON_UNESCAPED_UNICODE));
            return;
        }


        // ── Worker 返回提取视频文案结果 ───────────────────────────────
        if ($this->redis->sIsMember(self::KEY_WORKERS, (string)$fd) && $type === 'result') {
            $key     = $data['key'] ?? '';
            $content = $data['content'] ?? '';
            $isError = $data['error'] ?? false;
            $targetFds = $this->redis->sMembers("dsp:client_fds:{$key}");
            $sent = 0;
            foreach ($targetFds as $targetFdStr) {
                $targetFd = (int)$targetFdStr;
                if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                    $p = ['type' => 'result', 'content' => $content];
                    if ($isError) $p['error'] = true;
                    $server->push($targetFd, json_encode($p, JSON_UNESCAPED_UNICODE));
                    $sent++;
                } else {
                    $this->redis->sRem("dsp:client_fds:{$key}", $targetFdStr);
                }
            }
            $tag = $isError ? '错误' : '结果';
            echo "[WS] 提取文案{$tag} → key={$key} 发送到 {$sent} 个连接\n";
            return;
        }

        // ── Worker 返回 chatglm_video 结果 ────────────────────────────
        if ($type === 'chatglm_video_result') {
            if (!$this->redis->sIsMember(self::KEY_WORKERS, (string)$fd)) {
                echo "[WS] chatglm_video_result 忽略: fd={$fd} 不是 worker\n";
                return;
            }
            $key      = $data['key'] ?? '';
            $reqId    = $data['request_id'] ?? '';
            $senderFd = (int)($data['sender_fd'] ?? 0);
            $isError  = $data['error'] ?? false;
            $payload  = ['type' => 'chatglm_video_result'];
            if ($reqId !== '') $payload['request_id'] = $reqId;
            if ($isError) {
                $payload['error']     = true;
                $payload['error_msg'] = $data['error_msg'] ?? '';
            } else {
                $payload['video_url'] = $data['video_url'] ?? '';
                $payload['cover_url'] = $data['cover_url'] ?? '';
            }
            $this->_replyToClient($server, $key, $senderFd, json_encode($payload, JSON_UNESCAPED_UNICODE));
            $tag = $isError ? '错误' : '结果';
            echo "[WS] chatglm_video {$tag} → key={$key} request_id={$reqId}\n";
            return;
        }

        // ── 手机端发任务 → 转发给同 key 的 PC 端 ─────────────────────
        if ($senderKey !== '' && $type === 'mobile_task') {
            $senderRole = (string)($this->redis->hGet(self::KEY_FD_TO_ROLE, (string)$fd) ?: '');
            if ($senderRole !== 'mobile') {
                $server->push($fd, json_encode(['type' => 'error', 'msg' => '仅手机端可发送 mobile_task']));
                return;
            }
            $requestId = $data['request_id'] ?? uniqid('mt_');
            $taskType  = $data['task_type'] ?? '';
            $payload   = $data['payload'] ?? [];
            $pcFd      = (int)($this->redis->hGet("dsp:device_fd:{$senderKey}", 'pc') ?: '');

            if ($pcFd > 0 && $server->isEstablished($pcFd)) {
                $server->push($pcFd, json_encode([
                    'type'       => 'mobile_task',
                    'task_type'  => $taskType,
                    'request_id' => $requestId,
                    'key'        => $senderKey,
                    'sender_fd'  => $fd,
                    'payload'    => $payload,
                ], JSON_UNESCAPED_UNICODE));
                $server->push($fd, json_encode([
                    'type'       => 'ack',
                    'request_id' => $requestId,
                    'msg'        => "已转发到电脑端 (task_type={$taskType})",
                ]));
                echo "[WS] mobile_task: key={$senderKey} task_type={$taskType} → PC fd={$pcFd}\n";
            } else {
                $this->redis->hDel("dsp:device_fd:{$senderKey}", 'pc');
                $server->push($fd, json_encode([
                    'type'       => 'error',
                    'request_id' => $requestId,
                    'msg'        => '电脑端不在线，请先打开电脑端软件',
                ]));
            }
            return;
        }

        // ── PC 端返回手机端任务结果 ───────────────────────────────────
        if ($senderKey !== '' && $type === 'mobile_task_result') {
            $senderRole = (string)($this->redis->hGet(self::KEY_FD_TO_ROLE, (string)$fd) ?: '');
            if ($senderRole !== 'pc') {
                $server->push($fd, json_encode(['type' => 'error', 'msg' => '仅电脑端可发送 mobile_task_result']));
                return;
            }
            $requestId = $data['request_id'] ?? '';
            $senderFd  = (int)($data['sender_fd'] ?? 0);
            $isError   = $data['error'] ?? false;
            $payload   = [
                'type'       => 'mobile_task_result',
                'request_id' => $requestId,
                'task_type'  => $data['task_type'] ?? '',
            ];
            if ($isError) {
                $payload['error']     = true;
                $payload['error_msg'] = $data['error_msg'] ?? '未知错误';
            } else {
                $payload['result'] = $data['result'] ?? [];
            }
            $payloadJson = json_encode($payload, JSON_UNESCAPED_UNICODE);
            if ($senderFd > 0 && $server->isEstablished($senderFd)) {
                $server->push($senderFd, $payloadJson);
            } else {
                $mobileFd = (int)($this->redis->hGet("dsp:device_fd:{$senderKey}", 'mobile') ?: '');
                if ($mobileFd > 0 && $server->isEstablished($mobileFd)) {
                    $server->push($mobileFd, $payloadJson);
                }
            }
            echo "[WS] mobile_task_result → request_id={$requestId}\n";
            return;
        }

        // ── 同步消息：任意设备 → 同 key 的其他设备 ───────────────────
        if ($senderKey !== '' && $type === 'sync') {
            $targetDevice = $data['target_device'] ?? '';
            if ($targetDevice !== '') {
                $targetFd = (int)($this->redis->hGet("dsp:device_fd:{$senderKey}", $targetDevice) ?: '');
                if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                    $server->push($targetFd, json_encode($data, JSON_UNESCAPED_UNICODE));
                    echo "[WS] sync: key={$senderKey} → {$targetDevice} fd={$targetFd}\n";
                }
            }
            return;
        }
    }

    public function onClose($server, int $fd, int $reactorId): void
    {
        $this->redis->sRem(self::KEY_WORKERS, (string)$fd);
        $this->redis->sRem(self::KEY_GPU_MONITORS, (string)$fd);

        $key  = (string)($this->redis->hGet(self::KEY_FD_TO_KEY, (string)$fd) ?: '');
        $role = (string)($this->redis->hGet(self::KEY_FD_TO_ROLE, (string)$fd) ?: '');
        if ($key !== '') {
            $this->redis->sRem("dsp:client_fds:{$key}", (string)$fd);
            if ($role !== '' && $role !== 'worker' && $role !== 'gpu_monitor') {
                $currentFd = (string)($this->redis->hGet("dsp:device_fd:{$key}", $role) ?: '');
                if ($currentFd === (string)$fd) {
                    $this->redis->hDel("dsp:device_fd:{$key}", $role);
                }
            }
        }
        $this->redis->hDel(self::KEY_FD_TO_KEY, (string)$fd);
        $this->redis->hDel(self::KEY_FD_TO_ROLE, (string)$fd);

        echo "[WS] 断开 fd={$fd} key={$key} role={$role}\n";
    }

    // ─────────────────────── 内部工具方法 ────────────────────────────

    /**
     * 向所有在线 worker 分发消息，返回成功发送数量
     */
    private function _dispatchToWorker($server, string $msg, string $key): int
    {
        $workers = $this->redis->sMembers(self::KEY_WORKERS);
        $sent = 0;
        foreach ($workers as $wFdStr) {
            $wFd = (int)$wFdStr;
            if ($wFd > 0 && $server->isEstablished($wFd)) {
                $server->push($wFd, $msg);
                $sent++;
            } else {
                $this->redis->sRem(self::KEY_WORKERS, $wFdStr);
            }
        }
        echo "[WS] dispatchToWorker key={$key} sent={$sent}\n";
        return $sent;
    }

    /**
     * 将任务消息缓存到 pending 队列（GPU 离线时使用）
     */
    private function _enqueuePending(string $key, string $msgJson): void
    {
        $queueKey = $key !== '' ? self::KEY_PENDING_PFX . $key : self::KEY_PENDING_GLOBAL;
        $len = (int)$this->redis->lLen($queueKey);
        if ($len >= self::PENDING_MAX) {
            $this->redis->lPop($queueKey); // 删最旧的，防止无限堆积
            echo "[WS] pending 队列已满，移除最旧任务: key={$key}\n";
        }
        $this->redis->rPush($queueKey, $msgJson);
        $newLen = (int)$this->redis->lLen($queueKey);
        echo "[WS] 任务入队: key={$key} 当前积压={$newLen}\n";
    }

    /**
     * GPU 上线后批量推送所有积压任务给 worker
     */
    private function _flushPendingTasks($server, int $workerFd): void
    {
        $keys  = $this->redis->keys(self::KEY_PENDING_PFX . '*');
        $total = 0;

        foreach ($keys as $queueKey) {
            $batch = 0;
            while ($batch < self::FLUSH_BATCH) {
                $msgJson = $this->redis->lPop($queueKey);
                if ($msgJson === null || $msgJson === false) break;
                if ($server->isEstablished($workerFd)) {
                    $server->push($workerFd, $msgJson);
                    $total++;
                    $batch++;
                } else {
                    // worker 又断线了，把任务放回队列头
                    $this->redis->lPush($queueKey, $msgJson);
                    echo "[WS] flushPending: worker fd={$workerFd} 断线，停止推送\n";
                    return;
                }
            }
        }

        echo "[WS] flushPending: 推送积压任务 {$total} 条给 worker fd={$workerFd}\n";
    }

    /**
     * 广播 gpu.power.online 给所有在线客户端（兼容旧协议与新协议）
     */
    private function _broadcastGpuOnline($server, array $extraData = []): void
    {
        $clientFdSets = $this->redis->keys('dsp:client_fds:*');
        $notified = 0;
        $legacyMsg = json_encode([
            'type' => 'gpu_online',
            'msg'  => 'GPU服务器已上线，可以开始处理任务',
        ], JSON_UNESCAPED_UNICODE);

        $newProtocol = [
            'type'       => 'gpu.power.online',
            'version'    => '1.0',
            'source'     => 'gpu',
            'target'     => 'client',
            'ts'         => time(),
            'request_id' => uniqid('gpu_power_online_'),
            'trace_id'   => uniqid('trace_'),
            'data'       => array_merge([
                'status' => 'online',
                'msg'    => 'GPU服务器已上线，可以开始处理任务',
            ], $extraData),
        ];
        $newMsg = json_encode($newProtocol, JSON_UNESCAPED_UNICODE);

        foreach ($clientFdSets as $setKey) {
            foreach ($this->redis->sMembers($setKey) as $fdStr) {
                $targetFd = (int)$fdStr;
                if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                    $server->push($targetFd, $legacyMsg);
                    $server->push($targetFd, $newMsg);
                    $notified++;
                } else {
                    $this->redis->sRem($setKey, $fdStr);
                }
            }
        }
        echo "[WS] gpu.power.online(兼容gpu_online) 广播: {$notified} 个客户端\n";
    }

    /**
     * 广播消息给所有在线客户端（PC + Mobile）
     */
    private function _broadcastToClients($server, string $msgJson): void
    {
        $clientFdSets = $this->redis->keys('dsp:client_fds:*');
        $sent = 0;
        foreach ($clientFdSets as $setKey) {
            foreach ($this->redis->sMembers($setKey) as $fdStr) {
                $targetFd = (int)$fdStr;
                if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                    $server->push($targetFd, $msgJson);
                    $sent++;
                } else {
                    $this->redis->sRem($setKey, $fdStr);
                }
            }
        }
        echo "[WS] broadcastToClients: sent={$sent}\n";
    }

    /**
     * 回复原始发送者（优先精确 fd，回退到该 key 所有连接）
     */
    private function _replyToClient($server, string $key, int $senderFd, string $payloadJson): void
    {
        if ($senderFd > 0 && $server->isEstablished($senderFd)) {
            $server->push($senderFd, $payloadJson);
            return;
        }
        $targetFds = $this->redis->sMembers("dsp:client_fds:{$key}");
        $sent = 0;
        foreach ($targetFds as $fdStr) {
            $targetFd = (int)$fdStr;
            if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                $server->push($targetFd, $payloadJson);
                $sent++;
            } else {
                $this->redis->sRem("dsp:client_fds:{$key}", $fdStr);
            }
        }
        echo "[WS] replyToClient 广播: key={$key} sent={$sent}\n";
    }

    /**
     * 通知所有 GPU 监控器有新任务
     */
    private function _notifyGpuMonitors($server, array $data): void
    {
        $monitors = $this->redis->sMembers(self::KEY_GPU_MONITORS);
        $sent = 0;
        $msg = json_encode($data, JSON_UNESCAPED_UNICODE);
        foreach ($monitors as $fdStr) {
            $fd = (int)$fdStr;
            if ($fd > 0 && $server->isEstablished($fd)) {
                $server->push($fd, $msg);
                $sent++;
            } else {
                $this->redis->sRem(self::KEY_GPU_MONITORS, $fdStr);
            }
        }
        if ($sent > 0) {
            echo "[WS] 通知 GPU Monitor: type={$data['type']} sent={$sent}\n";
        }
    }

    /**
     * 检查任务状态（防止重复提交）
     *
     * @return array ['can_submit' => bool, 'reason' => string, 'old_request_id' => string]
     */
    private function _checkTaskStatus(string $key, string $taskType): array
    {
        $statusKey = self::KEY_TASK_STATUS_PFX . $key;
        $taskData = $this->redis->hGet($statusKey, $taskType);

        if (!$taskData) {
            // 没有进行中的任务，可以提交
            return ['can_submit' => true, 'reason' => '', 'old_request_id' => ''];
        }

        $task = json_decode($taskData, true);
        $startTime = $task['start_time'] ?? 0;
        $status = $task['status'] ?? 'unknown';
        $requestId = $task['request_id'] ?? '';
        $currentTime = time();
        $elapsed = $currentTime - $startTime;

        // 检查任务是否超时（10分钟）
        if ($elapsed > self::TASK_TIMEOUT) {
            // 任务超时，视为失败，可以重新提交
            echo "[WS] 任务超时: key={$key} task_type={$taskType} elapsed={$elapsed}s\n";
            $this->redis->hDel($statusKey, $taskType);
            return ['can_submit' => true, 'reason' => 'timeout', 'old_request_id' => $requestId];
        }

        // 有进行中的任务
        if ($status === 'processing') {
            // GPU 正在处理，不能提交
            return [
                'can_submit' => false,
                'reason' => "任务处理中，请等待完成（已用时 {$elapsed}秒）",
                'old_request_id' => $requestId
            ];
        } elseif ($status === 'queued') {
            // 任务在队列中（GPU 离线），可以取消旧任务
            return [
                'can_submit' => true,
                'reason' => 'replace_queued',
                'old_request_id' => $requestId
            ];
        }

        return ['can_submit' => true, 'reason' => '', 'old_request_id' => ''];
    }

    /**
     * 设置任务状态
     */
    private function _setTaskStatus(string $key, string $taskType, string $requestId, string $status): void
    {
        $statusKey = self::KEY_TASK_STATUS_PFX . $key;
        $taskData = json_encode([
            'task_type' => $taskType,
            'request_id' => $requestId,
            'status' => $status,  // 'queued' | 'processing' | 'completed' | 'failed'
            'start_time' => time(),
        ], JSON_UNESCAPED_UNICODE);

        $this->redis->hSet($statusKey, $taskType, $taskData);
        // 设置过期时间（1小时）
        $this->redis->expire($statusKey, 3600);
    }

    /**
     * 清除任务状态
     */
    private function _clearTaskStatus(string $key, string $taskType): void
    {
        $statusKey = self::KEY_TASK_STATUS_PFX . $key;
        $this->redis->hDel($statusKey, $taskType);
    }

    /**
     * 取消队列中的旧任务
     */
    private function _cancelQueuedTask(string $key, string $oldRequestId): void
    {
        $queueKey = self::KEY_PENDING_PFX . $key;
        $tasks = $this->redis->lRange($queueKey, 0, -1);

        foreach ($tasks as $index => $taskJson) {
            $task = json_decode($taskJson, true);
            if (isset($task['request_id']) && $task['request_id'] === $oldRequestId) {
                // 找到旧任务，删除
                $this->redis->lRem($queueKey, $taskJson, 1);
                echo "[WS] 取消队列中的旧任务: key={$key} request_id={$oldRequestId}\n";
                break;
            }
        }
    }

    /**
     * 检查并发送待处理的 GPU Monitor 通知
     *
     * 用于从 Redis 队列中获取 HTTP Controller 发送的通知并转发给 GPU Monitor
     */
    private function _checkAndSendGpuMonitorNotifications($server): void
    {
        $notifyKey = 'dsp:gpu_monitor_notify';

        $queueLen = (int)$this->redis->lLen($notifyKey);
        if ($queueLen <= 0) {
            return;
        }

        // 先筛出可用 monitor；若当前无可用连接，不弹出队列，避免消息丢失
        $aliveMonitors = [];
        foreach ($this->redis->sMembers(self::KEY_GPU_MONITORS) as $fdStr) {
            $fd = (int)$fdStr;
            if ($fd > 0 && $server->isEstablished($fd)) {
                $aliveMonitors[] = $fd;
            } else {
                $this->redis->sRem(self::KEY_GPU_MONITORS, (string)$fdStr);
            }
        }

        if (empty($aliveMonitors)) {
            echo "[WS] GPU Monitor 通知待发送={$queueLen}，但当前无在线 monitor，保留队列\n";
            return;
        }

        $messages = [];
        for ($i = 0; $i < 10; $i++) {
            $msg = $this->redis->lPop($notifyKey);
            if ($msg === null || $msg === false) {
                break;
            }
            $messages[] = (string)$msg;
        }

        if (empty($messages)) {
            return;
        }

        $sent = 0;
        foreach ($messages as $msg) {
            $delivered = 0;
            foreach ($aliveMonitors as $fd) {
                if ($server->isEstablished($fd)) {
                    $server->push($fd, $msg);
                    $sent++;
                    $delivered++;
                } else {
                    $this->redis->sRem(self::KEY_GPU_MONITORS, (string)$fd);
                }
            }

            // 全部 monitor 在发送阶段失效时，把消息放回队列头，等待下次重试
            if ($delivered === 0) {
                $this->redis->lPush($notifyKey, $msg);
            }
        }

        if ($sent > 0) {
            echo "[WS] GPU Monitor 通知发送完成: messages=" . count($messages) . ", sent={$sent}\n";
        }
    }
}
