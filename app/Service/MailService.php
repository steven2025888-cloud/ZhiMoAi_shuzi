<?php
declare(strict_types=1);

namespace App\Service;

use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;
use function Hyperf\Support\env;

class MailService
{
    
    public function send163(string $to, string $subject, string $body)
    {
        $mail = new PHPMailer(true);

        try {
            // SMTP 配置
            $mail->isSMTP();
            $mail->Host = env('MAIL_HOST');
            $mail->SMTPAuth = true;
            $mail->Username = env('MAIL_USERNAME');
            $mail->Password = env('MAIL_PASSWORD'); // ⚠️不是登录密码
            $mail->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;
            $mail->Port = env('MAIL_PORT');
            $mail->CharSet = 'UTF-8';

            // 发件人
            $mail->setFrom(env('MAIL_FROM_ADDRESS'), env('MAIL_FROM_NAME'));
            $mail->addAddress($to);

            // 内容
            $mail->isHTML(false);
            $mail->Subject = $subject;
            $mail->Body = $body;

            $mail->send();
        } catch (Exception $e) {
            throw new \RuntimeException('邮件发送失败：' . $mail->ErrorInfo);
        }
    }
    
    
}
