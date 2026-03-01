<?php
namespace App\Controller;

use App\Model\DspCard;
use App\Model\DspDevice;
use App\Model\DspLoginLog;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Hyperf\Utils\Str;
use function Hyperf\Support\env;

class DspController
{
    // 生成卡密
    public function generate(RequestInterface $request, ResponseInterface $response)
    {
        $count = (int)$request->input('count', 1);
        $days  = $request->input('days', 30);
        $max   = (int)$request->input('max_devices', 2); // 默认2：1PC+1手机
        $onlineEnabled = (int)$request->input('online_enabled', 0); // 0=仅本地, 1=本地+在线

        $list = [];

        for ($i = 0; $i < $count; $i++) {
            $key = 'ZM-' . date('Ymd') . '-' . strtoupper(Str::random(10));
            $start = date('Y-m-d H:i:s');
            $end   = date('Y-m-d H:i:s', time() + $days * 86400);

            DspCard::create([
                'license_key' => $key,
                'start_time' => $start,
                'end_time' => $end,
                'max_devices' => $max,
                'online_enabled' => $onlineEnabled,
                'status' => 1
            ]);

            $list[] = [
                'license_key' => $key,
                'start_time' => $start,
                'end_time' => $end,
                'online_enabled' => $onlineEnabled,
            ];
        }

        return $response->json(['code'=>0,'data'=>$list]);
    }

    // 卡密登录
    // device_type: 'pc' 或 'mobile'，每种类型最多绑定 1 台设备
    public function login(RequestInterface $request, ResponseInterface $response)
    {
        $key = $request->input('license_key');
        $machine = $request->input('machine_code');
        $deviceType = $request->input('device_type', 'pc'); // pc | mobile

        // 校验 device_type
        if (!in_array($deviceType, ['pc', 'mobile'])) {
            return $response->json(['code'=>400,'msg'=>'device_type 必须为 pc 或 mobile']);
        }

        $card = DspCard::where('license_key', $key)->first();

        if (!$card) {
            $this->log($key, $machine, 0, '卡密不存在', $request);
            return $response->json(['code'=>403,'msg'=>'卡密不存在']);
        }

        if ($card->status == 3) {
            return $response->json(['code'=>403,'msg'=>'卡密已封禁']);
        }

        if (strtotime($card->start_time) > time()) {
            return $response->json(['code'=>403,'msg'=>'卡密未到生效时间']);
        }

        if ($card->end_time && strtotime($card->end_time) < time()) {
            $card->status = 2;
            $card->save();
            return $response->json(['code'=>403,'msg'=>'卡密已过期']);
        }

        // 手机端登录需要卡密支持在线版
        if ($deviceType === 'mobile' && !(int)$card->online_enabled) {
            $this->log($key, $machine, 0, '卡密不支持手机端（在线版）', $request);
            return $response->json(['code'=>403,'msg'=>'当前卡密不支持手机端，请升级为在线版卡密']);
        }

        // 检查该设备是否已绑定
        $existsExact = DspDevice::where('license_key', $key)
            ->where('machine_code', $machine)
            ->where('device_type', $deviceType)
            ->exists();

        if (!$existsExact) {
            // 检查该类型是否已绑定了其他设备
            $boundDevice = DspDevice::where('license_key', $key)
                ->where('device_type', $deviceType)
                ->first();

            if ($boundDevice) {
                // 该类型已绑定了另一台设备
                $typeLabel = $deviceType === 'pc' ? '电脑' : '手机';
                $this->log($key, $machine, 0, "{$typeLabel}端已绑定其他设备", $request);
                return $response->json([
                    'code' => 403,
                    'msg'  => "该卡密的{$typeLabel}端已绑定其他设备（{$boundDevice->machine_code}）"
                ]);
            }
        }

        // 首次登录：绑定 machine_code 到 card（向后兼容）
        if (empty($card->machine_code)) {
            $card->machine_code = $machine;
            $card->save();
        }

        // 创建或更新设备记录
        DspDevice::updateOrCreate(
            [
                'license_key' => $key,
                'device_type' => $deviceType,
                'machine_code' => $machine,
            ],
            [
                'bind_time' => date('Y-m-d H:i:s'),
                'last_active_time' => date('Y-m-d H:i:s'),
            ]
        );

        $this->log($key, $machine, 1, null, $request);

        return $response->json([
            'code' => 0,
            'msg'  => '登录成功',
            'expire_time'    => $card->end_time,
            'online_enabled' => (int)$card->online_enabled,
            'device_type'    => $deviceType,
            // 直接返回 GPU 服务器地址
            'synthesis_server_url' => 'http://117.50.91.129:8383',
            'synthesis_api_secret' => '',
        ]);
    }

    private function log($key, $machine, $result, $reason, $request)
    {
        DspLoginLog::create([
            'license_key'=>$key,
            'machine_code'=>$machine,
            'ip'=>$request->getServerParams()['remote_addr'] ?? '0.0.0.0',
            'login_time'=>date('Y-m-d H:i:s'),
            'result'=>$result,
            'fail_reason'=>$reason
        ]);
    }
}
