# WebSocket GPU 电源管理流程说明

## 修改概述

实现了通过 WebSocket 自动管理 GPU 电源的完整流程，当 PC 端提交任务时：
1. 如果 GPU 在线 → 直接上传文件并处理
2. 如果 GPU 离线 → 自动触发开机 → 等待上线 → 上传文件并处理

## 修改的文件

### 1. unified_app.py

#### 修改点 1: TextExtractor 类新增方法
- **位置**: 第 2495 行附近
- **新增方法**: `_send_ws_request()`
- **功能**: 专门处理 GPU 电源管理的 WebSocket 请求
  - 发送 `gpu.job.submit` 请求
  - 如果收到 `gpu.power.offline` 响应，返回 `(False, response)`
  - 如果收到 `ack` 响应，返回 `(True, response)`

#### 修改点 2: run_heygem_online 函数重构
- **位置**: 第 1821 行开始
- **主要改动**:
  1. **步骤 1**: 通过 WebSocket 提交任务并检查 GPU 状态
     - 计算文件 hash（只计算一次）
     - 发送 `gpu.job.submit` 请求
     - 如果 GPU 离线，等待 `gpu.power.online` 消息（最多 30 分钟）
     - 如果 GPU 在线，直接继续

  2. **步骤 2**: GPU 上线后，执行文件上传和任务提交
     - 检查服务器是否已有文件（避免重复上传）
     - 上传缺失的文件
     - 提交合成任务
     - 轮询进度直到完成
     - 下载结果

- **删除的代码**:
  - 旧的 HTTP 健康检查循环（约 140 行）
  - 重复的初始化代码
  - 重复的 hash 计算

## 工作流程

```
PC 端提交任务
    ↓
计算文件 hash
    ↓
通过 WebSocket 发送 gpu.job.submit
    ↓
    ├─→ GPU 在线
    │       ↓
    │   收到 ack 响应
    │       ↓
    │   继续步骤 2
    │
    └─→ GPU 离线
            ↓
        收到 gpu.power.offline 响应
            ↓
        WebSocket 服务器通知 GPU Monitor
            ↓
        GPU Monitor 启动 GPU（约 2 分钟）
            ↓
        等待 gpu.power.online 消息
            ↓
        继续步骤 2

步骤 2: 上传文件和提交任务
    ↓
检查服务器已有文件
    ↓
上传缺失文件
    ↓
提交合成任务
    ↓
轮询进度
    ↓
下载结果
```

## 测试方法

### 方法 1: 使用测试脚本
```bash
python test_websocket_flow.py
```

这个脚本会：
1. 创建 TextExtractor 实例
2. 连接 WebSocket
3. 发送测试任务
4. 检查 GPU 状态响应
5. 如果 GPU 离线，等待上线通知

### 方法 2: 实际测试
1. 确保 GPU 服务器处于关机状态
2. 启动 unified_app.py
3. 上传视频和音频文件
4. 点击"开始合成"
5. 观察日志输出：
   ```
   [HEYGEM-ONLINE] 步骤1: 通过 WebSocket 提交任务
   [HEYGEM-ONLINE] GPU 离线，任务已入队
   [HEYGEM-ONLINE] 等待 GPU 上线...
   [HEYGEM-ONLINE] 等待 GPU 上线... (10s)
   [HEYGEM-ONLINE] 等待 GPU 上线... (20s)
   ...
   [HEYGEM-ONLINE] ✓ GPU 已上线
   [HEYGEM-ONLINE] 步骤2: GPU 已上线，开始上传文件
   ```

## 关键技术点

### 1. 避免 WebSocket recv() 冲突
- 问题: 多个协程同时调用 `recv()` 会导致冲突
- 解决: 使用 `TextExtractor._response_queue` 队列
  - 后台线程持续监听 WebSocket 消息
  - 所有消息放入队列
  - 业务代码从队列中获取消息

### 2. 消息类型处理
- `gpu.job.submit`: 提交任务请求
- `ack`: GPU 在线，任务已接收
- `gpu.power.offline`: GPU 离线，任务已入队
- `gpu.power.online`: GPU 已上线（广播消息）

### 3. 超时处理
- WebSocket 请求超时: 30 分钟（1800 秒）
- 等待 GPU 上线超时: 30 分钟
- 每 10 秒输出一次等待日志

## 注意事项

1. **WebSocket 连接**: 确保 `websockets` 模块已安装
   ```bash
   pip install websockets
   ```

2. **卡密配置**: 确保 `.license` 文件存在且包含有效的 `license_key`

3. **环境变量**: 确保 `.env` 文件配置正确
   ```
   HEYGEM_SERVER_URL=http://117.50.91.129:8383
   HEYGEM_API_SECRET=your_secret_key
   API_SERVER_URL=https://api.zhimengai.xyz
   ```

4. **GPU Monitor**: 确保 `gpu_power_manager.py` 正在运行并监听 WebSocket 消息

## 性能优化

1. **文件 hash 只计算一次**: 避免重复计算（大文件可能耗时较长）
2. **文件去重**: 检查服务器是否已有文件，避免重复上传
3. **异步处理**: WebSocket 连接在后台线程运行，不阻塞主线程

## 故障排查

### 问题 1: WebSocket 连接失败
- 检查网络连接
- 检查 `.license` 文件是否存在
- 查看日志: `[TextExtractor] 连接失败: ...`

### 问题 2: GPU 一直不上线
- 检查 `gpu_power_manager.py` 是否运行
- 检查 GPU 服务器网络连接
- 查看 GPU Monitor 日志

### 问题 3: 文件上传失败
- 检查 `HEYGEM_SERVER_URL` 配置
- 检查 GPU 服务器是否真正在线
- 查看日志: `[HEYGEM-ONLINE] 上传失败: ...`

## 后续优化建议

1. **断线重连**: 如果 WebSocket 断开，自动重连
2. **进度回调**: 文件上传时显示实时进度
3. **错误重试**: 网络错误时自动重试
4. **日志级别**: 添加 DEBUG/INFO/ERROR 日志级别控制
