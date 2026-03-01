# 手机端 TTS 查询接口 405 错误排查指南

## 问题现象

```
Request URL: https://api.zhimengai.xyz//api/dsp/voice/tts/result
Request Method: POST
Status Code: 405 Method Not Allowed
Response Header: Allow: GET
```

## 已完成的修改

### 1. 路由配置（app/routes.php 第 114 行）

```php
// 已修改为同时支持 GET 和 POST
Router::addRoute(['GET', 'POST'], '/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
```

### 2. 控制器方法（app/Controller/VoiceTtsDspController.php）

```php
// 已修改为同时支持 GET 和 POST 参数
$taskId = $request->query('taskId')
       ?: $request->query('task_id')
       ?: $request->input('taskId')
       ?: $request->input('task_id');
```

## 问题排查步骤

### 步骤 1：检查 URL 中的双斜杠

注意到 URL 中有双斜杠：

```
https://api.zhimengai.xyz//api/dsp/voice/tts/result
                         ^^
```

这可能导致路由匹配失败。检查手机端代码中的 baseUrl 配置：

```javascript
// hb_id/utils/api.js
function request(path, options = {}) {
  const baseUrl = getServerUrl()  // 检查这里是否以 / 结尾
  const url = `${baseUrl}${path}` // 如果 baseUrl 以 / 结尾，path 也以 / 开头，就会出现双斜杠
  // ...
}
```

**修复方法：**

```javascript
function request(path, options = {}) {
  const baseUrl = getServerUrl().replace(/\/$/, '')  // 移除末尾的斜杠
  const url = `${baseUrl}${path}`
  // ...
}
```

### 步骤 2：清理 Hyperf 路由缓存

Hyperf 框架会缓存路由配置，修改后需要清理缓存。

**方法 1：使用脚本（推荐）**

Windows:
```bash
cd D:\ZhiMoAi_shuzi
scripts\restart_api.bat
```

Linux:
```bash
cd /path/to/project
bash scripts/restart_api.sh
```

**方法 2：手动清理**

```bash
# 进入项目目录
cd D:\ZhiMoAi_shuzi

# 清理运行时缓存
rm -rf runtime/container/*
rm -rf runtime/cache/*
rm -rf runtime/proxy/*

# 重启服务
php bin/hyperf.php server:restart
```

**方法 3：使用 Hyperf 命令**

```bash
# 清理所有缓存
php bin/hyperf.php vendor:publish hyperf/config
php bin/hyperf.php config:clear

# 重启服务
php bin/hyperf.php server:restart
```

### 步骤 3：验证路由是否生效

**测试 GET 方法：**

```bash
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/result?taskId=test123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

**测试 POST 方法：**

```bash
curl -X POST https://api.zhimengai.xyz/api/dsp/voice/tts/result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"taskId": "test123"}' \
  -v
```

**预期结果：**

- 状态码：200（如果 taskId 有效）或 400（如果 taskId 无效）
- 不应该返回 405

### 步骤 4：检查服务器日志

查看 Hyperf 日志，确认路由是否正确加载：

```bash
# 查看最新日志
tail -f runtime/logs/hyperf.log

# 搜索路由相关日志
grep -i "route" runtime/logs/hyperf.log | tail -20
```

### 步骤 5：检查 Nginx 配置（如果使用）

如果使用 Nginx 作为反向代理，检查配置：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:9501;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # 确保允许所有 HTTP 方法
    proxy_method $request_method;
}
```

### 步骤 6：检查防火墙和安全组

确保服务器允许 POST 请求：

```bash
# 检查 iptables
sudo iptables -L -n -v | grep 9501

# 检查云服务器安全组
# 登录云服务器控制台，检查安全组规则
```

## 临时解决方案

如果以上方法都不行，可以临时修改手机端代码，使用 GET 方法：

```javascript
// hb_id/utils/api.js
export function ttsResult(taskId) {
  return request('/api/dsp/voice/tts/result', {
    method: 'GET',  // 明确指定使用 GET 方法
    data: { taskId },
    timeout: 30000,
  })
}
```

但这不是最佳方案，因为 GET 请求的参数会暴露在 URL 中。

## 最终解决方案

### 方案 A：修复双斜杠问题（推荐）

修改 `hb_id/utils/api.js`：

```javascript
function request(path, options = {}) {
  const baseUrl = getServerUrl().replace(/\/$/, '')  // 移除末尾的斜杠
  const url = `${baseUrl}${path}`
  // ...
}
```

### 方案 B：修改路由匹配规则

如果双斜杠是预期行为，修改路由配置：

```php
// app/routes.php
Router::addGroup('/api/dsp/voice', function () {
    // 同时匹配单斜杠和双斜杠
    Router::addRoute(['GET', 'POST'], '/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
    Router::addRoute(['GET', 'POST'], '//tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
});
```

### 方案 C：使用中间件统一处理

创建一个中间件来规范化 URL：

```php
// app/Middleware/NormalizeUrlMiddleware.php
class NormalizeUrlMiddleware implements MiddlewareInterface
{
    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        $uri = $request->getUri();
        $path = $uri->getPath();

        // 移除多余的斜杠
        $normalizedPath = preg_replace('#/+#', '/', $path);

        if ($path !== $normalizedPath) {
            $uri = $uri->withPath($normalizedPath);
            $request = $request->withUri($uri);
        }

        return $handler->handle($request);
    }
}
```

## 验证清单

- [ ] 检查 URL 是否有双斜杠
- [ ] 清理 Hyperf 缓存
- [ ] 重启 Hyperf 服务
- [ ] 测试 GET 方法
- [ ] 测试 POST 方法
- [ ] 检查服务器日志
- [ ] 检查 Nginx 配置
- [ ] 检查防火墙规则

## 常见错误

### 错误 1：缓存未清理

**症状：** 修改代码后仍然报 405

**解决：** 清理 `runtime/` 目录下的所有缓存

### 错误 2：服务未重启

**症状：** 清理缓存后仍然报 405

**解决：** 重启 Hyperf 服务

### 错误 3：路由冲突

**症状：** 有多个相同路径的路由

**解决：** 检查 `app/routes.php`，确保没有重复定义

### 错误 4：中间件拦截

**症状：** 请求被中间件拦截，返回 405

**解决：** 检查 `LicenseCardAuthDspMiddleware` 是否正确处理 POST 请求

## 联系支持

如果以上方法都无法解决问题，请提供以下信息：

1. 服务器日志（`runtime/logs/hyperf.log`）
2. Nginx 日志（如果使用）
3. 完整的 curl 测试结果（包括 `-v` 参数的输出）
4. 手机端的完整请求日志

## 总结

最可能的原因：

1. **双斜杠问题**：URL 中的 `//` 导致路由匹配失败
2. **缓存问题**：Hyperf 路由缓存未更新
3. **服务未重启**：修改后服务未重启

建议按以下顺序排查：

1. 修复双斜杠问题
2. 清理缓存并重启服务
3. 测试验证
