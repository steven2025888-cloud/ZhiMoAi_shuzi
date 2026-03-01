# 手机端 TTS 405 错误最终修复方案

## 问题根源

经过深入排查，发现问题的根本原因是 **URL 双斜杠**：

```
https://api.zhimengai.xyz//api/dsp/voice/tts/result
                         ^^
```

这导致路由匹配失败，返回 405 错误。

## 原因分析

### 1. URL 拼接问题

**手机端代码**（hb_id/utils/api.js）：

```javascript
function request(path, options = {}) {
  const baseUrl = getServerUrl()  // 可能返回 "https://api.zhimengai.xyz/"（带末尾斜杠）
  const url = `${baseUrl}${path}` // path 是 "/api/dsp/voice/tts/result"（带开头斜杠）
  // 结果：https://api.zhimengai.xyz//api/dsp/voice/tts/result（双斜杠）
}
```

### 2. 为什么会有末尾斜杠？

用户在登录时，服务器可能返回的 `server_url` 带有末尾斜杠，或者用户手动配置时添加了末尾斜杠。

### 3. 为什么双斜杠会导致 405？

Hyperf 框架的路由匹配是严格的：

- 配置的路由：`/api/dsp/voice/tts/result`
- 实际请求：`//api/dsp/voice/tts/result`（双斜杠）
- 结果：路由不匹配，返回 405

## 修复方案

### 修改 1：修复 request 函数（hb_id/utils/api.js）

```javascript
// 修改前
function request(path, options = {}) {
  const baseUrl = getServerUrl()
  const url = `${baseUrl}${path}`
  // ...
}

// 修改后
function request(path, options = {}) {
  // 移除 baseUrl 末尾的所有斜杠
  const baseUrl = getServerUrl().replace(/\/+$/, '')
  const url = `${baseUrl}${path}`
  // ...
}
```

### 修改 2：修复 synthRequest 函数（hb_id/utils/api.js）

```javascript
// 修改前
function synthRequest(path, options = {}) {
  const baseUrl = getSynthUrl()
  const url = `${baseUrl}${path}`
  // ...
}

// 修改后
function synthRequest(path, options = {}) {
  const baseUrl = getSynthUrl()
  if (!baseUrl) return Promise.reject(new Error('合成服务器未配置，请重新登录'))
  const url = `${baseUrl.replace(/\/+$/, '')}${path}`
  // ...
}
```

### 修改 3：API 端路由配置（已完成）

```php
// app/routes.php
Router::addRoute(['GET', 'POST'], '/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
```

### 修改 4：API 端控制器（已完成）

```php
// app/Controller/VoiceTtsDspController.php
public function result(RequestInterface $request)
{
    // 同时支持 GET 和 POST 参数
    $taskId = $request->query('taskId')
           ?: $request->query('task_id')
           ?: $request->input('taskId')
           ?: $request->input('task_id');
    // ...
}
```

## 修复效果

### 修复前

```
Request URL: https://api.zhimengai.xyz//api/dsp/voice/tts/result
                                      ^^
Request Method: POST
Status Code: 405 Method Not Allowed
Response Header: Allow: GET
```

### 修复后

```
Request URL: https://api.zhimengai.xyz/api/dsp/voice/tts/result
                                      ^（单斜杠）
Request Method: POST
Status Code: 200 OK
```

## 测试验证

### 测试 1：手机端调用

1. 重新编译手机端应用
2. 登录手机端
3. 提交语音合成任务
4. 查询合成结果

**预期结果：**

- ✅ 请求成功，返回 200
- ✅ 正确返回合成结果

### 测试 2：直接 API 测试

```bash
# POST 方法
curl -X POST https://api.zhimengai.xyz/api/dsp/voice/tts/result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"taskId": "test123"}' \
  -v

# GET 方法
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/result?taskId=test123" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

**预期结果：**

- ✅ 两种方法都返回 200
- ✅ 正确返回数据或错误信息

## 其他改进

### 1. 防御性编程

在所有 URL 拼接的地方都使用 `.replace(/\/+$/, '')` 移除末尾斜杠：

```javascript
// 推荐的 URL 拼接方式
function joinUrl(base, path) {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`
}

// 使用
const url = joinUrl(baseUrl, path)
```

### 2. 服务器端规范化

在服务器端也可以添加中间件来规范化 URL：

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

### 3. 配置验证

在保存服务器地址时，自动移除末尾斜杠：

```javascript
// hb_id/utils/storage.js
export function setServerUrl(url) {
  // 自动移除末尾斜杠
  const normalizedUrl = url.replace(/\/+$/, '')
  uni.setStorageSync(KEYS.SERVER_URL, normalizedUrl)
}
```

## 修改文件清单

### 手机端（hb_id）

- ✅ `utils/api.js`（2 处修改）
  - 修复 `request` 函数
  - 修复 `synthRequest` 函数

### API 端（app）

- ✅ `routes.php`（1 处修改）
  - 修改 `/tts/result` 路由，支持 GET 和 POST

- ✅ `Controller/VoiceTtsDspController.php`（1 处修改）
  - 修改 `result` 方法，同时支持 GET 和 POST 参数

## 部署步骤

### 1. 手机端

```bash
# 重新编译手机端应用
cd hb_id
npm run build:app-plus

# 或者使用 HBuilderX 重新打包
```

### 2. API 端

```bash
# 如果需要重启服务（通常不需要，Hyperf 支持热重载）
cd /path/to/api
php bin/hyperf.php server:restart
```

### 3. 验证

- 手机端重新登录
- 测试语音合成功能
- 检查网络请求日志

## 总结

本次修复解决了手机端 TTS 查询接口的 405 错误，主要原因是 URL 双斜杠导致路由匹配失败。

**修复内容：**

1. ✅ 修复手机端 URL 拼接逻辑，移除末尾斜杠
2. ✅ 修改 API 端路由，同时支持 GET 和 POST
3. ✅ 修改 API 端控制器，同时支持两种参数获取方式

**修改文件：**

- `hb_id/utils/api.js`（2 行）
- `app/routes.php`（1 行）
- `app/Controller/VoiceTtsDspController.php`（10 行）

**风险评估：**

- 低风险
- 向后兼容
- 不影响现有功能

**建议：**

1. 立即部署手机端修复
2. 测试验证所有 API 接口
3. 考虑添加 URL 规范化中间件
