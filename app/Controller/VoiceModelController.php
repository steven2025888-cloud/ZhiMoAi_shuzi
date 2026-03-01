<?php

namespace App\Controller;

use App\Middleware\LicenseCardAuthMiddleware;
use App\Service\LipVoiceClient;
use App\Service\VoiceService;
use App\Support\ApiResponse;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Annotation\Middleware;
use Hyperf\HttpServer\Contract\RequestInterface;
use App\Model\VoiceModel;

#[Middleware(LicenseCardAuthMiddleware::class)]
class VoiceModelController
{
    #[Inject]
    protected RequestInterface $request;

    #[Inject]
    protected LipVoiceClient $lip;

    #[Inject]
    protected VoiceService $voice;

    public function list()
    {
        try {
            $licenseKey = (string) $this->request->getAttribute('license_key');

            $rows = VoiceModel::where('license_key', $licenseKey)
                ->orderByDesc('is_default')
                ->orderByDesc('id')
                ->get()
                ->toArray();

            return ApiResponse::ok($rows);
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    public function upload()
    {
        try {
            $licenseKey = (string) $this->request->getAttribute('license_key');
            $card = $this->request->getAttribute('license_card');

            if (!$card) {
                throw new \RuntimeException('未获取到卡密信息，请检查中间件是否生效');
            }

            $file = $this->request->file('file');
            if (!$file) throw new \RuntimeException('缺少 file');

            $name = (string) $this->request->input('name', '默认模型');
            $describe = (string) $this->request->input('describe', '');

            $this->voice->ensureModelQuota($licenseKey, (int)$card->model_limit);

            $tmpPath = $file->getPathname();
            $clientName = method_exists($file, 'getClientFilename') ? $file->getClientFilename() : 'model.wav';
            $clientMime = method_exists($file, 'getClientMediaType') ? $file->getClientMediaType() : 'audio/wav';

            if (!preg_match('/\.wav$/i', $clientName)) {
                $clientName = $name . '.wav';
            }

            $resp = $this->lip->uploadReference($tmpPath, $clientName, $clientMime, $name, $describe);

            if (!isset($resp['code']) || (int)$resp['code'] !== 0) {
                throw new \RuntimeException($resp['msg'] ?? '第三方上传失败');
            }

            $audioId = $resp['data']['audioId'] ?? $resp['data']['audio_id'] ?? null;
            if (!$audioId) throw new \RuntimeException('第三方未返回 audio_id');

            $model = VoiceModel::create([
                'license_key' => $licenseKey,
                'name'        => $name,
                'audio_id'    => $audioId,
                'describe'    => $describe,
                'is_default'  => 0,
            ]);

            return ApiResponse::ok([
                'id'       => $model->id,
                'audio_id' => $audioId
            ], '上传成功');
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    public function setDefault()
    {
        try {
            $licenseKey = (string) $this->request->getAttribute('license_key');
            $modelId = (int) $this->request->input('model_id');
            if ($modelId <= 0) throw new \RuntimeException('model_id 不合法');

            $this->voice->mustOwnModel($licenseKey, $modelId);
            $this->voice->setDefault($licenseKey, $modelId);

            return ApiResponse::ok(true, '已设为默认');
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }

    public function delete()
    {
        try {
            $licenseKey = (string) $this->request->getAttribute('license_key');
            $modelId = (int) $this->request->input('model_id');
            if ($modelId <= 0) throw new \RuntimeException('model_id 不合法');

            $model = VoiceModel::where('license_key', $licenseKey)
                ->where('id', $modelId)
                ->first();

            if (!$model) {
                throw new \RuntimeException('模型不存在或无权限');
            }

            $audioId = $model->audio_id;

            // 1. 删除第三方
            $resp = $this->lip->deleteReference($audioId);
            if (!isset($resp['code']) || (int)$resp['code'] !== 0) {
                throw new \RuntimeException('第三方音色删除失败：' . ($resp['msg'] ?? json_encode($resp)));
            }

            // 2. 删除本地模型
            $model->delete();

            return ApiResponse::ok(true, '模型及云端声纹已删除');
        } catch (\Throwable $e) {
            return ApiResponse::fail($e->getMessage());
        }
    }
}
