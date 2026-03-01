# 手机端语音合成记录功能测试指南

## 快速测试步骤

### 步骤 1：测试 API 接口

```bash
# 1. 测试查询记录列表
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/history?page=1&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Machine-Code: YOUR_MACHINE_CODE" \
  -H "X-Device-Type: mobile"

# 预期结果：返回记录列表
{
  "code": 0,
  "data": {
    "list": [...],
    "total": 10,
    "page": 1,
    "limit": 5
  }
}

# 2. 测试查询记录详情
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/history/detail?id=1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 预期结果：返回单条记录
{
  "code": 0,
  "data": {
    "id": 1,
    "voice_url": "https://...",
    ...
  }
}

# 3. 测试音频下载代理
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/download?voice_url=xxx" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  --output test.mp3

# 预期结果：下载音频文件
```

### 步骤 2：测试手机端页面

#### 2.1 编译手机端

```bash
cd hb_id
npm run build:app-plus
```

或使用 HBuilderX：

1. 打开 HBuilderX
2. 打开 hb_id 项目
3. 运行 -> 运行到手机或模拟器 -> 运行到 Android App 基座

#### 2.2 测试功能

**测试 1：查看记录按钮**

1. 打开手机端应用
2. 登录账号
3. 进入"语音合成"页面
4. 检查是否有"📝 记录"按钮
5. 点击按钮

**预期结果：**
- ✅ 跳转到合成记录页面

**测试 2：记录列表显示**

1. 在合成记录页面
2. 检查记录列表是否正常显示

**预期结果：**
- ✅ 显示记录列表
- ✅ 每条记录显示：ID、状态、字数、时间
- ✅ 成功记录显示操作按钮

**测试 3：播放音频**

1. 点击任意成功记录的"▶ 播放"按钮
2. 等待音频加载

**预期结果：**
- ✅ 显示"🔊 正在播放..."提示
- ✅ 音频正常播放
- ✅ 播放完成后自动停止

**测试 4：停止播放**

1. 在播放过程中
2. 点击"停止"按钮

**预期结果：**
- ✅ 音频立即停止
- ✅ 播放提示消失

**测试 5：下载音频**

1. 点击"💾 保存"按钮
2. 等待下载完成

**预期结果：**
- ✅ 显示"下载中..."提示
- ✅ 下载完成后显示"保存成功"
- ✅ 文件保存到手机

**测试 6：用于视频合成**

1. 点击"➡️ 用于视频"按钮

**预期结果：**
- ✅ 跳转到视频合成页面
- ✅ 音频 URL 已自动填充

**测试 7：分页功能**

1. 如果记录超过 20 条
2. 点击"下一页"按钮

**预期结果：**
- ✅ 显示下一页记录
- ✅ 页码正确显示
- ✅ "上一页"按钮可用

**测试 8：空状态**

1. 使用没有合成记录的账号登录
2. 进入合成记录页面

**预期结果：**
- ✅ 显示空状态提示
- ✅ 显示"立即合成"按钮
- ✅ 点击按钮跳转到合成页面

## 常见问题排查

### 问题 1：记录列表为空

**可能原因：**
- 账号没有合成记录
- API 接口返回错误

**排查步骤：**

1. 检查 API 响应

```bash
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/history" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

2. 检查数据库

```sql
SELECT * FROM tts_logs WHERE license_key = 'YOUR_KEY' ORDER BY id DESC LIMIT 10;
```

3. 先进行一次语音合成，生成记录

### 问题 2：音频无法播放

**可能原因：**
- voice_url 为空
- sign 参数错误
- 网络问题

**排查步骤：**

1. 检查 voice_url 是否存在

```javascript
console.log('voice_url:', record.voice_url)
```

2. 检查代理下载接口

```bash
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/download?voice_url=xxx" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -v
```

3. 检查环境变量 `LIPVOICE_SIGN`

```bash
# 在 API 服务器上
echo $LIPVOICE_SIGN
```

4. 检查手机端日志

```javascript
// 在 playRecord 函数中添加
console.log('播放 URL:', url)

audioCtx.onError((err) => {
  console.error('播放错误:', err)
})
```

### 问题 3：下载失败

**可能原因：**
- 权限不足
- 存储空间不足
- 网络问题

**排查步骤：**

1. 检查手机存储空间
2. 检查应用权限（存储权限）
3. 检查网络连接
4. 查看控制台日志

### 问题 4：页面跳转失败

**可能原因：**
- 页面路径错误
- 页面未注册

**排查步骤：**

1. 检查 pages.json 配置

```json
{
  "path": "pages/tts/history",
  "style": {
    "navigationBarTitleText": "合成记录"
  }
}
```

2. 检查文件是否存在

```bash
ls -la hb_id/pages/tts/history.vue
```

3. 重新编译应用

### 问题 5：分页不工作

**可能原因：**
- total 值错误
- page 参数未更新

**排查步骤：**

1. 检查 API 响应

```javascript
console.log('total:', total.value)
console.log('page:', page.value)
console.log('limit:', limit.value)
```

2. 检查按钮状态

```javascript
console.log('上一页禁用:', page.value <= 1)
console.log('下一页禁用:', page.value >= Math.ceil(total.value / limit.value))
```

## 性能测试

### 测试 1：大量记录加载

1. 创建 100+ 条合成记录
2. 进入合成记录页面
3. 测试加载速度

**预期结果：**
- ✅ 加载时间 < 2 秒
- ✅ 页面流畅，无卡顿

### 测试 2：快速切换页面

1. 快速点击"上一页"/"下一页"
2. 测试响应速度

**预期结果：**
- ✅ 响应及时
- ✅ 无重复请求

### 测试 3：音频播放性能

1. 连续播放多个音频
2. 测试内存占用

**预期结果：**
- ✅ 内存占用正常
- ✅ 无内存泄漏

## 兼容性测试

### 测试平台

- ✅ Android 8.0+
- ✅ iOS 12.0+
- ✅ 微信小程序（如果支持）
- ✅ H5（如果支持）

### 测试设备

- ✅ 小屏手机（< 5 英寸）
- ✅ 中屏手机（5-6 英寸）
- ✅ 大屏手机（> 6 英寸）
- ✅ 平板

## 验收标准

### 功能完整性

- ✅ 可以查看合成记录列表
- ✅ 可以播放历史音频
- ✅ 可以下载音频到本地
- ✅ 可以将音频用于视频合成
- ✅ 支持分页浏览

### 用户体验

- ✅ 界面美观，符合设计规范
- ✅ 操作流畅，响应及时
- ✅ 错误提示清晰
- ✅ 加载状态明确

### 性能要求

- ✅ 列表加载时间 < 2 秒
- ✅ 音频播放延迟 < 1 秒
- ✅ 页面切换流畅

### 稳定性

- ✅ 无崩溃
- ✅ 无内存泄漏
- ✅ 网络异常时有友好提示

## 测试报告模板

```markdown
# 测试报告

## 测试信息

- 测试人员：[姓名]
- 测试时间：[日期]
- 测试版本：[版本号]
- 测试设备：[设备型号]
- 系统版本：[Android/iOS 版本]

## 测试结果

### 功能测试

| 功能 | 测试结果 | 备注 |
|------|----------|------|
| 查看记录列表 | ✅ 通过 | |
| 播放音频 | ✅ 通过 | |
| 下载音频 | ✅ 通过 | |
| 用于视频合成 | ✅ 通过 | |
| 分页浏览 | ✅ 通过 | |

### 性能测试

| 指标 | 预期值 | 实际值 | 结果 |
|------|--------|--------|------|
| 列表加载时间 | < 2s | 1.2s | ✅ 通过 |
| 音频播放延迟 | < 1s | 0.5s | ✅ 通过 |

### 问题列表

| 问题描述 | 严重程度 | 状态 |
|----------|----------|------|
| [问题1] | 高/中/低 | 待修复/已修复 |

### 总结

[测试总结]

### 建议

[改进建议]
```

## 总结

完成以上测试后，确认：

1. ✅ API 接口正常工作
2. ✅ 手机端页面正常显示
3. ✅ 所有功能正常运行
4. ✅ 性能满足要求
5. ✅ 兼容性良好

如有问题，请参考"常见问题排查"部分。
