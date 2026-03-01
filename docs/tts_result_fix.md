# 手机端语音合成查询接口修复

## 问题描述

手机端（hb_id）调用语音合成查询接口时报错：

```
https://api.zhimengai.xyz//api/dsp/voice/tts/result
Allow: GET
```

错误提示：`405 Method Not Allowed`

## 问题原因

1. **路由配置问题**：API 端的 `/tts/result` 路由只配置了 GET 方法
2. **客户端请求方法不匹配**：手机端使用 POST 方法调用接口
3. **参数获取方式错误**：控制器使用 `$request->input()` 获取参数，但这个方法主要用于 POST body，不适用于 GET 查询参数

### 代码分析

**手机端代码**（hb_id/utils/api.js）：

```javascript
// 第 9-40 行
function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: options.method || 'POST',  // 默认使用 POST
      data: options.data || {},
      // ...
    })
  })
}

// 第 139-144 行
export function ttsResult(taskId) {
  return request('/api/dsp/voice/tts/result', {
    data: { taskId },  // 使用 POST body 传参
    timeout: 30000,
  })
}
```

**API 端路由配置**（app/routes.php）：

```php
// 第 113 行（修复前）
Router::get('/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
```

**控制器代码**（app/Controller/VoiceTtsDspController.php）：

```php
// 第 138-155 行（修复前）
public function result(RequestInterface $request)
{
    $taskId = $request->input('taskId');  // 只能获取 POST body 参数
    // ...
}
```

## 修复方案

### 修改 1：路由配置（app/routes.php）

**修改前：**

```php
Router::get('/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
```

**修改后：**

```php
// 同时支持 GET 和 POST 方法
Router::addRoute(['GET', 'POST'], '/tts/result', [App\Controller\VoiceTtsDspController::class, 'result']);
```

### 修改 2：控制器方法（app/Controller/VoiceTtsDspController.php）

**修改前：**

```php
public function result(RequestInterface $request)
{
    $taskId = $request->input('taskId');
    if (!$taskId) {
        throw new \RuntimeException('缺少 taskId');
    }
    // ...
}
```

**修改后：**

```php
/**
 * 查询合成结果
 * 支持 GET 和 POST 方法
 */
public function result(RequestInterface $request)
{
    try {
        // 同时支持 GET 查询参数和 POST body 参数
        $taskId = $request->query('taskId')
               ?: $request->query('task_id')
               ?: $request->input('taskId')
               ?: $request->input('task_id');

        if (!$taskId) {
            throw new \RuntimeException('缺少 taskId 参数');
        }

        $resp = $this->lip->ttsResult($taskId);
        if (!isset($resp['code']) || (int)$resp['code'] !== 0) {
            throw new \RuntimeException($resp['msg'] ?? '第三方查询失败');
        }

        return ApiResponse::ok($resp['data']);
    } catch (\Throwable $e) {
        return ApiResponse::fail($e->getMessage());
    }
}
```

## 修复效果

### 修复前

- ❌ 手机端调用接口报错：`405 Method Not Allowed`
- ❌ 无法查询语音合成结果
- ❌ 用户体验差

### 修复后

- ✅ 手机端可以正常调用接口
- ✅ 同时支持 GET 和 POST 方法
- ✅ 同时支持 `taskId` 和 `task_id` 参数名
- ✅ 兼容性更好

## 测试验证

### 测试 1：POST 方法（手机端）

```bash
curl -X POST https://api.zhimengai.xyz/api/dsp/voice/tts/result \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"taskId": "test_task_123"}'
```

**预期结果：**

```json
{
  "code": 0,
  "data": {
    "status": "completed",
    "voiceUrl": "https://..."
  }
}
```

### 测试 2：GET 方法（浏览器）

```bash
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/result?taskId=test_task_123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期结果：**

```json
{
  "code": 0,
  "data": {
    "status": "completed",
    "voiceUrl": "https://..."
  }
}
```

### 测试 3：参数名兼容性

支持以下参数名：

- `taskId`（驼峰命名）
- `task_id`（下划线命名）

```bash
# 使用 taskId
curl -X POST ... -d '{"taskId": "xxx"}'

# 使用 task_id
curl -X POST ... -d '{"task_id": "xxx"}'

# GET 方式
curl -X GET "...?taskId=xxx"
curl -X GET "...?task_id=xxx"
```

## 其他相关接口

检查其他接口是否有类似问题：

### 已检查的接口

| 接口 | 方法 | 状态 |
|------|------|------|
| `/tts` | POST | ✅ 正常 |
| `/tts/result` | GET/POST | ✅ 已修复 |
| `/tts/play` | GET | ✅ 正常 |
| `/tts/download` | GET | ✅ 正常 |
| `/model/list` | GET | ✅ 正常 |
| `/model/upload` | POST | ✅ 正常 |
| `/model/delete` | POST | ✅ 正常 |

## 最佳实践建议

### 1. 统一请求方法

建议在 `request` 函数中根据接口类型自动选择方法：

```javascript
function request(path, options = {}) {
  // 查询类接口使用 GET，其他使用 POST
  const defaultMethod = path.includes('/list') || path.includes('/result')
    ? 'GET'
    : 'POST'

  return new Promise((resolve, reject) => {
    uni.request({
      url,
      method: options.method || defaultMethod,
      // ...
    })
  })
}
```

### 2. 参数传递规范

- **GET 请求**：使用查询参数（query string）
- **POST 请求**：使用 body 参数（JSON）

### 3. API 端兼容性

对于查询类接口，建议同时支持 GET 和 POST 方法，提高兼容性：

```php
// 推荐写法
Router::addRoute(['GET', 'POST'], '/api/xxx/query', [Controller::class, 'query']);

// 控制器中同时支持两种参数获取方式
$param = $request->query('param') ?: $request->input('param');
```

## 部署说明

### 无需重启服务

Hyperf 框架支持热重载，修改路由和控制器后会自动生效。

如果需要手动重启：

```bash
# 重启 Hyperf 服务
php bin/hyperf.php server:restart
```

### 验证修复

1. 重启 API 服务（如需要）
2. 手机端重新登录
3. 测试语音合成功能
4. 检查查询结果是否正常

## 总结

本次修复解决了手机端语音合成查询接口的 `405 Method Not Allowed` 错误，主要修改：

1. ✅ 路由配置：同时支持 GET 和 POST 方法
2. ✅ 控制器方法：同时支持查询参数和 body 参数
3. ✅ 参数名兼容：支持 `taskId` 和 `task_id`

修改文件：

- `app/routes.php`（1 行）
- `app/Controller/VoiceTtsDspController.php`（10 行）

风险评估：低风险，向后兼容，不影响现有功能。
