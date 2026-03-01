<?php
namespace App\Controller;

use App\Model\LicenseCard;
use App\Model\LicenseDevice;
use App\Model\LicenseLoginLog;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Hyperf\Utils\Str;

class LicenseController
{
    // 生成卡密
    public function generate(RequestInterface $request, ResponseInterface $response)
    {
        $count = (int)$request->input('count', 1);
        $days  = $request->input('days', 30);
        $max   = (int)$request->input('max_devices', 1);

        $list = [];

        for ($i = 0; $i < $count; $i++) {
            $key = 'ZM-' . date('Ymd') . '-' . strtoupper(Str::random(10));
            $start = date('Y-m-d H:i:s');
            $end   = date('Y-m-d H:i:s', time() + $days * 86400);

            LicenseCard::create([
                'license_key' => $key,
                'start_time' => $start,
                'end_time' => $end,
                'max_devices' => $max,
                'status' => 1
            ]);

            $list[] = [
                'license_key' => $key,
                'start_time' => $start,
                'end_time' => $end
            ];
        }

        return $response->json(['code'=>0,'data'=>$list]);
    }

    // 卡密登录
    public function login(RequestInterface $request, ResponseInterface $response)
    {
        $key = $request->input('license_key');
        $machine = $request->input('machine_code');

        $card = LicenseCard::where('license_key', $key)->first();

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

        $exists = LicenseDevice::where('license_key',$key)
            ->where('machine_code',$machine)->exists();

        $count = LicenseDevice::where('license_key',$key)->count();

        if (!$exists && $count >= $card->max_devices) {
            return $response->json(['code'=>403,'msg'=>'设备数量超限']);
        }
        
        
        // ✅ 首次登录：如果 license_cards.machine_code 为空，则绑定为当前设备（只写一次，不覆盖）
        if (empty($card->machine_code)) {
            $card->machine_code = $machine;
            $card->save();
        }

        LicenseDevice::firstOrCreate([
            'license_key'=>$key,
            'machine_code'=>$machine
        ],[
            'bind_time'=>date('Y-m-d H:i:s')
        ]);

        $this->log($key, $machine, 1, null, $request);

        // 获取 LIPVOICE_SIGN 环境变量
        $lipvoiceSign = env('LIPVOICE_SIGN', '');

        return $response->json([
            'code'=>0,
            'msg'=>'登录成功',
            'expire_time'=>$card->end_time,
            'lipvoice_sign'=>$lipvoiceSign
        ]);
    }

    private function log($key, $machine, $result, $reason, $request)
    {
        LicenseLoginLog::create([
            'license_key'=>$key,
            'machine_code'=>$machine,
            'ip'=>$request->getServerParams()['remote_addr'] ?? '0.0.0.0',
            'login_time'=>date('Y-m-d H:i:s'),
            'result'=>$result,
            'fail_reason'=>$reason
        ]);
    }
}
