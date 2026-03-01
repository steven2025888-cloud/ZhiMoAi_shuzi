<?php
declare(strict_types=1);

namespace App\Service;

class SpeedTestService
{
    /**
     * 域名直接写在这里
     */
    protected array $urls = [
        'https://yunwu.ai',
        // 'https://yunwu.zeabur.app',
        // 'https://api.apiplus.org',
        // 'https://api3.wlai.vip',
        // 'https://api.zhongzhuan.chat',
        // 'https://api.bltcy.ai',
        // 'https://api.gptbest.vip',
        // 'https://hk-api.gptbest.vip',

        // 'https://api.openai.com',
    ];

    public function run(): array
    {
        $mh = curl_multi_init();
        $handles = [];

        foreach ($this->urls as $url) {
            $ch = curl_init();
            curl_setopt_array($ch, [
                CURLOPT_URL => $url,
            
                // ✅ 关键：只请求头，不下载页面
                CURLOPT_NOBODY => true,
            
                // ✅ 仍然走 GET（HEAD 也是 GET 派生）
                CURLOPT_CUSTOMREQUEST => 'GET',
            
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_FOLLOWLOCATION => true,
                CURLOPT_MAXREDIRS => 3,
            
                // ⏱ 放宽超时
                CURLOPT_CONNECTTIMEOUT => 10,
                CURLOPT_TIMEOUT => 20,
            
                // 🧠 测速必备
                CURLOPT_USERAGENT => 'Hyperf-Speed-Test/1.0',
            
                // 🔒 SSL（测速阶段建议关）
                CURLOPT_SSL_VERIFYPEER => false,
                CURLOPT_SSL_VERIFYHOST => false,
            ]);


            curl_multi_add_handle($mh, $ch);
            $handles[(int)$ch] = [
                'ch' => $ch,
                'url' => $url,
            ];
        }

        // 并发执行
        $running = null;
        do {
            curl_multi_exec($mh, $running);
            curl_multi_select($mh);
        } while ($running > 0);

        $result = [];

        foreach ($handles as $item) {
            $ch = $item['ch'];
            $info = curl_getinfo($ch);

            $result[] = [
                'url' => $item['url'],
                'http_code' => $info['http_code'] ?? 0,
                'dns_ms' => round(($info['namelookup_time'] ?? 0) * 1000, 2),
                'tcp_ms' => round(
                    max(0, ($info['connect_time'] ?? 0) - ($info['namelookup_time'] ?? 0)) * 1000,
                    2
                ),
                'tls_ms' => round(
                    max(0, ($info['appconnect_time'] ?? 0) - ($info['connect_time'] ?? 0)) * 1000,
                    2
                ),
                'ttfb_ms' => round(($info['starttransfer_time'] ?? 0) * 1000, 2),
                'total_ms' => round(($info['total_time'] ?? 0) * 1000, 2),
            ];

            curl_multi_remove_handle($mh, $ch);
            curl_close($ch);
        }

        curl_multi_close($mh);

        // 按最快排序
        usort($result, fn($a, $b) => $a['total_ms'] <=> $b['total_ms']);

        return $result;
    }
}
