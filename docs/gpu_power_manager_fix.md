# GPU 电源管理器问题修复

## 问题描述

当 PC 端执行视频合成任务时，GPU 服务器处于关机状态，但 GPU 电源管理器没有收到任务通知，导致无法自动开机。

### 问题日志

```
PC 端: 等待GPU服务器启动中 (已等待 25秒)

GPU Manager:
[WS] 连接: wss://api.zhimengai.xyz/dsp
[WS] 已连接
[WS] 已发送注册 (gpu_monitor)
[WS] 服务端确认: gpu_monitor
[GPU] 状态: 已关机
[Check] GPU=stopped, 有任务=False, 最后任务时间=None, 空闲=N/A
```

## 根本原因

在 `app/WebSocket/Dsp.php` 中，处理 `gpu.job.submit` 类型任务时，**没有通知 GPU Monitor**。

### 代码分析

**其他任务类型（正常）**:
```php
// url 任务
if ($senderKey !== '' && $type === 'url') {
    $msg = json_encode([...]);
    $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
    // ✓ 通知 GPU 监控器
    $this->_notifyGpuMonitors($server, ['type' => 'url', 'key' => $senderKey]);
    ...
}

// chatglm_video 任务
if ($senderKey !== '' && $type === 'chatglm_video') {
    $msg = json_encode([...]);
    $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
    // ✓ 通知 GPU 监控器
    $this->_notifyGpuMonitors($server, ['type' => 'chatglm_video', 'key' => $senderKey]);
    ...
}
```

**gpu.job.submit 任务（有问题）**:
```php
// gpu.job.submit 任务
if ($senderKey !== '' && ($type === 'gpu_task' || $type === 'gpu.job.submit')) {
    $msg = json_encode([...]);
    $sent = $this->_dispatchToWorker($server, $msg, $senderKey);
    // ✗ 缺少通知 GPU 监控器的代码
    if ($sent === 0) {
        ...
    }
}
```

## 解决方案

在 `app/WebSocket/Dsp.php` 第 238 行添加通知 GPU Monitor 的代码：

```php
$sent = $this->_dispatchToWorker($server, $msg, $senderKey);
// 同时通知 GPU 监控器有任务
$this->_notifyGpuMonitors($server, ['type' => 'gpu.job.submit', 'task_type' => $taskType, 'key' => $senderKey]);
if ($sent === 0) {
    ...
}
```

## 修复后的流程

```
PC 端提交视频合成任务
    ↓
Dsp.php 接收 gpu.job.submit
    ↓
├─→ 转发给 GPU Worker (如果在线)
└─→ 通知 GPU Monitor ✓ (新增)
    ↓
GPU Monitor 收到通知
    ↓
检测到 GPU 关机
    ↓
自动启动 GPU
    ↓
GPU 启动完成
    ↓
处理积压任务
```

## 测试验证

### 1. 重启 WebSocket 服务

修改 Dsp.php 后需要重启 Hyperf 服务：

```bash
# 停止服务
ps aux | grep hyperf
kill -9 <pid>

# 启动服务
cd /path/to/project
php bin/hyperf.php start
```

### 2. 重启 GPU Manager

```bash
# 停止
Ctrl+C

# 启动
python gpu_power_manager.py
```

### 3. 测试流程

1. 确保 GPU 服务器处于关机状态
2. PC 端提交视频合成任务
3. 观察 GPU Manager 日志

**预期日志**:
```
[WS] 收到消息: {"type":"gpu.job.submit","task_type":"heygem_submit","key":"..."}
[WS] 检测到 GPU 任务: gpu.job.submit
[Check] GPU=stopped, 有任务=True, 最后任务时间=None, 空闲=N/A
[Check] 检测到 GPU 任务，准备启动 GPU
[GPU] 开始启动...
[GPU] 已点击启动按钮
[GPU] 等待启动... (0s)
...
[GPU] ✓ 启动成功
```

## 相关文件

- `app/WebSocket/Dsp.php` - WebSocket 服务器（已修复）
- `gpu_power_manager.py` - GPU 电源管理器
- `docs/gpu_offline_fix.md` - GPU 离线排队问题文档

## 注意事项

1. **修改 PHP 代码后必须重启 Hyperf 服务**
2. GPU Monitor 需要保持运行状态
3. 确保 WebSocket 连接正常
4. 首次使用需要手动登录 GPU 控制台

## 其他任务类型

确保所有 GPU 任务类型都会通知 GPU Monitor：

| 任务类型 | 是否通知 | 说明 |
|---------|---------|------|
| `url` | ✓ | 视频转文字 |
| `chatglm_video` | ✓ | 视频生成 |
| `gpu.job.submit` | ✓ | 通用 GPU 任务（已修复） |
| `gpu_task` | ✓ | 旧版 GPU 任务（已修复） |

## 更新日志

### 2026-03-02

- 修复 `gpu.job.submit` 任务不通知 GPU Monitor 的问题
- 添加 `_notifyGpuMonitors` 调用
- 更新测试文档
