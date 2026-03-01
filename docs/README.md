# 统一任务调度系统

## 概述

本系统实现了手机端、PC 端、API 端、GPU 服务端之间的统一任务调度机制，支持 GPU 离线排队和开机自动执行。

## 系统架构

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

## 核心功能

### 1. 离线排队机制

- GPU 离线时，任务自动入队到 Redis
- 用户立即收到"已排队"响应
- 提示：`任务已排队，请等待约2分钟`

### 2. 开机自动执行

- GPU 开机后自动连接 WebSocket 网关
- API 端批量下发积压任务
- 任务自动执行，结果回传给客户端

### 3. 统一消息协议

所有消息遵循统一格式：

```json
{
  "type": "消息类型",
  "version": "1.0",
  "request_id": "唯一ID",
  "task_type": "任务类型",
  "payload": {},
  "error": false,
  "result": {}
}
```

### 4. 幂等性保证

- 使用 request_id 防止重复执行
- GPU 端维护已处理请求缓存
- 自动清理过期缓存

## 快速开始

### 1. 安装依赖

```bash
cd HeyGem-Linux-Python-Hack-RTX-50-main
pip install websocket-client
```

### 2. 配置 WebSocket

编辑 `config/config.ini`：

```ini
[server]
ws_api_url = ws://your-api-server:9501/dsp
```

### 3. 启动服务

```bash
python run_server.py
```

### 4. 验证功能

```bash
# 测试资产删除
curl -X POST http://api/api/asset/delete \
  -H "Authorization: Bearer TOKEN" \
  -d '{"id": 123}'
```

## 文档

- [快速开始指南](docs/quickstart.md) - 5 分钟快速部署
- [部署文档](docs/deployment.md) - 完整部署指南
- [问题修复总结](docs/fix_summary.md) - 修复内容和测试验证

## 支持的任务类型

- `delete_asset` - 删除资产（音色/数字人）
- `heygem_submit` - HeyGem 视频合成（未来扩展）
- `chatglm_video` - ChatGLM 视频生成（未来扩展）

## 关键文件

### 新增文件

- `HeyGem-Linux-Python-Hack-RTX-50-main/ws_client.py` - WebSocket 客户端
- `HeyGem-Linux-Python-Hack-RTX-50-main/requirements_ws.txt` - 依赖列表
- `docs/deployment.md` - 部署文档
- `docs/quickstart.md` - 快速开始指南
- `docs/fix_summary.md` - 问题修复总结

### 修改文件

- `HeyGem-Linux-Python-Hack-RTX-50-main/run_server.py` - 集成 WebSocket 客户端
- `HeyGem-Linux-Python-Hack-RTX-50-main/config/config.ini` - 添加 ws_api_url 配置

### 无需修改

- `app/WebSocket/Dsp.php` - WebSocket 网关（已完成）
- `app/Controller/AssetDspController.php` - 资产控制器（已完成）

## 配置说明

### GPU 服务端配置

```ini
[server]
# 最大并发任务数
max_concurrent = 3

# WebSocket API 地址（必填）
ws_api_url = ws://api.example.com:9501/dsp

# API 鉴权密钥（可选）
api_secret = your_secret_key
```

### API 服务端配置

```env
# GPU 服务器地址
HEYGEM_SERVER_URL=http://gpu-server:8383
```

## 故障排查

### WebSocket 连接失败

```bash
# 检查 API 端 WebSocket 服务
netstat -tlnp | grep 9501

# 检查防火墙
firewall-cmd --zone=public --add-port=9501/tcp --permanent

# 测试连通性
telnet api.example.com 9501
```

### 任务未执行

```bash
# 检查 Redis 队列
redis-cli KEYS "dsp:pending_tasks:*"
redis-cli LLEN dsp:pending_tasks:your_key

# 检查 GPU 端日志
tail -f dh.log | grep "WS"
```

### 查看日志

```bash
# GPU 端
tail -f dh.log

# API 端
tail -f runtime/logs/hyperf.log
```

## 监控

### 健康检查

```bash
# GPU 服务端
curl http://gpu-server:8383/api/heygem/health

# WebSocket 连接数
redis-cli SCARD dsp:workers

# 队列长度
redis-cli KEYS "dsp:pending_tasks:*" | wc -l
```

### 关键指标

- WebSocket 连接状态
- 任务队列长度
- 任务处理时长
- GPU 利用率
- 内存使用率

## 性能优化

### 调整并发数

根据 GPU 性能调整 `max_concurrent`：

- RTX 3090：3-5
- RTX 4090：5-8
- A100：8-12

### 网络优化

- 使用内网连接
- 启用 TCP BBR
- 增加 TCP 缓冲区

### 存储优化

- 使用 SSD
- 定期清理过期文件
- 使用对象存储

## 安全建议

1. 使用 TLS/SSL（wss://）
2. 配置 API 鉴权
3. 添加限流
4. 日志脱敏
5. 定期更新依赖

## 生产环境部署

### 使用 systemd

```bash
sudo systemctl enable heygem-gpu
sudo systemctl start heygem-gpu
sudo systemctl status heygem-gpu
```

### 使用 Supervisor

```bash
sudo supervisorctl start heygem-gpu
sudo supervisorctl status heygem-gpu
```

详见[部署文档](docs/deployment.md)。

## 常见问题

**Q: WebSocket 连接频繁断开？**

A: 检查网络稳定性，增加心跳间隔，调整重连策略。

**Q: 任务队列积压严重？**

A: 增加 GPU 服务器数量，或增加 `max_concurrent` 配置。

**Q: 资产删除后仍然显示？**

A: 检查数据库同步，清理缓存。

**Q: GPU 内存不足？**

A: 减少 `max_concurrent`，或升级 GPU 硬件。

## 技术栈

- **GPU 服务端**: Python 3.8+, Flask, OpenCV, websocket-client
- **API 服务端**: PHP 8.0+, Hyperf, Redis, MySQL
- **WebSocket**: Swoole WebSocket Server
- **消息队列**: Redis List
- **数据库**: SQLite (GPU 端), MySQL (API 端)

## 版本历史

### v1.0.0 (2026-03-01)

- 实现 GPU 端 WebSocket 客户端
- 实现离线排队机制
- 实现开机自动执行
- 统一消息协议
- 完善错误处理
- 编写完整文档

## 贡献

欢迎提交 Issue 和 Pull Request。

## 许可证

[MIT License](LICENSE)

## 联系方式

如有问题，请联系技术支持团队。
