<?php

namespace App\Service;

use App\Model\VoiceModel;
use Hyperf\DbConnection\Db;

class VoiceService
{
    // 校验模型数量配额
    public function ensureModelQuota(string $licenseKey, int $limit): void
    {
        $count = VoiceModel::where('license_key', $licenseKey)->count();
        if ($count >= $limit) {
            throw new \RuntimeException("模型数量已达上限：{$limit}");
        }
    }

    // 校验模型归属
    public function mustOwnModel(string $licenseKey, int $modelId): VoiceModel
    {
        $model = VoiceModel::where('license_key', $licenseKey)
            ->where('id', $modelId)
            ->first();

        if (!$model) {
            throw new \RuntimeException('模型不存在或无权限');
        }

        return $model;
    }

    // 设为默认模型（事务保证唯一）
    public function setDefault(string $licenseKey, int $modelId): void
    {
        Db::transaction(function () use ($licenseKey, $modelId) {
            VoiceModel::where('license_key', $licenseKey)
                ->update(['is_default' => 0]);

            VoiceModel::where('license_key', $licenseKey)
                ->where('id', $modelId)
                ->update(['is_default' => 1]);
        });
    }
}
