<?php

declare(strict_types=1);
/**
 * This file is part of Hyperf.
 *
 * @link     https://www.hyperf.io
 * @document https://hyperf.wiki
 * @contact  group@hyperf.io
 * @license  https://github.com/hyperf/hyperf/blob/master/LICENSE
 */
use Hyperf\HttpServer\Router\Router;
use App\Middleware\LicenseCardAuthMiddleware;
use App\Controller\VoiceModelController;
use App\Controller\VoiceTtsController;


Router::addRoute(['GET', 'POST', 'HEAD'], '/', 'App\Controller\IndexController@index');


Router::get('/favicon.ico', function () {
    return '';
});


// Router::addServer('ws', function () {
//     Router::get('/', 'App\Controller\WebSocketController');
// });


use App\Controller\VideoExtractController;

Router::addRoute(['GET', 'POST'], '/api/video/extract-rescontent', [VideoExtractController::class, 'extract']);

use App\Controller\WecomCallbackController;

// 回调接口必须同时支持 GET（URL验证）与 POST（业务回调）

Router::addRoute(['GET', 'POST'], '/wecom/callback', [WecomCallbackController::class, 'callback']);


Router::addServer('ws_live', function () {
    Router::get('/live', \App\WebSocket\LiveHandler::class);
    Router::get('/chat', \App\WebSocket\PythonGateway::class);
    Router::get('/dsp', \App\WebSocket\Dsp::class);
});



Router::addGroup('/api/auth', function () {
    Router::post('/send-code', [\App\Controller\AuthController::class, 'sendCode']);
    Router::post('/register', [\App\Controller\AuthController::class, 'register']);
    Router::post('/login', [\App\Controller\AuthController::class, 'login']);
    Router::post('/change-password', [\App\Controller\AuthController::class, 'changePassword']);
});




Router::addGroup('/api', function () {
    Router::post('/admin/license/generate', [\App\Controller\LicenseController::class, 'generate']);
    Router::post('/license/login', [\App\Controller\LicenseController::class, 'login']);

});





Router::addGroup('/api/voice', function () {

    Router::get('/model/list', [VoiceModelController::class, 'list']);
    Router::post('/model/upload', [VoiceModelController::class, 'upload']);
    Router::post('/model/default', [VoiceModelController::class, 'setDefault']);
    Router::post('/model/delete', [VoiceModelController::class, 'delete']);

    Router::post('/tts', [VoiceTtsController::class, 'create']);
    
    Router::get('/tts/result', [VoiceTtsController::class, 'result']);
    
    Router::get('/tts/play', [VoiceTtsController::class, 'play']);
    

}, ['middleware' => [LicenseCardAuthMiddleware::class]]);




Router::addGroup('/api/dsp', function () {
    Router::post('/login', [\App\Controller\DspController::class, 'login']);
    // 添加授权登录接口
    Router::post('/license/login', [\App\Controller\DspController::class, 'licenseLogin']);
});
Router::addGroup('/api/asset', function () {
    Router::get('/list', [\App\Controller\AssetDspController::class, 'list']);
    Router::post('/delete', [\App\Controller\AssetDspController::class, 'delete']);
}, ['middleware' => [App\Middleware\LicenseCardAuthDspMiddleware::class]]);

Router::addGroup('/api/dsp/asset', function () {
    Router::get('/list', [\App\Controller\AssetDspController::class, 'list']);
    Router::post('/delete', [\App\Controller\AssetDspController::class, 'delete']);
}, ['middleware' => [App\Middleware\LicenseCardAuthDspMiddleware::class]]);

Router::addGroup('/api/dsp/voice', function () {

    Router::get('/model/list', [App\Controller\VoiceModelDspController::class, 'list']);
    Router::post('/model/upload', [App\Controller\VoiceModelDspController::class, 'upload']);
    Router::post('/model/default', [App\Controller\VoiceModelDspController::class, 'setDefault']);
    Router::post('/model/delete', [App\Controller\VoiceModelDspController::class, 'delete']);

    Router::post('/tts', [App\Controller\VoiceTtsDspController::class, 'create']);

    // 修复：同时支持 GET 和 POST 方法
    Router::addRoute(['GET', 'POST'], '/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);

    // 合成记录
    Router::get('/tts/history', [App\Controller\VoiceTtsDspController::class, 'history']);
    Router::get('/tts/history/detail', [App\Controller\VoiceTtsDspController::class, 'historyDetail']);

    Router::get('/tts/play', [App\Controller\VoiceTtsDspController::class, 'play']);

    Router::get('/tts/download', [App\Controller\VoiceTtsDspController::class, 'download']);

}, ['middleware' => [App\Middleware\LicenseCardAuthDspMiddleware::class]]);

Router::addGroup('/api/heygem/task', function () {
    Router::post('/submit', [App\Controller\HeyGemTaskController::class, 'submit']);
    Router::get('/status', [App\Controller\HeyGemTaskController::class, 'status']);
}, ['middleware' => [App\Middleware\LicenseCardAuthDspMiddleware::class]]);


