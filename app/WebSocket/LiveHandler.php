<?php

namespace App\WebSocket;

use App\Model\LicenseCard;
use Hyperf\Contract\OnOpenInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnCloseInterface;
use Hyperf\Redis\Redis;

class LiveHandler implements OnOpenInterface, OnMessageInterface, OnCloseInterface
{
    protected Redis $redis;

    public function __construct(Redis $redis)
    {
        $this->redis = $redis;
    }

    public function onOpen($server, $request): void
    {
        $server->push($request->fd, json_encode([
            'event' => 'open',
            'message' => 'ws_live connected, please auth'
        ], JSON_UNESCAPED_UNICODE));
    }

    public function onMessage($server, $frame): void
    {
        $fd = $frame->fd;
        $raw = (string)$frame->data;
        $data = json_decode($raw, true);

        // 1️⃣ 认证（增加：卡密合法性校验）
        if (is_array($data) && ($data['event'] ?? '') === 'auth') {
            $licenseKey = trim($data['license_key'] ?? '');
            if (!$licenseKey) return;

            $card = LicenseCard::where('license_key', $licenseKey)->first();
            if (!$card) {
                $server->push($fd, json_encode([
                    'event' => 'auth_fail',
                    'msg'   => '卡密不存在'
                ], JSON_UNESCAPED_UNICODE));
                $server->disconnect($fd);
                return;
            }

            if ((int)$card->status === 3) {
                $server->push($fd, json_encode([
                    'event' => 'auth_fail',
                    'msg'   => '卡密已封禁'
                ], JSON_UNESCAPED_UNICODE));
                $server->disconnect($fd);
                return;
            }

            if ($card->start_time && strtotime($card->start_time) > time()) {
                $server->push($fd, json_encode([
                    'event' => 'auth_fail',
                    'msg'   => '卡密未到生效时间'
                ], JSON_UNESCAPED_UNICODE));
                $server->disconnect($fd);
                return;
            }

            if ($card->end_time && strtotime($card->end_time) < time()) {
                // 过期就顺便落库更新
                $card->status = 2;
                $card->save();

                $server->push($fd, json_encode([
                    'event' => 'auth_fail',
                    'msg'   => '卡密已过期'
                ], JSON_UNESCAPED_UNICODE));
                $server->disconnect($fd);
                return;
            }

            // ✅ 校验通过才允许绑定
            $this->redis->set("ws:fd:{$fd}", $licenseKey);
            $this->redis->sAdd("ws:license:{$licenseKey}", $fd);

            $server->push($fd, json_encode([
                'event'       => 'auth_ok',
                'license_key' => $licenseKey,
                'expire_time' => $card->end_time,   // 给前端显示
            ], JSON_UNESCAPED_UNICODE));

            return;
        }

        // 2️⃣ 必须已认证
        $licenseKey = $this->redis->get("ws:fd:{$fd}");
        if (!$licenseKey) return;

        // 3️⃣ 广播给同卡密所有 fd（跨进程）
        $fds = $this->redis->sMembers("ws:license:{$licenseKey}");
        foreach ($fds as $clientFd) {
            if ($server->isEstablished((int)$clientFd)) {
                $server->push((int)$clientFd, $raw);
            }
        }
    }

    public function onClose($server, $fd, $reactorId): void
    {
        $licenseKey = $this->redis->get("ws:fd:{$fd}");
        if ($licenseKey) {
            $this->redis->del("ws:fd:{$fd}");
            $this->redis->sRem("ws:license:{$licenseKey}", $fd);
        }
    }
}
