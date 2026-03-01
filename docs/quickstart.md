# 快速开始指南

## 一、5 分钟快速部署

### 1. GPU 服务端配置

```bash
# 进入 GPU 服务端目录
cd HeyGem-Linux-Python-Hack-RTX-50-main

# 安装 WebSocket 客户端依赖
pip install websocket-client

# 编辑配置文件
vim config/config.ini
```

在 `config.ini` 中添加：

```ini
[server]
ws_api_url = ws://your-api-server:9501/dsp
```

**重要提示：**

- 将 `your-api-server` 替换为实际的 API 服务器地址
- 如果是本地测试，使用 `ws://127.0.0.1:9501/dsp`
- 如果是生产环境，使用实际域名或 IP

### 2. 启动服务

```bash
# 启动 GPU 服务端
python run_server.py
```

**成功标志：**

看到以下日志表示启动成功：

```
[WS Client] 连接成功
[WS Client] 注册成功，等待任务...
[Server] 启动 API: 0.0.0.0:8383 (最大并发=3)
```

### 3. 测试功能

#### 测试 1：资产删除（GPU 在线）

```bash
curl -X POST http://your-api-server/api/asset/delete \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"id": 123}'
```

**预期结果：**

```json
{
  "code": 0,
  "msg": "已删除"
}
```

#### 测试 2：资产删除（GPU 离线）

1. 停止 GPU 服务端：`Ctrl+C`
2. 再次调用删除接口

**预期结果：**

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

3. 重新启动 GPU 服务端
4. 观察日志，任务会自动执行

```
[WS Client] 收到批量任务: 1 个
[WS Task] 删除资产成功: id=123
```

## 二、配置说明

### GPU 服务端配置（config/config.ini）

```ini
[server]
# 最大并发任务数（根据 GPU 性能调整）
max_concurrent = 3

# WebSocket API 地址（必填）
ws_api_url = ws://api.example.com:9501/dsp

# API 鉴权密钥（可选，建议生产环境启用）
api_secret = your_secret_key
```

### API 服务端配置（.env）

API 服务端已配置完成，无需修改。

如需修改 GPU 服务器地址，编辑 `.env`：

```env
HEYGEM_SERVER_URL=http://gpu-server:8383
```

## 三、常用命令

### 启动服务

```bash
# GPU 服务端
cd HeyGem-Linux-Python-Hack-RTX-50-main
python run_server.py

# 指定端口
python run_server.py --port 8383

# 指定最大并发数
python run_server.py --max-concurrent 5
```

### 查看日志

```bash
# GPU 服务端日志
tail -f dh.log

# 只看 WebSocket 相关日志
tail -f dh.log | grep "WS"

# API 服务端日志
tail -f runtime/logs/hyperf.log
```

### 检查状态

```bash
# 检查 GPU 服务端健康状态
curl http://gpu-server:8383/api/heygem/health

# 检查 WebSocket 连接数（在 API 服务端执行）
redis-cli SCARD dsp:workers

# 检查任务队列长度
redis-cli KEYS "dsp:pending_tasks:*"
```

### 清理队列

```bash
# 清空所有任务队列（谨慎使用）
redis-cli KEYS "dsp:pending_tasks:*" | xargs redis-cli DEL

# 清空特定 license_key 的队列
redis-cli DEL dsp:pending_tasks:your_license_key
```

## 四、故障排查速查表

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| WebSocket 连接失败 | API 服务端未启动 | 启动 API 服务端 |
| WebSocket 连接失败 | 防火墙阻止 | 开放 9501 端口 |
| WebSocket 连接失败 | ws_api_url 配置错误 | 检查配置文件 |
| 任务未执行 | GPU 服务端未启动 | 启动 GPU 服务端 |
| 任务未执行 | Redis 连接失败 | 检查 Redis 服务 |
| 任务重复执行 | request_id 重复 | 检查客户端代码 |
| GPU 内存不足 | 并发数过高 | 减少 max_concurrent |

## 五、生产环境部署建议

### 1. 使用进程管理工具

**使用 systemd：**

创建 `/etc/systemd/system/heygem-gpu.service`：

```ini
[Unit]
Description=HeyGem GPU Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/HeyGem-Linux-Python-Hack-RTX-50-main
ExecStart=/usr/bin/python3 run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable heygem-gpu
sudo systemctl start heygem-gpu
sudo systemctl status heygem-gpu
```

**使用 Supervisor：**

创建 `/etc/supervisor/conf.d/heygem-gpu.conf`：

```ini
[program:heygem-gpu]
command=/usr/bin/python3 run_server.py
directory=/path/to/HeyGem-Linux-Python-Hack-RTX-50-main
user=your_user
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/heygem-gpu.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start heygem-gpu
```

### 2. 配置日志轮转

创建 `/etc/logrotate.d/heygem-gpu`：

```
/path/to/HeyGem-Linux-Python-Hack-RTX-50-main/dh.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 your_user your_group
}
```

### 3. 配置监控告警

使用 Prometheus + Grafana 监控：

- GPU 利用率
- 内存使用率
- WebSocket 连接状态
- 任务队列长度
- 任务处理时长

### 4. 配置备份

定期备份：

- 配置文件：`config/config.ini`
- 数据库：`assets.db`
- 资产文件：`uploads/assets/`

## 六、性能优化建议

### 1. 调整并发数

根据 GPU 性能调整 `max_concurrent`：

- RTX 3090：3-5
- RTX 4090：5-8
- A100：8-12

### 2. 优化网络

- 使用内网连接（避免公网延迟）
- 启用 TCP BBR 拥塞控制
- 增加 TCP 缓冲区大小

### 3. 优化存储

- 使用 SSD 存储资产文件
- 定期清理过期文件
- 使用对象存储（如 MinIO）

### 4. 优化数据库

- 定期执行 `VACUUM` 清理 SQLite
- 添加索引优化查询
- 考虑迁移到 PostgreSQL

## 七、下一步

- 阅读完整的[部署文档](deployment.md)
- 了解[架构设计](architecture.md)
- 查看[API 文档](api.md)
- 加入技术支持群

## 八、获取帮助

如有问题，请：

1. 查看日志文件
2. 阅读故障排查文档
3. 联系技术支持团队
