# GPU 自动开关机完整实施指南

## 问题分析

当前架构：
```
PC 端 ──HTTP──> GPU 服务器 (直接连接，离线时报错)
```

目标架构：
```
PC 端 ──HTTP──> API 端 ──WebSocket──> GPU Worker
                  ↓
              GPU Monitor (监听任务，自动开关机)
```

## 核心问题

1. **PC 端直接调用 GPU 服务器**，不经过 API 端
2. **GPU Monitor 收不到任务通知**，无法自动开机
3. **HeyGemTaskController 无法直接发送 WebSocket 消息**

## 完整解决方案

### 步骤 1: 修改 PC 端代码（unified_app.py）

在 `.env` 文件中添加配置：

```env
# API 服务器地址（用于任务提交）
API_SERVER_URL=https://api.zhimengai.xyz

# GPU 服务器地址（用于文件上传和下载）
HEYGEM_SERVER_URL=http://117.50.91.129:8383
```

修改 `run_heygem_online` 函数，在健康检查部分改为调用 API 端：

```python
def run_heygem_online(video_path, audio_path, progress=gr.Progress(), ...):
    import requests as _req

    # 获取配置
    api_url = os.getenv("API_SERVER_URL", "").strip().rstrip("/")
    server_url = os.getenv("HEYGEM_SERVER_URL", "").strip().rstrip("/")
    api_secret = os.getenv("HEYGEM_API_SECRET", "").strip()
    license_key = _get_license_key()  # 获取卡密

    if not api_url:
        raise gr.Error("API_SERVER_URL 未配置")
    if not server_url:
        raise gr.Error("HEYGEM_SERVER_URL 未配置")

    headers = {}
    if api_secret:
        headers["Authorization"] = f"Bearer {api_secret}"

    # ... 计算 hash 等步骤保持不变 ...

    # 1. 上传文件到 GPU 服务器（保持不变）
    # ... 上传逻辑 ...

    # 2. 通过 API 端提交任务
    try:
        resp = _req.post(
            f"{api_url}/api/heygem/task/submit",
            json={
                "audio_hash": audio_hash,
                "audio_ext": audio_ext,
                "video_hash": video_hash,
                "video_ext": video_ext,
                "license_key": license_key,
            },
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") != 0:
            raise gr.Error(f"任务提交失败: {result.get('msg')}")

        data = result.get("data", {})
        task_id = data.get("task_id")
        status = data.get("status")

        if status == "queued":
            # GPU 离线，任务已排队
            progress(0.1, desc="⏳ GPU 服务器未上线，任务已排队...")
            yield "⏳ GPU 服务器未上线，任务已排队\\n\\n服务器启动后将自动执行（约2分钟）\\n\\n请稍后在「历史记录」中查看结果"
            return

        # GPU 在线，继续轮询任务状态
        # ... 轮询逻辑 ...

    except Exception as e:
        raise gr.Error(f"任务提交失败: {e}")
```

### 步骤 2: 修改 HeyGemTaskController.php

问题：HTTP Controller 无法直接发送 WebSocket 消息。

解决方案：使用 Redis 作为消息队列，Dsp.php 定时检查并发送。

修改 `_notifyGpuMonitors` 方法（已完成）：

```php
private function _notifyGpuMonitors(array $data): void
{
    $monitors = $this->redis->sMembers('dsp:gpu_monitors');
    if (empty($monitors)) {
        echo "[HeyGemTask] 没有在线的 GPU Monitor\n";
        return;
    }

    $msg = json_encode($data, JSON_UNESCAPED_UNICODE);

    // 将通知消息存入 Redis
    $notifyKey = 'dsp:gpu_monitor_notify';
    $this->redis->rPush($notifyKey, $msg);
    $this->redis->expire($notifyKey, 60);

    echo "[HeyGemTask] 已通知 GPU Monitor: " . count($monitors) . " 个\n";
}
```

### 步骤 3: 修改 Dsp.php，添加定时检查

在 Dsp.php 的 `onMessage` 方法中添加定时检查逻辑：

```php
// 在 onMessage 方法开始处添加
// 检查是否有待发送的 GPU Monitor 通知
$this->_checkAndSendGpuMonitorNotifications($server);

// 在类的末尾添加新方法
private function _checkAndSendGpuMonitorNotifications($server): void
{
    $notifyKey = 'dsp:gpu_monitor_notify';

    // 批量获取所有待发送的通知
    $messages = [];
    for ($i = 0; $i < 10; $i++) {  // 最多取10条
        $msg = $this->redis->lPop($notifyKey);
        if ($msg === null || $msg === false) {
            break;
        }
        $messages[] = $msg;
    }

    if (empty($messages)) {
        return;
    }

    // 发送给所有 GPU Monitor
    $monitors = $this->redis->sMembers(self::KEY_GPU_MONITORS);
    foreach ($messages as $msg) {
        foreach ($monitors as $fdStr) {
            $fd = (int)$fdStr;
            if ($fd > 0 && $server->isEstablished($fd)) {
                $server->push($fd, $msg);
            } else {
                $this->redis->sRem(self::KEY_GPU_MONITORS, $fdStr);
            }
        }
    }

    echo "[WS] 发送 GPU Monitor 通知: " . count($messages) . " 条\n";
}
```

### 步骤 4: 添加路由

在 `app/routes.php` 中添加路由：

```php
Router::addGroup('/api/heygem/task', function () {
    Router::post('/submit', [HeyGemTaskController::class, 'submit']);
    Router::get('/status', [HeyGemTaskController::class, 'status']);
}, [
    'middleware' => [LicenseMiddleware::class],
]);
```

## 实施步骤

### 1. 修改 Dsp.php

```bash
# 编辑 app/WebSocket/Dsp.php
# 在 onMessage 方法开始处添加检查逻辑
# 在类末尾添加 _checkAndSendGpuMonitorNotifications 方法
```

### 2. 重启 Hyperf 服务

```bash
ps aux | grep hyperf
kill -9 <pid>
php bin/hyperf.php start
```

### 3. 修改 PC 端代码

```bash
# 编辑 unified_app.py
# 修改 run_heygem_online 函数
# 添加 API_SERVER_URL 配置
```

### 4. 更新 .env 配置

```env
API_SERVER_URL=https://api.zhimengai.xyz
HEYGEM_SERVER_URL=http://117.50.91.129:8383
```

### 5. 测试

```bash
# 1. 启动 GPU Manager
python gpu_power_manager.py

# 2. 在 PC 端提交视频合成任务

# 3. 观察日志
# GPU Manager 应该看到:
[WS] 收到完整消息: {"type":"gpu.job.submit",...}
[WS] ✓✓✓ 检测到 GPU 任务: gpu.job.submit ✓✓✓
[Check] GPU=stopped, 有任务=True
[Check] 检测到 GPU 任务，准备启动 GPU
[GPU] 开始启动...
```

## 验证清单

- [ ] Dsp.php 已添加 `_checkAndSendGpuMonitorNotifications` 方法
- [ ] HeyGemTaskController.php 已添加 `_notifyGpuMonitors` 方法
- [ ] Hyperf 服务已重启
- [ ] PC 端代码已修改为调用 API 端
- [ ] .env 配置已更新
- [ ] GPU Manager 能收到任务通知
- [ ] GPU 能自动开机
- [ ] 任务能正常执行

## 故障排查

### 问题: GPU Manager 收不到通知

检查：
1. Hyperf 服务是否重启
2. Redis 中是否有通知消息: `redis-cli LRANGE dsp:gpu_monitor_notify 0 -1`
3. Dsp.php 是否调用了 `_checkAndSendGpuMonitorNotifications`

### 问题: PC 端报错

检查：
1. API_SERVER_URL 是否配置正确
2. 路由是否添加
3. HeyGemTaskController 是否正常工作

### 问题: 任务提交后没有执行

检查：
1. GPU Worker 是否在线
2. Redis 队列中是否有任务: `redis-cli LRANGE dsp:pending_tasks:<key> 0 -1`
3. GPU Worker 是否能处理 heygem_submit 任务
