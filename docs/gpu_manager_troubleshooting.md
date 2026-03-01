# GPU 电源管理器问题排查和修复指南

## 问题现象

PC 端提交视频合成任务后，显示"等待GPU服务器启动中"，但 GPU Manager 没有自动开机。

## 排查步骤

### 步骤 1: 运行诊断工具

```bash
python diagnose_gpu_manager.py
```

这个工具会检查:
1. WebSocket 连接是否正常
2. GPU Monitor 注册是否成功
3. 任务通知是否能到达 GPU Monitor
4. GPU Manager 是否在运行

### 步骤 2: 检查 Hyperf 服务

**重要**: 修改 Dsp.php 后必须重启 Hyperf 服务！

```bash
# 查找 Hyperf 进程
ps aux | grep hyperf

# 停止服务
kill -9 <pid>

# 启动服务
cd /path/to/project
php bin/hyperf.php start

# 确认服务已启动
ps aux | grep hyperf
```

### 步骤 3: 检查 GPU Manager 日志

启动 GPU Manager 并查看日志:

```bash
python gpu_power_manager.py
```

**正常日志应该包含**:

```
[WS] 连接: wss://api.zhimengai.xyz/dsp
[WS] 已连接
[WS] 已发送注册 (gpu_monitor)
[WS] 服务端确认: gpu_monitor
[Check] GPU 状态检查循环启动
```

**当有任务时应该看到**:

```
[WS] 收到消息: {"type":"gpu.job.submit",...}
[WS] 检测到 GPU 任务: gpu.job.submit
[Check] GPU=stopped, 有任务=True, 最后任务时间=...
[Check] 检测到 GPU 任务，准备启动 GPU
[GPU] 开始启动...
```

### 步骤 4: 常见问题

#### 问题 A: GPU Monitor 未收到任务通知

**症状**:
- GPU Manager 日志中没有 "[WS] 检测到 GPU 任务"
- 诊断工具显示"任务通知: ✗ 异常"

**原因**:
- Dsp.php 未添加 `_notifyGpuMonitors` 调用
- Hyperf 服务未重启

**解决**:
1. 确认 Dsp.php 第 243 行有:
   ```php
   $this->_notifyGpuMonitors($server, ['type' => 'gpu.job.submit', 'task_type' => $taskType, 'key' => $senderKey]);
   ```
2. 重启 Hyperf 服务
3. 重新运行诊断工具

#### 问题 B: GPU Manager 检测状态错误

**症状**:
- GPU Manager 显示 `[Check] GPU=running` 但实际上 GPU 已关机
- 或者显示 `[Check] GPU=stopped` 但实际上 GPU 正在运行

**原因**:
- 页面元素选择器不正确
- 页面加载不完整

**解决**:
1. 检查控制台页面是否正确加载
2. 手动刷新页面: 在 GPU Manager 的浏览器窗口中按 F5
3. 检查页面 HTML 结构是否变化

#### 问题 C: 登录状态丢失

**症状**:
- 每次启动都需要重新登录

**原因**:
- 浏览器数据目录权限问题
- Cookies 未正确保存

**解决**:
1. 删除旧的数据目录:
   ```bash
   rm -rf gpu_browser_data
   ```
2. 重新启动 GPU Manager
3. 手动登录一次
4. 确认数据目录中有文件生成:
   ```bash
   ls -la gpu_browser_data/
   ```

#### 问题 D: has_pending_task 标志位问题

**症状**:
- GPU Manager 收到任务通知
- 但是 `[Check]` 日志显示 `有任务=False`

**原因**:
- 标志位在检查前被重置

**临时解决**:
在 `_check_and_manage_gpu` 方法开始处添加日志:

```python
async def _check_and_manage_gpu(self):
    """检查并管理 GPU 状态"""
    try:
        # 添加详细日志
        print(f"[Check] 开始检查: has_pending_task={self.has_pending_task}")

        # 检查 GPU 状态
        status = await self.check_gpu_status()
        ...
```

## 完整测试流程

### 1. 准备环境

```bash
# 确保 Hyperf 服务已重启
ps aux | grep hyperf
kill -9 <pid>
php bin/hyperf.php start

# 确保 GPU 服务器已关机
# 在控制台页面手动确认
```

### 2. 启动 GPU Manager

```bash
python gpu_power_manager.py
```

等待看到:
```
[WS] 服务端确认: gpu_monitor
[Check] GPU 状态检查循环启动
[GPU] 状态: 已关机
```

### 3. 提交测试任务

在另一个终端运行:

```bash
python test_gpu_job_notification.py
```

或者在 PC 端提交真实的视频合成任务。

### 4. 观察 GPU Manager 日志

应该看到:

```
[WS] 收到消息: {"type":"gpu.job.submit",...}
[WS] 检测到 GPU 任务: gpu.job.submit
[Check] GPU=stopped, 有任务=True, ...
[Check] 检测到 GPU 任务，准备启动 GPU
[GPU] 开始启动...
[GPU] 已点击启动按钮
[GPU] 等待启动... (0s)
...
[GPU] ✓ 启动成功
```

### 5. 验证 GPU 已启动

在控制台页面确认 GPU 状态为"运行中"。

## 调试技巧

### 1. 增加日志输出

在关键位置添加 print 语句:

```python
# 在 ws_loop 中
elif msg_type in ["url", "chatglm_video", "gpu.job.submit", "gpu_task"]:
    print(f"[DEBUG] 收到任务: type={msg_type}, data={data}")
    self.has_pending_task = True
    print(f"[DEBUG] 设置 has_pending_task=True")
    self.last_task_time = datetime.now()
    print(f"[DEBUG] 设置 last_task_time={self.last_task_time}")

# 在 _check_and_manage_gpu 中
async def _check_and_manage_gpu(self):
    print(f"[DEBUG] 检查开始: has_pending_task={self.has_pending_task}")
    status = await self.check_gpu_status()
    print(f"[DEBUG] GPU 状态: {status}")
    has_task = self.has_pending_task
    print(f"[DEBUG] has_task={has_task}")
    ...
```

### 2. 使用诊断工具

```bash
# 检查任务通知机制
python diagnose_gpu_manager.py

# 测试任务通知
python test_gpu_job_notification.py

# 测试关机功能
python test_gpu_shutdown.py quick
```

### 3. 检查 Redis 状态

```bash
# 连接 Redis
redis-cli

# 查看 GPU Monitor
SMEMBERS dsp:gpu_monitors

# 查看任务状态
KEYS dsp:task_status:*
HGETALL dsp:task_status:<key>

# 查看待处理任务
KEYS dsp:pending_tasks:*
LRANGE dsp:pending_tasks:<key> 0 -1
```

## 联系支持

如果以上步骤都无法解决问题，请提供以下信息:

1. 诊断工具的完整输出
2. GPU Manager 的完整日志
3. Hyperf 服务的日志
4. PC 端的错误信息
5. 控制台页面的截图

## 快速修复命令

```bash
# 一键重启所有服务
cd /path/to/project

# 1. 重启 Hyperf
ps aux | grep hyperf | awk '{print $2}' | xargs kill -9
php bin/hyperf.php start

# 2. 重启 GPU Manager
# 先停止旧的进程 (Ctrl+C)
# 然后启动新的
python gpu_power_manager.py

# 3. 运行诊断
python diagnose_gpu_manager.py
```
