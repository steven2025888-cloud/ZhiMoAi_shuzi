<?php
declare(strict_types=1);

namespace App\Controller;

use App\Service\SpeedTestService;
use Hyperf\HttpServer\Annotation\Controller;
use Hyperf\HttpServer\Annotation\GetMapping;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Contract\ResponseInterface;

#[Controller(prefix: "/speed")]
class SpeedTestController
{
    #[Inject]
    protected SpeedTestService $service;

    #[Inject]
    protected ResponseInterface $response;

    #[GetMapping(path: "test")]
    public function test()
    {
        // 因为你是“域名写死 + 浏览器直接访问”
        // 这里根本不需要 request

        $data = $this->service->run();

        return $this->response->json([
            'code' => 0,
            'server_time' => date('Y-m-d H:i:s'),
            'data' => $data,
        ]);
    }
}
