<?php
declare(strict_types=1);

namespace App\Service;

use Hyperf\Redis\Redis;
use Swoole\WebSocket\Server;
use Hyperf\WebSocketServer\Sender;
use Hyperf\WebSocketServer\Collector\FdCollector;

class PythonTaskBus
{
    private const PY_WORKERS_KEY = 'wecom:py_workers';

    public function __construct(
        private Redis $redis,
        private Sender $sender,
    ) {}

    public function dispatch(array $task): void
    {
        // 广播给所有 python worker fd
        $fds = $this->redis->sMembers(self::PY_WORKERS_KEY);
        if (!$fds) return;

        $payload = json_encode($task, JSON_UNESCAPED_UNICODE);
        foreach ($fds as $fd) {
            $fd = (int)$fd;
            try {
                // Sender 会自动找 websocket server 推送
                $this->sender->push($fd, $payload);
            } catch (\Throwable $e) {
                // fd 可能已失效，清理
                $this->redis->sRem(self::PY_WORKERS_KEY, (string)$fd);
            }
        }
    }
}
