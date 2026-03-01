<?php

declare(strict_types=1);

namespace App\Controller;

use Hyperf\HttpServer\Contract\ResponseInterface;

class IndexController extends AbstractController
{
    public function index(ResponseInterface $response)
    {
        // 读取 public 目录下的 chat.html 文件
        $html = file_get_contents(BASE_PATH . '/public/chat.html');

        // 返回 HTML 内容并设置正确的 Content-Type 头部
        return $response->raw($html)->withHeader('Content-Type', 'text/html');
    }
}
