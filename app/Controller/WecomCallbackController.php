<?php
declare(strict_types=1);

namespace App\Controller;

use App\Service\PythonTaskBus;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Hyperf\Redis\Redis;
use function Hyperf\Support\env;

class WecomCallbackController
{
    private const STREAM_KEY_PREFIX = 'wecom:stream:';

    public function __construct(
        private PythonTaskBus $taskBus,
        private Redis $redis,
    ) {}

    public function callback(RequestInterface $request, ResponseInterface $response)
    {
        $token  = (string) env('WECOM_TOKEN');
        $aesKey = (string) env('WECOM_ENCODING_AES_KEY'); // 43位
        $receiveId = ''; // 内部智能机器人：传空串

        $msgSignature = (string)($request->query('msg_signature', '') ?: $request->query('msgsignature', ''));
        $timestamp    = (string) $request->query('timestamp', '');
        $nonce        = (string) $request->query('nonce', '');

        if ($msgSignature === '' || $timestamp === '' || $nonce === '') {
            return $response->withStatus(400)->raw('missing signature params');
        }

        // GET：验证 URL
        if (strtoupper($request->getMethod()) === 'GET') {
            $echostr = (string) $request->query('echostr', '');
            if (strpos($echostr, '%') !== false) $echostr = rawurldecode($echostr);
            $echostr = str_replace(' ', '+', $echostr);

            $calcSig = $this->sha1Signature([$token, $timestamp, $nonce, $echostr]);
            if (!hash_equals($calcSig, $msgSignature)) {
                return $response->withStatus(403)->raw('invalid msg_signature');
            }

            $plain = $this->decryptWecom($echostr, $aesKey, $receiveId);
            $plain = $this->stripBomAndNewlines($plain);

            return $response->withHeader('Content-Type', 'text/plain; charset=utf-8')->raw($plain);
        }

        // POST：解密回调 body.encrypt
        $rawBody = (string) $request->getBody();
        $body = json_decode($rawBody, true);
        if (!is_array($body) || empty($body['encrypt'])) {
            return $response->withStatus(400)->raw('invalid json body');
        }

        $encrypt = (string)$body['encrypt'];
        if (strpos($encrypt, '%') !== false) $encrypt = rawurldecode($encrypt);
        $encrypt = str_replace(' ', '+', $encrypt);

        $calcSig = $this->sha1Signature([$token, $timestamp, $nonce, $encrypt]);
        if (!hash_equals($calcSig, $msgSignature)) {
            return $response->withStatus(403)->raw('invalid msg_signature');
        }

        $plainJson = $this->decryptWecom($encrypt, $aesKey, $receiveId);
        $event = json_decode($plainJson, true);
        if (!is_array($event)) {
            return $response->withStatus(400)->raw('plain json invalid');
        }

        // 1) 流式刷新回调：带 stream.id / stream_id 的，优先处理
        $streamId = $this->extractStreamId($event);
        if ($streamId !== '' && $this->looksLikeStreamRefresh($event)) {
            $stateRaw = $this->redis->get(self::STREAM_KEY_PREFIX . $streamId);
            if ($stateRaw) {
                $state = json_decode((string)$stateRaw, true) ?: [];
                $replyPlain = [
                    "msgtype" => "stream",
                    "stream" => array_filter([
                        "id" => $streamId,
                        "finish" => (bool)($state["finish"] ?? false),
                        "content" => (string)($state["content"] ?? "处理中…"),
                        // finish=true 才建议带图片
                        "msg_item" => (is_array($state["msg_item"] ?? null) ? $state["msg_item"] : null),
                    ], fn($v) => $v !== null),
                ];
            } else {
                $replyPlain = [
                    "msgtype" => "stream",
                    "stream" => [
                        "id" => $streamId,
                        "finish" => false,
                        "content" => "处理中…",
                    ],
                ];
            }

            return $this->replyEncrypted($response, $replyPlain, $token, $aesKey, $receiveId, $timestamp, $nonce);
        }

        // 2) 用户发送消息回调：首次回复（finish=false），并发任务给 Python
        if ($this->looksLikeUserMessage($event)) {
            $text = $this->extractUserText($event);
            $streamId = 's_' . bin2hex(random_bytes(8));

            // 初始化状态（可选）
            $this->redis->set(self::STREAM_KEY_PREFIX . $streamId, json_encode([
                "finish" => false,
                "content" => "处理中…",
                "updated_at" => time(),
            ], JSON_UNESCAPED_UNICODE));
            $this->redis->expire(self::STREAM_KEY_PREFIX . $streamId, 3600);

            // dispatch 给 Python
            $this->taskBus->dispatch([
                "type" => "task",
                "stream_id" => $streamId,
                "user_text" => $text,
                "event" => $event,
            ]);

            // 首次被动回复：stream，finish=false
            $replyPlain = [
                "msgtype" => "stream",
                "stream" => [
                    "id" => $streamId,
                    "finish" => false,
                    "content" => "处理中…",
                ],
            ];

            return $this->replyEncrypted($response, $replyPlain, $token, $aesKey, $receiveId, $timestamp, $nonce);
        }

        // 其它事件：不回复内容
        return $response->withHeader('Content-Type', 'text/plain; charset=utf-8')->raw('success');
    }

    // ====== 事件判断（先容错，跑通后可按你的明文字段精准化）======
    private function looksLikeUserMessage(array $event): bool
    {
        // 常见：存在 msgtype/text/content 即认为是用户消息
        return isset($event['msgtype']) || isset($event['text']) || isset($event['content']) || isset($event['msg']);
    }

    private function looksLikeStreamRefresh(array $event): bool
    {
        // 常见：刷新事件里会带 stream.id 或 stream_id；也可能 event_type 包含 refresh/stream
        $t = strtolower((string)($event['event_type'] ?? $event['type'] ?? ''));
        if ($t !== '' && (str_contains($t, 'stream') || str_contains($t, 'refresh'))) return true;

        // 兜底：只要带 stream id，就当成刷新回调（企微会反复来拉取）
        return $this->extractStreamId($event) !== '';
    }

    private function extractStreamId(array $event): string
    {
        return (string)($event['stream']['id'] ?? $event['stream_id'] ?? $event['streamid'] ?? '');
    }

    private function extractUserText(array $event): string
    {
        return (string)(
            $event['text']['content']
            ?? $event['content']
            ?? $event['msg']['text']
            ?? ''
        );
    }

    // ====== 加密回复（返回 {encrypt,msgsignature,timestamp,nonce}）======
    private function replyEncrypted(
        ResponseInterface $response,
        array $replyPlain,
        string $token,
        string $aesKey43,
        string $receiveId,
        string $timestamp,
        string $nonce
    ) {
        $replyPlainJson = json_encode($replyPlain, JSON_UNESCAPED_UNICODE);
        if ($replyPlainJson === false) {
            return $response->withStatus(500)->raw('reply json_encode failed');
        }

        $ts = ctype_digit($timestamp) ? (int)$timestamp : time();
        $nn = $nonce !== '' ? $nonce : bin2hex(random_bytes(6));

        $encryptOut = $this->encryptWecom($replyPlainJson, $aesKey43, $receiveId);
        $msgSigOut  = $this->sha1Signature([$token, (string)$ts, $nn, $encryptOut]);

        return $response
            ->withHeader('Content-Type', 'application/json; charset=utf-8')
            ->raw(json_encode([
                "encrypt" => $encryptOut,
                "msgsignature" => $msgSigOut,
                "timestamp" => $ts,
                "nonce" => $nn,
            ], JSON_UNESCAPED_UNICODE));
    }

    // ===== 企业微信签名：SHA1(sort(...)) =====
    private function sha1Signature(array $parts): string
    {
        sort($parts, SORT_STRING);
        return sha1(implode('', $parts));
    }

    // ===== 解密/加密（AES-256-CBC + PKCS7，块大小32）=====
    private function decryptWecom(string $cipherBase64, string $encodingAesKey43, string $receiveIdExpected = ''): string
    {
        $aesKey = base64_decode($encodingAesKey43 . '=', true);
        if ($aesKey === false || strlen($aesKey) !== 32) throw new \RuntimeException('bad aes key');

        $cipher = base64_decode($cipherBase64, true);
        if ($cipher === false) throw new \RuntimeException('bad base64');

        $iv = substr($aesKey, 0, 16);
        $plainPadded = openssl_decrypt($cipher, 'AES-256-CBC', $aesKey, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $iv);
        if ($plainPadded === false || $plainPadded === '') throw new \RuntimeException('openssl decrypt failed');

        $plain = $this->pkcs7UnpadFast($plainPadded);

        if (strlen($plain) < 20) throw new \RuntimeException('plain too short');
        $msgLen = unpack('N', substr($plain, 16, 4))[1] ?? 0;
        if ($msgLen < 0 || $msgLen > 204800) throw new \RuntimeException('bad msg len');

        $msg = substr($plain, 20, $msgLen);
        $receiveId = substr($plain, 20 + $msgLen);

        if ($receiveIdExpected !== '' && $receiveId !== $receiveIdExpected) {
            throw new \RuntimeException('receiveId mismatch');
        }
        return $msg;
    }

    private function encryptWecom(string $plainMsg, string $encodingAesKey43, string $receiveId = ''): string
    {
        $aesKey = base64_decode($encodingAesKey43 . '=', true);
        if ($aesKey === false || strlen($aesKey) !== 32) throw new \RuntimeException('bad aes key');

        $random = random_bytes(16);
        $msgLen = pack('N', strlen($plainMsg));
        $raw = $random . $msgLen . $plainMsg . $receiveId;
        $padded = $this->pkcs7Pad($raw);

        $iv = substr($aesKey, 0, 16);
        $cipher = openssl_encrypt($padded, 'AES-256-CBC', $aesKey, OPENSSL_RAW_DATA | OPENSSL_ZERO_PADDING, $iv);
        if ($cipher === false) throw new \RuntimeException('openssl encrypt failed');

        return base64_encode($cipher);
    }

    private function pkcs7UnpadFast(string $text): string
    {
        $len = strlen($text);
        if ($len === 0) throw new \RuntimeException('empty padded');
        $pad = ord($text[$len - 1]);
        if ($pad < 1 || $pad > 32) throw new \RuntimeException('bad padding');
        return substr($text, 0, $len - $pad);
    }

    private function pkcs7Pad(string $text): string
    {
        $blockSize = 32;
        $amountToPad = $blockSize - (strlen($text) % $blockSize);
        if ($amountToPad === 0) $amountToPad = 32;
        return $text . str_repeat(chr($amountToPad), $amountToPad);
    }

    private function stripBomAndNewlines(string $s): string
    {
        if (strncmp($s, "\xEF\xBB\xBF", 3) === 0) $s = substr($s, 3);
        return str_replace(["\r", "\n"], '', $s);
    }
}
