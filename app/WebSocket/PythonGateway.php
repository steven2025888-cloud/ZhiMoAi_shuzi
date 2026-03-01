<?php
declare(strict_types=1);

namespace App\WebSocket;

use Hyperf\Contract\OnCloseInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnOpenInterface;
use Hyperf\Redis\Redis;
use Swoole\Http\Request;
use Swoole\WebSocket\Frame;
use Swoole\WebSocket\Server;

class PythonGateway implements OnOpenInterface, OnMessageInterface, OnCloseInterface
{
    private const PY_WORKERS_KEY = 'wecom:py_workers'; // set(fd)
    private const STREAM_KEY_PREFIX = 'wecom:stream:'; // string(json)

    public function __construct(private Redis $redis) {}

    public function onOpen($server, $request): void
    {
        $fd = (int) $request->fd;
        $this->redis->sAdd(self::PY_WORKERS_KEY, (string)$fd);
    
        // 可选：确认连接
        $server->push($fd, json_encode(["type"=>"system","msg"=>"connected"], JSON_UNESCAPED_UNICODE));
    }


public function onMessage($server, $frame): void
{
    $fd = (int) $frame->fd;
    $data = json_decode($frame->data, true);

    if (!is_array($data) || empty($data['type'])) {
        $server->push($fd, json_encode(["type"=>"error","msg"=>"bad json"], JSON_UNESCAPED_UNICODE));
        return;
    }

    if ($data['type'] === 'result') {
        $streamId = (string)($data['stream_id'] ?? '');
        if ($streamId === '') return;

        $payload = [
            "finish" => (bool)($data['finish'] ?? true),
            "content" => (string)($data['content'] ?? ''),
            "updated_at" => time(),
            "msg_item" => $data['msg_item'] ?? null,
        ];

        $this->redis->set(self::STREAM_KEY_PREFIX . $streamId, json_encode($payload, JSON_UNESCAPED_UNICODE));
        $this->redis->expire(self::STREAM_KEY_PREFIX . $streamId, 3600);

        $server->push($fd, json_encode(["type"=>"ack","stream_id"=>$streamId], JSON_UNESCAPED_UNICODE));
        return;
    }

    if ($data['type'] === 'hello') {
        $this->redis->sAdd(self::PY_WORKERS_KEY, (string)$fd);
        $server->push($fd, json_encode(["type"=>"ok","msg"=>"registered"], JSON_UNESCAPED_UNICODE));
        return;
    }
}


public function onClose($server, int $fd, int $reactorId): void
{
    $this->redis->sRem(self::PY_WORKERS_KEY, (string)$fd);
}

}
