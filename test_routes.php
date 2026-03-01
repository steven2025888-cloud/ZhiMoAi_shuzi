<?php
/**
 * 测试路由配置
 * 运行: php test_routes.php
 */

require __DIR__ . '/vendor/autoload.php';

use Hyperf\HttpServer\Router\Router;

echo "=== 测试路由配置 ===\n\n";

// 模拟路由配置
Router::addGroup('/api/dsp/voice', function () {
    Router::addRoute(['GET', 'POST'], '/tts/result', function() {
        return 'OK';
    });
});

// 获取所有路由
$routes = Router::getData();

echo "已注册的路由:\n";
print_r($routes);

echo "\n=== 测试完成 ===\n";
