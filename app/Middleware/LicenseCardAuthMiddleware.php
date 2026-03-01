<?php

namespace App\Middleware;

use App\Service\LicenseCardService;
use App\Support\ApiResponse;
use Hyperf\Di\Annotation\Inject;
use Hyperf\HttpServer\Contract\RequestInterface;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Psr\Http\Message\ResponseInterface as Psr7Response;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface;

class LicenseCardAuthMiddleware implements MiddlewareInterface
{
    #[Inject]
    protected LicenseCardService $licenseCardService;

    public function process(\Psr\Http\Message\ServerRequestInterface $request, RequestHandlerInterface $handler): Psr7Response
    {
        $container = \Hyperf\Context\ApplicationContext::getContainer();
        $req = $container->get(RequestInterface::class);
        $resp = $container->get(ResponseInterface::class);
         $path = $request->getUri()->getPath();
         
        try {
            
             // 播放接口放行（ffplay 不能带 Authorization 头）
            if ($path === '/api/voice/tts/play'||$path === '/api/voice/tts/download') {
                return $handler->handle($request);
            }
            
            $auth = $req->header('authorization', '');
            if (!$auth || stripos($auth, 'bearer ') !== 0) {
                return $resp->json(ApiResponse::fail('缺少 Authorization Bearer'));
            }

            $licenseKey = trim(substr($auth, 7));
            
            // error_log("License middleware OK: " . $licenseKey);


            $machineCode = $req->header('x-machine-code', '');

            $card = $this->licenseCardService->mustValid($licenseKey);
            $this->licenseCardService->ensureMachineBound($card, $licenseKey, $machineCode);

            // 关键：注入 attribute
            $request = $request->withAttribute('license_key', $licenseKey);
            $request = $request->withAttribute('license_card', $card);
            $request = $request->withAttribute('machine_code', $machineCode);

            return $handler->handle($request);

        } catch (\Throwable $e) {
            return $resp->json(ApiResponse::fail($e->getMessage()));
        }
    }
}
