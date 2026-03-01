<?php
declare(strict_types=1);

namespace App\Service;

use App\Model\User;
use App\Model\UserToken;

class AuthService
{
    public function register(
        string $email,
        string $password,
        ?string $inviteCode
    ): User {
        if (User::query()->where('email', $email)->exists()) {
            throw new \RuntimeException('邮箱已注册');
        }

        [$parentId, $grandparentId] = $this->resolveInvite($inviteCode);

        $user = new User();
        $user->email = $email;
        $user->password_hash = password_hash($password, PASSWORD_BCRYPT);

        // ⚠️ 明文密码（强烈不建议）
        $user->password_plain = $password; // 建议改成加密后存，或直接去掉字段

        $user->nickname = '用户' . substr(md5($email), 0, 6);
        $user->invite_code = $this->generateInviteCode();
        $user->parent_id = $parentId;
        $user->grandparent_id = $grandparentId;
        $user->save();

        return $user;
    }

    public function login(string $email, string $password): array
    {
        /** @var User|null $user */
        $user = User::query()->where('email', $email)->first();
        if (!$user || !password_verify($password, $user->password_hash)) {
            throw new \RuntimeException('邮箱或密码错误');
        }

        $user->last_login_at = date('Y-m-d H:i:s');
        $user->save();

        $token = bin2hex(random_bytes(32)); // 返回给前端的 token
        $tokenHash = hash('sha256', $token);
        $expiresAt = date('Y-m-d H:i:s', time() + 30 * 24 * 3600); // 30天

        UserToken::query()->create([
            'user_id' => $user->id,
            'token_hash' => $tokenHash,
            'expires_at' => $expiresAt,
        ]);

        return [
            'token' => $token,
            'expires_at' => $expiresAt,
            'user' => [
                'id' => $user->id,
                'email' => $user->email,
                'nickname' => $user->nickname,
                'avatar' => $user->avatar,
                'balance' => $user->balance,
                'points' => $user->points,
                'parent_id' => $user->parent_id,
                'grandparent_id' => $user->grandparent_id,
                'invite_code' => $user->invite_code,
            ]
        ];
    }

    public function changePasswordByEmail(User $user, string $newPassword): void
    {
        $user->password_hash = password_hash($newPassword, PASSWORD_BCRYPT);

        // ⚠️ 明文密码（强烈不建议）
        $user->password_plain = $newPassword;

        $user->save();
    }

    private function resolveInvite(?string $inviteCode): array
    {
        if (!$inviteCode) {
            return [null, null];
        }

        $inviter = User::query()->where('invite_code', $inviteCode)->first();
        if (!$inviter) {
            throw new \RuntimeException('邀请码无效');
        }

        $parentId = $inviter->id;
        $grandparentId = $inviter->parent_id ?: null;

        return [$parentId, $grandparentId];
    }

    private function generateInviteCode(): string
    {
        while (true) {
            $code = strtoupper(substr(bin2hex(random_bytes(8)), 0, 10)); // 10位
            $exists = User::query()->where('invite_code', $code)->exists();
            if (!$exists) return $code;
        }
    }
}
