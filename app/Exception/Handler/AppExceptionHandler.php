<?php
declare(strict_types=1);

namespace App\Exception\Handler;

use Hyperf\ExceptionHandler\ExceptionHandler;
use Hyperf\HttpServer\Contract\ResponseInterface;
use Psr\Http\Message\ResponseInterface as PsrResponseInterface;
use Throwable;
use function Hyperf\Support\env;

class AppExceptionHandler extends ExceptionHandler
{
    public function __construct(
        private ResponseInterface $response
    ) {}

    public function handle(Throwable $throwable, PsrResponseInterface $response)
    {
        // 告诉 Hyperf：这个异常我处理了
        $this->stopPropagation();

        // 开发环境：直接把错误返回给前端
        if (env('APP_DEBUG') === true || env('APP_DEBUG') === 'true') {
            return $this->response->json([
                'code' => 500,
                'message' => $throwable->getMessage(),
                'file' => $throwable->getFile(),
                'line' => $throwable->getLine(),
            ]);
        }

        // 生产环境：不返回堆栈
        return $this->response->json([
            'code' => 500,
            'message' => $throwable->getMessage(),
        ]);
    }

    public function isValid(Throwable $throwable): bool
    {
        // 所有异常都交给这个处理器
        return true;
    }
}
