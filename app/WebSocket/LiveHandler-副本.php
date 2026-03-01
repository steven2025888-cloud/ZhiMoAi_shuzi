<?php

namespace App\WebSocket;

use Hyperf\Contract\OnOpenInterface;
use Hyperf\Contract\OnMessageInterface;
use Hyperf\Contract\OnCloseInterface;

/**
 * @WebSocketController(server="ws_live")
 */
class LiveHandler implements OnOpenInterface, OnMessageInterface, OnCloseInterface
{
    public function onOpen($server, $request): void
    {
        $server->push($request->fd, json_encode([
            'event' => 'open',
            'message' => 'ws_live connected',
        ], JSON_UNESCAPED_UNICODE));
    }

    
    public function onMessage($server, $frame): void
    {
        $raw = (string) ($frame->data ?? '');
        if ($raw === '') {
            return;
        }
    
    
        // 🔥 广播给所有已建立的 WS 连接
        foreach ($server->connections as $fd) {
            if ($server->isEstablished($fd)) {
                $server->push($fd, $raw);
            }
        }
    }
    // public function onMessage($server, $frame): void
    // {
    //     $raw = (string) ($frame->data ?? '');
    //     if ($raw === '') {
    //         return;
    //     }
    
    //     $data = json_decode($raw, true);
    //     if (!is_array($data)) {
    //         return;
    //     }
    
        
    //     $content  = trim((string) ($data['content'] ?? ''));
    
    //     if ($content === '') {
    //         return;
    //     }
    
    //     $payload = json_encode([
    //         'type'    => 1,
    //         'content' => "读‘".$content."’",
    //     ], JSON_UNESCAPED_UNICODE);
    
    //     // 🔥 广播给所有已建立的 WS 连接
    //     foreach ($server->connections as $fd) {
    //         if ($server->isEstablished($fd)) {
    //             $server->push($fd, $payload);
    //         }
    //     }
    // }
    
    /**
     * 只转发弹幕（type = 1）
     */
    // public function onMessage($server, $frame): void
    // {
    //     $raw = (string) ($frame->data ?? '');
    //     if ($raw === '') {
    //         return;
    //     }
    
    //     $data = json_decode($raw, true);
    //     if (!is_array($data)) {
    //         return;
    //     }
    
    //     // 只处理弹幕
    //     if (($data['type'] ?? null) !== 1) {
    //         return;
    //     }
    
    //     $nickname = trim((string) ($data['nickname'] ?? ''));
    //     $content  = trim((string) ($data['content'] ?? ''));
    
    //     if ($content === '') {
    //         return;
    //     }
    
    //     // ✅ 从昵称中“提取中文部分”，比如：王12 -> 王，@王_哥123 -> 王哥
    //     $useNickname = '';
    //     if ($nickname !== '') {
    //         if (preg_match_all('/[\x{4e00}-\x{9fa5}]+/u', $nickname, $m) && !empty($m[0])) {
    //             $useNickname = implode('', $m[0]); // 把所有中文片段拼起来
    //         }
    //     }
    
    //     // 组合新的文案
    //     if ($useNickname !== '') {
    //         $newContent = "看到{$useNickname}大哥还是{$useNickname}大姐问{$content}，这边给大家解答一下";
    //     } else {
    //         $newContent = "看到有朋友问{$content}，这边给大家解答一下";
    //     }
    
    //     $payload = json_encode([
    //         'type'    => 1,
    //         'content' => $newContent,
    //     ], JSON_UNESCAPED_UNICODE);
    
    //     // 🔥 广播给所有已建立的 WS 连接
    //     foreach ($server->connections as $fd) {
    //         if ($server->isEstablished($fd)) {
    //             $server->push($fd, $payload);
    //         }
    //     }
    // }



    public function onClose($server, $fd, $reactorId): void
    {
    }
}
