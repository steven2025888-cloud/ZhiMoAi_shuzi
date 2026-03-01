<?php
declare(strict_types=1);

namespace App\Controller;

use App\Model\User;
use App\Service\AuthService;
use App\Service\EmailCodeService;
use Hyperf\HttpServer\Contract\RequestInterface;

class AuthController
{
    public function __construct(
        private RequestInterface $request,
        private EmailCodeService $emailCodeService,
        private AuthService $authService,
    ) {}

    // POST /api/auth/send-code
    public function sendCode()
    {
        $email = (string) $this->request->input('email', '');
        $purpose = (string) $this->request->input('purpose', 'register'); // register|reset

        $this->assertEmail($email);
        if (!in_array($purpose, ['register', 'reset'], true)) {
            return $this->jsonFail('purpose 不合法');
        }

        $ip = (string) ($this->request->getServerParams()['remote_addr'] ?? '');
        $this->emailCodeService->send($email, $purpose, $ip);

        return $this->jsonOk(['message' => '验证码已发送']);
    }

    // POST /api/auth/register
    public function register()
    {
        $email = (string) $this->request->input('email', '');
        $password = (string) $this->request->input('password', '');
        $code = (string) $this->request->input('code', '');
        $inviteCode = $this->request->input('invite_code'); // 可空

        $this->assertEmail($email);
        $this->assertPassword($password);
        if ($code === '') return $this->jsonFail('请输入验证码');

        if (!$this->emailCodeService->verify($email, 'register', $code)) {
            return $this->jsonFail('验证码错误或已过期');
        }

        $user = $this->authService->register($email, $password, $inviteCode ? (string)$inviteCode : null);
        $this->emailCodeService->consume($email, 'register');

        return $this->jsonOk([
            'id' => $user->id,
            'email' => $user->email,
            'invite_code' => $user->invite_code,
            'parent_id' => $user->parent_id,
            'grandparent_id' => $user->grandparent_id,
        ]);
    }

    // POST /api/auth/login
    public function login()
    {
        $email = (string) $this->request->input('email', '');
        $password = (string) $this->request->input('password', '');

        $this->assertEmail($email);
        $this->assertPassword($password);

        $data = $this->authService->login($email, $password);
        return $this->jsonOk($data);
    }

    // POST /api/auth/change-password （邮箱验证码重置）
    public function changePassword()
    {
        $email = (string) $this->request->input('email', '');
        $code = (string) $this->request->input('code', '');
        $newPassword = (string) $this->request->input('new_password', '');

        $this->assertEmail($email);
        if ($code === '') return $this->jsonFail('请输入验证码');
        $this->assertPassword($newPassword);

        if (!$this->emailCodeService->verify($email, 'reset', $code)) {
            return $this->jsonFail('验证码错误或已过期');
        }

        /** @var User|null $user */
        $user = User::query()->where('email', $email)->first();
        if (!$user) return $this->jsonFail('用户不存在');

        $this->authService->changePasswordByEmail($user, $newPassword);
        $this->emailCodeService->consume($email, 'reset');

        return $this->jsonOk(['message' => '密码已修改']);
    }

    private function assertEmail(string $email): void
    {
        if ($email === '' || !preg_match('/^[^\s@]+@[^\s@]+\.[^\s@]+$/', $email)) {
            throw new \RuntimeException('邮箱格式不正确');
        }
    }

    private function assertPassword(string $pwd): void
    {
        if (strlen($pwd) < 6) {
            throw new \RuntimeException('密码至少6位');
        }
    }

    private function jsonOk(array $data = [])
    {
        return ['code' => 0, 'data' => $data];
    }

    private function jsonFail(string $msg, int $code = 1)
    {
        return ['code' => $code, 'message' => $msg];
    }
}
