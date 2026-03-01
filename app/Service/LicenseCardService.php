<?php

namespace App\Service;

use App\Model\LicenseCard;
use App\Model\TtsLog;

class LicenseCardService
{
    /**
     * 校验卡密：状态 + 时间窗
     * status: 1正常 2过期 3禁用
     */
    public function mustValid(string $licenseKey): LicenseCard
    {
        $card = LicenseCard::where('license_key', $licenseKey)->first();

        if (!$card) {
            throw new \RuntimeException('卡密不存在');
        }

        if ((int)$card->status !== 1) {
            throw new \RuntimeException((int)$card->status === 2 ? '卡密已过期' : '卡密已禁用');
        }

        $now = time();

        if ($card->start_time && strtotime($card->start_time) > $now) {
            throw new \RuntimeException('卡密尚未生效');
        }

        if ($card->end_time && strtotime($card->end_time) < $now) {
            throw new \RuntimeException('卡密已过期');
        }

        return $card;
    }

    /**
     * 首次绑定 / 校验 machine_code
     */
    public function ensureMachineBound(LicenseCard $card, string $licenseKey, ?string $machineCode): void
    {
        if (!$machineCode) {
            throw new \RuntimeException('缺少 machine_code（设备指纹）');
        }

        if (empty($card->machine_code)) {
            $card->machine_code = $machineCode;
            $card->save();
            return;
        }

        if ($card->machine_code !== $machineCode) {
            throw new \RuntimeException('卡密已绑定其他设备');
        }
    }

    /**
     * 今日已使用字数
     */
    public function getTodayUsedChars(string $licenseKey): int
    {
        return (int) TtsLog::where('license_key', $licenseKey)
            ->whereBetween('created_at', [
                date('Y-m-d 00:00:00'),
                date('Y-m-d 23:59:59'),
            ])
            ->sum('text_len');
    }

    /**
     * 校验今日剩余额度
     */
    public function ensureDailyQuota(string $licenseKey, int $dailyLimit, int $newLen): void
    {
        $used = $this->getTodayUsedChars($licenseKey);

        if ($used + $newLen > $dailyLimit) {
            throw new \RuntimeException("今日字数额度不足：{$used}/{$dailyLimit}");
        }
    }
}
