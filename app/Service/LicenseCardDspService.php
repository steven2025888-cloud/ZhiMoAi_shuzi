<?php

namespace App\Service;

use App\Model\DspCard;
use App\Model\TtsLog;

class LicenseCardDspService
{
    /**
     * 校验卡密：状态 + 时间窗
     * status: 1正常 2过期 3禁用
     */
    public function mustValid(string $licenseKey): DspCard
    {
        $card = DspCard::where('license_key', $licenseKey)->first();

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
     * 首次绑定 / 校验 machine_code（支持多设备类型）
     */
    public function ensureMachineBound(DspCard $card, string $licenseKey, ?string $machineCode, string $deviceType = 'pc'): void
    {
        if (!$machineCode) {
            throw new \RuntimeException('缺少 machine_code（设备指纹）');
        }

        // 检查 dsp_devices 表中该类型是否已绑定
        $bound = \App\Model\DspDevice::where('license_key', $licenseKey)
            ->where('device_type', $deviceType)
            ->first();

        if ($bound && $bound->machine_code !== $machineCode) {
            $typeLabel = $deviceType === 'pc' ? '电脑' : '手机';
            throw new \RuntimeException("该卡密的{$typeLabel}端已绑定其他设备");
        }

        // 向后兼容：首次绑定写入 card.machine_code
        if (empty($card->machine_code)) {
            $card->machine_code = $machineCode;
            $card->save();
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
