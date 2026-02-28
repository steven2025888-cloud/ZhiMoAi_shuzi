<?php

declare(strict_types=1);

namespace App\WebSocket;

use Hyperf\Contract\OnCloseInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnOpenInterface;
use Hyperf\Redis\Redis;

/**
 * WebSocket 中转 (Redis 存储，跨实例共享)
 */
class Dsp implements OnMessageInterface, OnOpenInterface, OnCloseInterface
{
    private const KEY_WORKERS = 'dsp:workers'; // set(fd)
    private const KEY_CLIENTS = 'dsp:clients'; // hash(key => fd)
    private const KEY_FD_TO_KEY = 'dsp:fdToKey'; // hash(fd => key)

    public function __construct(private Redis $redis) {}

    // ---------- 事件 ----------
    public function onOpen($server, $request): void
    {
        $fd = $request->fd;
        echo "[WS] 新连接 fd={$fd} pid=" . getmypid() . "\n";
        $server->push($fd, json_encode(['type' => 'connected', 'fd' => $fd]));
    }

    public function onMessage($server, $frame): void
    {
        $fd  = $frame->fd;
        $raw = $frame->data;
        echo "[WS] fd={$fd} 消息: " . mb_substr($raw, 0, 200) . "\n";

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

        if ($type === 'ping') {
            $server->push($fd, json_encode(['type' => 'pong']));
            return;
        }

        // ---- 注册 worker ----
        if ($type === 'register' && ($data['role'] ?? '') === 'worker') {
            $this->redis->sAdd(self::KEY_WORKERS, (string)$fd);
            $server->push($fd, json_encode(['type' => 'registered', 'role' => 'worker']));
            $workers = $this->redis->sMembers(self::KEY_WORKERS);
            echo "[WS] Worker 注册: fd={$fd}  workers=" . json_encode($workers) . "\n";
            return;
        }

        // ---- 注册客户端 ----
        // 支持同一 key 多个连接（用于并发任务）
        if ($type === 'register' && ($data['key'] ?? '') !== '') {
            $key = $data['key'];
            // 将 fd 添加到该 key 的连接集合中
            $this->redis->sAdd("dsp:client_fds:{$key}", (string)$fd);
            $this->redis->hSet(self::KEY_FD_TO_KEY, (string)$fd, (string)$key);
            $server->push($fd, json_encode(['type' => 'registered', 'key' => $key]));
            $fds = $this->redis->sMembers("dsp:client_fds:{$key}");
            echo "[WS] 客户端注册: fd={$fd} key={$key} 当前连接数=" . count($fds) . "\n";
            return;
        }

        // ---- 客户端发链接 → 转发 worker (提取视频文案) ----
        $senderKey = (string)($this->redis->hGet(self::KEY_FD_TO_KEY, (string)$fd) ?: '');

        if ($senderKey !== '' && $type === 'url') {
            $msg = json_encode(['type' => 'url', 'url' => $data['url'] ?? '', 'key' => $senderKey]);
            $workers = $this->redis->sMembers(self::KEY_WORKERS);
            echo "[WS] 转发链接 key={$senderKey} workers=" . json_encode($workers) . "\n";
            $sent = 0;
            foreach ($workers as $wFdStr) {
                $wFd = (int)$wFdStr;
                if ($wFd > 0 && $server->isEstablished($wFd)) {
                    $server->push($wFd, $msg);
                    $sent++;
                } else {
                    $this->redis->sRem(self::KEY_WORKERS, (string)$wFdStr);
                }
            }
            if ($sent > 0) {
                $server->push($fd, json_encode(['type' => 'ack', 'msg' => '已提交']));
            } else {
                $server->push($fd, json_encode(['type' => 'error', 'msg' => '没有在线的 worker']));
            }
            return;
        }

        // ---- 客户端发 chatglm_video → 转发 worker (视频生成) ----
        if ($senderKey !== '' && $type === 'chatglm_video') {
            $requestId = $data['request_id'] ?? '';
            $msg = json_encode([
                'type' => 'chatglm_video',
                'content' => $data['content'] ?? '',
                'key' => $senderKey,
                'request_id' => $requestId,
                'sender_fd' => $fd  // 记录发送者fd，用于精确回复
            ]);
            $workers = $this->redis->sMembers(self::KEY_WORKERS);
            echo "[WS] 转发 chatglm_video key={$senderKey} request_id={$requestId} workers=" . json_encode($workers) . "\n";
            $sent = 0;
            foreach ($workers as $wFdStr) {
                $wFd = (int)$wFdStr;
                if ($wFd > 0 && $server->isEstablished($wFd)) {
                    $server->push($wFd, $msg);
                    $sent++;
                } else {
                    $this->redis->sRem(self::KEY_WORKERS, (string)$wFdStr);
                }
            }
            if ($sent > 0) {
                $ackMsg = ['type' => 'ack', 'msg' => '已提交'];
                if ($requestId !== '') {
                    $ackMsg['request_id'] = $requestId;
                }
                $server->push($fd, json_encode($ackMsg));
            } else {
                $server->push($fd, json_encode(['type' => 'error', 'msg' => '没有在线的 worker']));
            }
            return;
        }

        // ---- Worker 返回提取视频文案结果 → 发给对应 key 的所有连接 ----
        if ($this->redis->sIsMember(self::KEY_WORKERS, (string)$fd) && $type === 'result') {
            $key     = $data['key'] ?? '';
            $content = $data['content'] ?? '';
            $isError = $data['error'] ?? false;
            $targetFds = $this->redis->sMembers("dsp:client_fds:{$key}");
            $sent = 0;
            foreach ($targetFds as $targetFdStr) {
                $targetFd = (int)$targetFdStr;
                if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                    $payload = [
                        'type'    => 'result',
                        'content' => $content,
                    ];
                    if ($isError) {
                        $payload['error'] = true;
                    }
                    $server->push($targetFd, json_encode($payload, JSON_UNESCAPED_UNICODE));
                    $sent++;
                } else {
                    $this->redis->sRem("dsp:client_fds:{$key}", (string)$targetFdStr);
                }
            }
            $tag = $isError ? '错误' : '结果';
            echo "[WS] 提取文案{$tag} → key={$key} 发送到 {$sent} 个连接\n";
            return;
        }

        // ---- Worker 返回 chatglm_video 结果 → 发给对应的客户端 ----
        if ($type === 'chatglm_video_result') {
            $isWorker = $this->redis->sIsMember(self::KEY_WORKERS, (string)$fd);
            $workers = $this->redis->sMembers(self::KEY_WORKERS);
            echo "[WS] chatglm_video_result 收到: fd={$fd} isWorker=" . ($isWorker ? 'true' : 'false') . " workers=" . json_encode($workers) . "\n";
            
            if (!$isWorker) {
                echo "[WS] chatglm_video_result 忽略: fd={$fd} 不是 worker\n";
                return;
            }
            
            $key       = $data['key'] ?? '';
            $requestId = $data['request_id'] ?? '';
            $senderFd  = (int)($data['sender_fd'] ?? 0);
            $videoUrl  = $data['video_url'] ?? '';
            $coverUrl  = $data['cover_url'] ?? '';
            $isError   = $data['error'] ?? false;
            $errorMsg  = $data['error_msg'] ?? '';

            // 构建响应消息
            $payload = ['type' => 'chatglm_video_result'];
            if ($requestId !== '') {
                $payload['request_id'] = $requestId;
            }
            if ($isError) {
                $payload['error'] = true;
                $payload['error_msg'] = $errorMsg;
            } else {
                $payload['video_url'] = $videoUrl;
                $payload['cover_url'] = $coverUrl;
            }
            $payloadJson = json_encode($payload, JSON_UNESCAPED_UNICODE);

            // 优先发送给原始发送者 fd（如果还在线）
            if ($senderFd > 0 && $server->isEstablished($senderFd)) {
                $server->push($senderFd, $payloadJson);
                $tag = $isError ? '错误' : '结果';
                echo "[WS] chatglm_video {$tag} → key={$key} request_id={$requestId} fd={$senderFd}\n";
            } else {
                // 回退：发送给该 key 的所有连接
                $targetFds = $this->redis->sMembers("dsp:client_fds:{$key}");
                echo "[WS] chatglm_video_result 回退广播: key={$key} request_id={$requestId} fds=" . json_encode($targetFds) . "\n";
                $sent = 0;
                foreach ($targetFds as $targetFdStr) {
                    $targetFd = (int)$targetFdStr;
                    if ($targetFd > 0 && $server->isEstablished($targetFd)) {
                        $server->push($targetFd, $payloadJson);
                        $sent++;
                    } else {
                        $this->redis->sRem("dsp:client_fds:{$key}", (string)$targetFdStr);
                    }
                }
                $tag = $isError ? '错误' : '结果';
                echo "[WS] chatglm_video {$tag} → key={$key} request_id={$requestId} 广播到 {$sent} 个连接\n";
            }
            return;
        }
    }

    public function onClose($server, int $fd, int $reactorId): void
    {
        $this->redis->sRem(self::KEY_WORKERS, (string)$fd);

        $key = (string)($this->redis->hGet(self::KEY_FD_TO_KEY, (string)$fd) ?: '');
        if ($key !== '') {
            // 从该 key 的连接集合中移除此 fd
            $this->redis->sRem("dsp:client_fds:{$key}", (string)$fd);
        }
        $this->redis->hDel(self::KEY_FD_TO_KEY, (string)$fd);

        echo "[WS] 断开 fd={$fd} key={$key}\n";
    }
}
