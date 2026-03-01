# 统一任务调度系统部署文档

## 一、系统架构

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  手机端     │         │   PC 端     │         │  API 服务端 │
│  (hb_id)    │◄───────►│ (当前目录)  │◄───────►│   (app)     │
└─────────────┘         └─────────────┘         └──────┬──────┘
                                                        │
                                                        │ WebSocket
                                                        │ /dsp
                                                        │
                                                 ┌──────▼──────┐
                                                 │ GPU 服务端  │
                                                 │ (HeyGem)    │
                                                 └─────────────┘
```

## 二、部署步骤

### 1. GPU 服务端部署

#### 1.1 安装依赖

```bash
cd HeyGem-Linux-Python-Hack-RTX-50-main
pip install websocket-client>=1.6.0
```

或使用 requirements 文件：

```bash
pip install -r requirements_ws.txt
```

#### 1.2 配置 WebSocket 连接

编辑 `config/config.ini`，添加 WebSocket API 地址：

```ini
[server]
# ... 其他配置 ...

# WebSocket API 地址（连接到 API 端的 WebSocket 网关）
# 格式: ws://域名或IP:端口/dsp
ws_api_url = ws://your-api-server.com:9501/dsp
```

**示例配置：**

- 本地测试：`ws://127.0.0.1:9501/dsp`
- 生产环境：`ws://api.example.com:9501/dsp`

#### 1.3 启动服务

```bash
python run_server.py --host 0.0.0.0 --port 8383
```

**启动日志示例：**

```
[Server] 正在初始化数字人推理服务...
[Server] 数字人推理服务初始化完成
[Server] 正在启动 WebSocket 客户端: ws://api.example.com:9501/dsp
[WS Client] 正在连接 ws://api.example.com:9501/dsp...
[WS Client] 连接成功
[WS Client] 已发送注册消息
[WS Client] 注册成功，等待任务...
[Server] WebSocket 客户端已启动
[Server] 启动 API: 0.0.0.0:8383 (最大并发=3)
```

### 2. API 服务端配置

API 服务端（app）的 WebSocket 网关已经配置完成，无需修改。

**验证 WebSocket 网关：**

```bash
# 检查 WebSocket 服务是否运行
netstat -tlnp | grep 9501
```

**路由配置：**

- WebSocket 地址：`ws://your-api-server:9501/dsp`
- 资产列表：`GET /api/asset/list`
- 资产删除：`POST /api/asset/delete`

### 3. 手机端/PC 端配置

手机端和 PC 端无需修改，它们通过 API 端的 WebSocket 网关与 GPU 通信。

## 三、功能验证

### 3.1 验证 GPU 开机上线

**步骤：**

1. 启动 GPU 服务端
2. 观察日志，确认 WebSocket 连接成功
3. 检查 API 端日志，确认收到 `register` 消息

**预期日志（GPU 端）：**

```
[WS Client] 连接成功
[WS Client] 已发送注册消息
[WS Client] 注册成功，等待任务...
```

**预期日志（API 端）：**

```
[WS] Worker 注册: fd=123  workers=["123"]
[WS] gpu.power.online(兼容gpu_online) 广播: 5 个客户端
[WS] flushPending: 推送积压任务 3 条给 worker fd=123
```

### 3.2 验证资产删除（GPU 在线）

**测试步骤：**

1. 确保 GPU 服务端在线
2. 调用资产删除接口

```bash
curl -X POST http://api.example.com/api/asset/delete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": 123}'
```

**预期响应：**

```json
{
  "code": 0,
  "msg": "已删除"
}
```

**预期日志（GPU 端）：**

```
[WS Client] 处理任务: request_id=del_asset_xxx task_type=delete_asset
[WS Task] 处理任务: type=delete_asset request_id=del_asset_xxx
[WS Task] 删除文件: /path/to/asset.wav
[WS Task] 删除资产成功: id=123
[WS Client] 发送结果: request_id=del_asset_xxx task_type=delete_asset error=False
```

### 3.3 验证资产删除（GPU 离线）

**测试步骤：**

1. 停止 GPU 服务端
2. 调用资产删除接口

```bash
curl -X POST http://api.example.com/api/asset/delete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": 456}'
```

**预期响应：**

```json
{
  "code": 0,
  "msg": "已排队",
  "data": {
    "queued": true,
    "request_id": "del_asset_xxx",
    "msg": "GPU服务器未上线，删除任务已排队，服务器启动后自动执行（约2分钟）"
  }
}
```

**预期日志（API 端）：**

```
[AssetDsp] 任务入队: key=license_key task_type=delete_asset request_id=del_asset_xxx
```

3. 启动 GPU 服务端
4. 观察任务自动执行

**预期日志（GPU 端）：**

```
[WS Client] 收到批量任务: 1 个
[WS Client] 处理任务: request_id=del_asset_xxx task_type=delete_asset
[WS Task] 删除资产成功: id=456
```

### 3.4 验证资产列表查询

```bash
curl -X GET "http://api.example.com/api/asset/list?asset_type=voice" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期响应：**

```json
{
  "code": 0,
  "data": [
    {
      "id": 1,
      "asset_type": "voice",
      "name": "我的音色",
      "file_hash": "abc123...",
      "file_ext": ".wav",
      "file_size": 1024000,
      "created_at": 1234567890,
      "days_left": 28
    }
  ]
}
```

## 四、故障排查

### 4.1 WebSocket 连接失败

**症状：**

```
[WS Client] 错误: [Errno 111] Connection refused
[WS Client] 连接关闭: code=None msg=None
[WS Client] 5秒后重连...
```

**排查步骤：**

1. 检查 API 端 WebSocket 服务是否运行

```bash
netstat -tlnp | grep 9501
```

2. 检查防火墙规则

```bash
# 开放 9501 端口
firewall-cmd --zone=public --add-port=9501/tcp --permanent
firewall-cmd --reload
```

3. 检查 config.ini 中的 ws_api_url 配置是否正确

4. 测试网络连通性

```bash
telnet api.example.com 9501
```

### 4.2 任务未执行

**症状：**

- GPU 离线时任务入队成功
- GPU 上线后任务未自动执行

**排查步骤：**

1. 检查 Redis 中的队列

```bash
redis-cli
> KEYS dsp:pending_tasks:*
> LLEN dsp:pending_tasks:your_license_key
> LRANGE dsp:pending_tasks:your_license_key 0 -1
```

2. 检查 GPU 端是否收到批量任务

```
[WS Client] 收到批量任务: 0 个
```

如果收到 0 个任务，说明队列已清空或 Redis 连接有问题。

3. 检查 API 端日志

```
[WS] flushPending: 推送积压任务 0 条给 worker fd=123
```

### 4.3 任务重复执行

**症状：**

- 同一个任务被执行多次
- 资产被重复删除

**排查步骤：**

1. 检查 request_id 是否唯一

2. 检查 GPU 端的幂等性缓存

```python
# 在 ws_client.py 中添加日志
logger.info(f"已处理的请求数: {len(self._processed_requests)}")
```

3. 清理过期缓存

```python
# 定期调用清理函数
client.cleanup_processed_cache(ttl=3600)
```

### 4.4 GPU 服务端崩溃

**症状：**

```
[WS Task] 任务执行失败: ...
Traceback (most recent call last):
  ...
```

**排查步骤：**

1. 检查错误日志

```bash
tail -f dh.log
```

2. 检查磁盘空间

```bash
df -h
```

3. 检查 GPU 内存

```bash
nvidia-smi
```

4. 重启服务

```bash
pkill -f run_server.py
python run_server.py --host 0.0.0.0 --port 8383
```

## 五、监控与维护

### 5.1 健康检查

**GPU 服务端健康检查：**

```bash
curl http://gpu-server:8383/api/heygem/health
```

**预期响应：**

```json
{
  "code": 0,
  "msg": "ok",
  "initialized": true,
  "queue": {
    "total_tasks": 5,
    "processing": 2,
    "queued": 3,
    "max_concurrent": 3
  }
}
```

### 5.2 日志监控

**GPU 端日志：**

```bash
tail -f dh.log | grep -E "WS Client|WS Task"
```

**API 端日志：**

```bash
tail -f runtime/logs/hyperf.log | grep -E "WS|AssetDsp"
```

### 5.3 性能监控

**监控指标：**

- WebSocket 连接状态
- 任务队列长度
- 任务处理时长
- GPU 利用率
- 内存使用率

**监控脚本示例：**

```bash
#!/bin/bash
# monitor.sh

while true; do
  echo "=== $(date) ==="

  # 检查 WebSocket 连接
  echo "WebSocket 连接数:"
  redis-cli SCARD dsp:workers

  # 检查队列长度
  echo "队列任务数:"
  redis-cli KEYS "dsp:pending_tasks:*" | wc -l

  # 检查 GPU 状态
  nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv,noheader

  sleep 60
done
```

### 5.4 定期维护

**每日维护：**

- 检查日志文件大小，必要时轮转
- 检查磁盘空间
- 检查任务队列是否有积压

**每周维护：**

- 清理过期文件（自动清理线程会处理）
- 检查数据库大小
- 备份配置文件

**每月维护：**

- 更新依赖包
- 检查安全补丁
- 性能优化

## 六、扩展功能

### 6.1 添加新任务类型

在 `run_server.py` 的 `_handle_ws_task` 函数中添加新的任务类型：

```python
def _handle_ws_task(task_msg: dict):
    task_type = task_msg.get("task_type", "")

    if task_type == "your_new_task":
        # 处理新任务
        result = process_your_task(task_msg)

        # 发送结果
        if _ws_client:
            _ws_client.send_result(
                request_id=task_msg.get("request_id"),
                task_type=task_type,
                key=task_msg.get("key"),
                sender_fd=task_msg.get("sender_fd"),
                result=result,
                error=False,
            )
```

### 6.2 添加任务优先级

修改 Redis 队列结构，使用 Sorted Set 代替 List：

```python
# 入队时指定优先级
redis.zadd("dsp:pending_tasks:key", {msg_json: priority})

# 出队时按优先级取出
redis.zpopmin("dsp:pending_tasks:key", count=50)
```

### 6.3 添加任务进度回调

在任务处理过程中，定期发送进度更新：

```python
def process_long_task(task_msg):
    total = 100
    for i in range(total):
        # 处理任务
        time.sleep(0.1)

        # 发送进度
        if i % 10 == 0:
            _ws_client.send_result(
                request_id=task_msg.get("request_id"),
                task_type="progress",
                result={"progress": i, "total": total},
            )
```

## 七、安全建议

1. **使用 TLS/SSL**：生产环境使用 `wss://` 代替 `ws://`
2. **API 鉴权**：配置 `api_secret`，启用 API 鉴权
3. **限流**：在 API 端添加限流中间件
4. **日志脱敏**：避免在日志中输出敏感信息
5. **定期更新**：及时更新依赖包，修复安全漏洞

## 八、常见问题

**Q: WebSocket 连接频繁断开？**

A: 检查网络稳定性，增加心跳间隔，调整重连策略。

**Q: 任务队列积压严重？**

A: 增加 GPU 服务器数量，或增加 `max_concurrent` 配置。

**Q: 资产删除后仍然显示？**

A: 检查数据库同步，清理缓存。

**Q: GPU 内存不足？**

A: 减少 `max_concurrent`，或升级 GPU 硬件。

## 九、联系支持

如有问题，请联系技术支持团队。
