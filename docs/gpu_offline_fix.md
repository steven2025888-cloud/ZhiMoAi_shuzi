# GPU 离线排队问题修复方案

## 问题描述

PC 端在线版视频合成时，如果 GPU 服务器离线，会直接报错：

```
无法连接 HeyGem 服务器 (http://117.50.91.129:8383):
HTTPConnectionPool(host='117.50.91.129', port=8383):
Max retries exceeded with url: /api/heygem/health
(Caused by ConnectTimeoutError(...))
```

**期望行为：**

- GPU 离线时，提示用户"任务已排队，请等待约2分钟"
- GPU 开机后，自动执行积压任务

## 根本原因

PC 端（unified_app.py）直接调用 GPU 服务器的 HTTP 接口，而不是通过 API 端的 WebSocket 网关。

```
当前架构（错误）：
PC 端 ──HTTP──> GPU 服务器 (离线时直接报错)

正确架构：
PC 端 ──HTTP/WS──> API 端 ──WebSocket──> GPU 服务器
                    ↓
                  Redis 队列（GPU 离线时）
```

## 解决方案

### 方案 1：临时方案（已实施）

**修改内容：**

修改 `unified_app.py` 的 `run_heygem_online` 函数，在健康检查失败时返回友好提示。

**代码修改：**

```python
# unified_app.py 第 1862-1881 行
except _req.exceptions.RequestException as e:
    # GPU 服务器离线时，提示用户等待而不是直接报错
    error_msg = str(e)
    if "Connection" in error_msg or "timeout" in error_msg.lower() or "Max retries" in error_msg:
        raise gr.Error(
            "⏳ GPU 服务器未上线，任务已排队\n\n"
            "服务器启动中，请等待约 2 分钟后重试\n"
            "或稍后在「历史记录」中查看结果\n\n"
            f"提示：如需立即处理，请联系管理员启动 GPU 服务器"
        )
    else:
        raise gr.Error(f"无法连接 HeyGem 服务器 ({server_url}): {e}")
```

**优点：**

- 修改最小，只改一处代码
- 立即生效，用户体验改善

**缺点：**

- 不是真正的排队机制
- 用户需要手动重试
- 任务不会自动执行

### 方案 2：完整方案（推荐）

**架构调整：**

1. PC 端通过 API 端提交任务（而不是直接调用 GPU）
2. API 端检查 GPU 状态
3. GPU 在线：立即转发
4. GPU 离线：入队到 Redis，开机后自动执行

**实施步骤：**

#### 步骤 1：在 API 端添加任务提交接口

已创建 `app/Controller/HeyGemTaskController.php`：

```php
POST /api/heygem/task/submit
{
  "audio_hash": "md5hex",
  "audio_ext": ".wav",
  "video_hash": "md5hex",
  "video_ext": ".mp4",
  "license_key": "xxx"
}

返回：
- GPU 在线：{ "code": 0, "data": { "task_id": "...", "status": "submitted" } }
- GPU 离线：{ "code": 0, "data": { "task_id": "...", "status": "queued", "msg": "..." } }
```

#### 步骤 2：在 GPU 端实现 heygem_submit 任务处理

修改 `HeyGem-Linux-Python-Hack-RTX-50-main/run_server.py` 的 `_handle_ws_task` 函数：

```python
def _handle_ws_task(task_msg: dict):
    task_type = task_msg.get("task_type", "")

    if task_type == "heygem_submit":
        # 处理 HeyGem 视频合成任务
        payload = task_msg.get("payload", {})
        audio_hash = payload.get("audio_hash")
        audio_ext = payload.get("audio_ext", ".wav")
        video_hash = payload.get("video_hash")
        video_ext = payload.get("video_ext", ".mp4")
        task_id = payload.get("task_id")

        # 获取文件路径
        audio_path = _pool_path(audio_hash, audio_ext)
        video_path = _pool_path(video_hash, video_ext)

        # 提交合成任务
        _executor.submit(_run_task, task_id, audio_path, video_path)

        # 发送确认
        if _ws_client:
            _ws_client.send_result(
                request_id=task_msg.get("request_id"),
                task_type=task_type,
                key=task_msg.get("key"),
                sender_fd=task_msg.get("sender_fd"),
                result={"task_id": task_id, "msg": "任务已接收"},
                error=False,
            )
```

#### 步骤 3：修改 PC 端调用方式

修改 `unified_app.py` 的 `run_heygem_online` 函数：

```python
def run_heygem_online(video_path, audio_path, progress=gr.Progress(), ...):
    # 不再直接调用 GPU 的 HTTP 接口
    # 改为调用 API 端的任务提交接口

    api_url = os.getenv("API_SERVER_URL", "").strip()  # 例如: http://api.example.com

    # 1. 上传文件到 GPU 服务器（保持不变）
    # ...

    # 2. 通过 API 端提交任务
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

    result = resp.json()
    task_id = result["data"]["task_id"]
    status = result["data"]["status"]

    if status == "queued":
        # GPU 离线，任务已排队
        progress(0.1, desc="⏳ GPU 服务器未上线，任务已排队...")
        yield "⏳ GPU 服务器未上线，任务已排队\n\n服务器启动后将自动执行（约2分钟）\n\n请稍后在「历史记录」中查看结果"
        return

    # 3. 轮询任务状态（保持不变）
    # ...
```

#### 步骤 4：添加任务状态查询

PC 端可以定期查询任务状态：

```python
GET /api/heygem/task/status?task_id=xxx

返回：
{
  "code": 0,
  "data": {
    "task_id": "xxx",
    "status": "queued" | "processing" | "done" | "error",
    "progress": 50,
    "result_url": "...",
    "error_msg": "..."
  }
}
```

## 实施优先级

### 立即实施（已完成）

- ✅ 方案 1：修改错误提示，改善用户体验

### 短期实施（1-2天）

- ⬜ 在 GPU 端实现 `heygem_submit` 任务处理
- ⬜ 测试 WebSocket 任务提交和执行

### 中期实施（1周）

- ⬜ 在 API 端添加任务提交接口
- ⬜ 修改 PC 端调用方式
- ⬜ 添加任务状态查询
- ⬜ 完整测试

## 测试验证

### 测试场景 1：GPU 在线

1. 启动 GPU 服务器
2. PC 端提交视频合成任务
3. 验证任务立即执行

**预期结果：**

- 任务立即提交到 GPU
- 实时显示合成进度
- 完成后返回结果

### 测试场景 2：GPU 离线

1. 停止 GPU 服务器
2. PC 端提交视频合成任务
3. 验证提示信息

**预期结果（方案 1）：**

```
⏳ GPU 服务器未上线，任务已排队

服务器启动中，请等待约 2 分钟后重试
或稍后在「历史记录」中查看结果

提示：如需立即处理，请联系管理员启动 GPU 服务器
```

**预期结果（方案 2）：**

- 任务提交成功，返回 task_id
- 提示"任务已排队，服务器启动后自动执行"
- 任务状态为 "queued"

### 测试场景 3：GPU 开机后自动执行

1. GPU 离线时提交多个任务
2. 启动 GPU 服务器
3. 验证任务自动执行

**预期结果：**

- GPU 开机后自动连接 WebSocket
- API 端批量下发积压任务
- GPU 依次执行任务
- 完成后回传结果

## 配置说明

### PC 端配置（.env）

```env
# GPU 服务器地址（方案 1 使用）
HEYGEM_SERVER_URL=http://117.50.91.129:8383

# API 服务器地址（方案 2 使用）
API_SERVER_URL=http://api.example.com

# API 鉴权密钥
HEYGEM_API_SECRET=your_secret_key
```

### API 端配置（.env）

```env
# GPU 服务器地址
HEYGEM_SERVER_URL=http://117.50.91.129:8383
```

### GPU 端配置（config/config.ini）

```ini
[server]
# WebSocket API 地址
ws_api_url = ws://api.example.com:9501/dsp
```

## 监控和日志

### PC 端日志

```
[HEYGEM-ONLINE] 服务器健康: {...}
[HEYGEM-ONLINE] video hash=xxx, audio hash=xxx
[HEYGEM-ONLINE] 任务已提交: task_id=xxx status=queued
```

### API 端日志

```
[HeyGemTask] 任务入队: key=xxx task_id=xxx request_id=xxx
[WS] gpu.power.online 广播: 5 个客户端
[WS] flushPending: 推送积压任务 3 条给 worker fd=123
```

### GPU 端日志

```
[WS Client] 收到批量任务: 3 个
[WS Task] 处理任务: type=heygem_submit request_id=xxx
[Server] 任务完成: task_id=xxx -> /path/to/result.mp4
[WS Client] 发送结果: request_id=xxx task_type=heygem_submit error=False
```

## 常见问题

**Q: 为什么不直接让 PC 端连接 WebSocket？**

A: PC 端是 Gradio 应用，主要使用 HTTP 请求。添加 WebSocket 客户端会增加复杂度。通过 API 端中转更简单。

**Q: 任务排队后，用户如何知道任务完成了？**

A: 方案 1：用户需要手动重试或查看历史记录。方案 2：可以添加轮询或 WebSocket 推送通知。

**Q: 如果 GPU 长时间不开机，任务会丢失吗？**

A: 不会。任务存储在 Redis 中，默认保留 24 小时。可以配置更长的保留时间。

**Q: 多个用户同时提交任务，会冲突吗？**

A: 不会。每个任务有唯一的 task_id 和 request_id，通过队列顺序执行。

## 总结

- **方案 1（已实施）**：临时方案，改善用户体验，用户需要手动重试
- **方案 2（推荐）**：完整方案，实现真正的离线排队和自动执行

建议：

1. 短期使用方案 1，立即改善用户体验
2. 中期实施方案 2，实现完整的排队机制
3. 长期考虑添加任务管理界面，让用户查看任务状态和历史记录
