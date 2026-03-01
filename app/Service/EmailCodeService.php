<?php
declare(strict_types=1);

namespace App\Service;

use App\Model\EmailCode;
use Hyperf\Contract\ConfigInterface;
use Hyperf\Redis\Redis;
use Hyperf\Stringable\Str;

class EmailCodeService
{
    public function __construct(
        private Redis $redis,
        private MailService $mailService,
    ) {}

    public function send(string $email, string $purpose, string $ip = null): void
    {
        $cooldownKey = "email_code:cooldown:{$purpose}:{$email}";
        if ($this->redis->exists($cooldownKey)) {
            throw new \RuntimeException('发送太频繁，请稍后再试');
        }

        $code = (string) random_int(100000, 999999);
        $expiresAt = date('Y-m-d H:i:s', time() + 10 * 60); // 10分钟

        // DB 留痕（可选）
        EmailCode::query()->create([
            'email' => $email,
            'purpose' => $purpose,
            'code' => $code,
            'expires_at' => $expiresAt,
            'ip' => $ip,
        ]);

        // 发送邮件
        $subject = $purpose === 'reset' ? '重置密码验证码' : '注册验证码';
        $body = "您的验证码是：{$code}，10分钟内有效。如非本人操作请忽略。";
        $this->mailService->send163($email, $subject, $body);

        // 60 秒冷却
        $this->redis->setex($cooldownKey, 60, '1');

        // Redis 存一份“可用验证码”（用于快速校验）
        $codeKey = "email_code:value:{$purpose}:{$email}";
        $this->redis->setex($codeKey, 10 * 60, $code);
    }

    public function verify(string $email, string $purpose, string $code): bool
    {
        $codeKey = "email_code:value:{$purpose}:{$email}";
        $saved = $this->redis->get($codeKey);
        if (!$saved) return false;
        return hash_equals((string)$saved, (string)$code);
    }

    public function consume(string $email, string $purpose): void
    {
        $codeKey = "email_code:value:{$purpose}:{$email}";
        $this->redis->del($codeKey);
    }
}
