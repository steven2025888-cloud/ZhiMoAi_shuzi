<?php
declare(strict_types=1);

namespace App\Controller;

use App\Model\LicenseCard;
use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\PostMapping;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;

use function Hyperf\Support\env;
#[Controller(prefix: "api")]
class UploadController
{
    #[PostMapping(path: "upload_audio")]
    public function uploadAudio(RequestInterface $request, ResponseInterface $response)
    {
        $key = trim((string)$request->input('license_key', ''));
        if (!$key) return $response->json(['code'=>403,'msg'=>'缺少license_key']);

        // ✅ 卡密校验（你可按 login 那套继续加完整逻辑）
        $card = LicenseCard::where('license_key', $key)->first();
        if (!$card) return $response->json(['code'=>403,'msg'=>'卡密不存在']);
        if ((int)$card->status === 3) return $response->json(['code'=>403,'msg'=>'卡密已封禁']);
        if ($card->start_time && strtotime($card->start_time) > time()) return $response->json(['code'=>403,'msg'=>'卡密未到生效时间']);
        if ($card->end_time && strtotime($card->end_time) < time()) {
            $card->status = 2; $card->save();
            return $response->json(['code'=>403,'msg'=>'卡密已过期']);
        }

        $file = $request->file('file');
        if (!$file || !$file->isValid()) return $response->json(['code'=>400,'msg'=>'未收到有效文件']);

        $ext = strtolower((string)$file->getExtension());
        $allow = ['wav','mp3','m4a','aac','ogg','webm']; // ✅ 你如果只做APP录wav，可删webm
        if (!in_array($ext, $allow, true)) return $response->json(['code'=>400,'msg'=>'不支持的音频格式']);

        if ($file->getSize() > 20 * 1024 * 1024) return $response->json(['code'=>400,'msg'=>'文件过大（>20MB）']);

        $dir = BASE_PATH . '/storage/recordings'; // ✅ 建议放 storage，不要直接暴露 public
        if (!is_dir($dir)) @mkdir($dir, 0777, true);

        $name = 'rec_' . date('Ymd_His') . '_' . substr(md5($key . microtime(true)), 0, 10) . '.' . $ext;
        $path = $dir . '/' . $name;
        $file->moveTo($path);

        // ✅ 生成2分钟有效签名下载URL
        $ts = time();
        $token = $this->sign($name, $ts);

        $base = env('app_url');
        if (!$base) {
            // 从请求拼
            $base = $request->getUri()->getScheme() . '://' . $request->getUri()->getHost();
        }

        $downloadUrl = rtrim($base, '/') . "/api/recording_download?file=" . urlencode($name) . "&ts={$ts}&token={$token}";

        return $response->json([
            'code' => 0,
            'msg'  => 'ok',
            'url'  => $downloadUrl,           // ✅ 直接给 python 用的可下载URL（带签名）
            'file' => $name,
            'expire_time' => $card->end_time,
        ]);
    }

    private function sign(string $file, int $ts): string
    {
        $secret = (string)env('recording.secret', 'change-me');
        $payload = $file . '|' . $ts;
        return hash_hmac('sha256', $payload, $secret);
    }
}
