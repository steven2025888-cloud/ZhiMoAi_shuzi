# 手机端语音合成记录功能实现

## 功能概述

为手机端添加了语音合成记录功能，用户可以：

1. 查看所有合成记录
2. 播放历史合成的音频
3. 下载音频到本地
4. 将历史音频用于视频合成
5. 分页浏览记录

## 实现内容

### 1. API 端（app）

#### 新增接口

**1.1 查询合成记录列表**

```
GET /api/dsp/voice/tts/history?page=1&limit=20
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "list": [
      {
        "id": 123,
        "model_id": 1,
        "text_len": 50,
        "task_id": "task_xxx",
        "voice_url": "https://...",
        "status": 1,
        "error_msg": null,
        "created_at": "2026-03-01 12:00:00"
      }
    ],
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

**1.2 查询单条记录详情**

```
GET /api/dsp/voice/tts/history/detail?id=123
```

**响应：**

```json
{
  "code": 0,
  "data": {
    "id": 123,
    "model_id": 1,
    "text_len": 50,
    "task_id": "task_xxx",
    "voice_url": "https://...",
    "status": 1,
    "error_msg": null,
    "created_at": "2026-03-01 12:00:00"
  }
}
```

#### 修改文件

- `app/Controller/VoiceTtsDspController.php`（新增 2 个方法）
- `app/routes.php`（新增 2 个路由）

### 2. 手机端（hb_id）

#### 新增页面

**2.1 合成记录页面**

文件：`hb_id/pages/tts/history.vue`

功能：
- 显示合成记录列表
- 支持分页浏览
- 播放音频
- 下载音频
- 用于视频合成

#### 新增 API 函数

文件：`hb_id/utils/api.js`

```javascript
// 查询合成记录列表
export function ttsHistory(page = 1, limit = 20)

// 查询合成记录详情
export function ttsHistoryDetail(id)
```

#### 修改文件

- `hb_id/pages.json`（添加页面配置）
- `hb_id/pages/tts/tts.vue`（添加"查看记录"按钮）
- `hb_id/utils/api.js`（添加 API 函数）

## 音频播放问题修复

### 问题描述

手机端无法直接播放音频，因为音频 URL 需要 `sign` 参数才能访问。

### 解决方案

使用 API 端的代理下载接口：

```
GET /api/dsp/voice/tts/download?voice_url=xxx
```

这个接口会：
1. 接收 `voice_url` 参数
2. 自动添加 `sign` 头（从环境变量 `LIPVOICE_SIGN` 读取）
3. 代理下载音频并返回给客户端

### 实现代码

```javascript
// hb_id/utils/api.js
export function ttsDownloadUrl(voiceUrl) {
  const baseUrl = getServerUrl().replace(/\/+$/, '')
  return `${baseUrl}/api/dsp/voice/tts/download?voice_url=${encodeURIComponent(voiceUrl)}`
}

// 使用
const audioUrl = ttsDownloadUrl(record.voice_url)
audioCtx.src = audioUrl
audioCtx.play()
```

## 使用说明

### 1. 查看合成记录

1. 打开手机端应用
2. 进入"语音合成"页面
3. 点击"📝 记录"按钮
4. 查看所有合成记录

### 2. 播放音频

**方法 1：点击记录卡片**

1. 在记录列表中点击任意记录
2. 选择"播放音频"
3. 音频开始播放

**方法 2：点击播放按钮**

1. 在记录卡片上直接点击"▶ 播放"按钮
2. 音频开始播放

### 3. 下载音频

1. 点击记录卡片或"💾 保存"按钮
2. 选择"保存到本地"
3. 音频下载并保存到手机

### 4. 用于视频合成

1. 点击"➡️ 用于视频"按钮
2. 自动跳转到视频合成页面
3. 音频已自动填充

### 5. 分页浏览

- 点击"上一页"/"下一页"按钮
- 查看更多记录

## 数据库表结构

使用现有的 `tts_logs` 表：

```sql
CREATE TABLE tts_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  license_key VARCHAR(255) NOT NULL,
  model_id INT NOT NULL,
  text_len INT NOT NULL,
  task_id VARCHAR(255),
  voice_url TEXT,
  status TINYINT NOT NULL, -- 1=成功, 2=失败
  error_msg TEXT,
  created_at DATETIME NOT NULL,
  INDEX idx_license_key (license_key),
  INDEX idx_created_at (created_at)
);
```

## 测试验证

### 测试 1：查询记录列表

```bash
curl -X GET "https://api.zhimengai.xyz/api/dsp/voice/tts/history?page=1&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**预期结果：**

```json
{
  "code": 0,
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

### 测试 2：播放音频

1. 打开手机端应用
2. 进入合成记录页面
3. 点击播放按钮
4. 验证音频是否正常播放

### 测试 3：下载音频

1. 点击保存按钮
2. 验证音频是否成功下载
3. 检查文件是否可以播放

### 测试 4：用于视频合成

1. 点击"用于视频"按钮
2. 验证是否跳转到视频合成页面
3. 检查音频是否已填充

## 注意事项

### 1. 权限要求

- 所有接口都需要登录（`LicenseCardAuthDspMiddleware`）
- 只能查看自己的合成记录

### 2. 性能优化

- 记录列表支持分页，默认每页 20 条
- 最大每页 100 条
- 按创建时间倒序排列

### 3. 音频播放

- 使用 `uni.createInnerAudioContext()` 播放
- 自动停止之前的播放
- 播放完成后自动释放资源

### 4. 错误处理

- 网络错误：显示"加载失败"提示
- 音频不存在：显示"该记录无可用音频"
- 播放失败：显示"播放失败"提示

## 后续优化建议

### 1. 添加搜索功能

```javascript
// 按文本内容搜索
GET /api/dsp/voice/tts/history?keyword=xxx

// 按日期范围搜索
GET /api/dsp/voice/tts/history?start_date=2026-03-01&end_date=2026-03-31
```

### 2. 添加删除功能

```javascript
// 删除单条记录
DELETE /api/dsp/voice/tts/history/:id

// 批量删除
DELETE /api/dsp/voice/tts/history/batch
```

### 3. 添加收藏功能

```sql
ALTER TABLE tts_logs ADD COLUMN is_favorite TINYINT DEFAULT 0;
```

### 4. 添加标签功能

```sql
ALTER TABLE tts_logs ADD COLUMN tags VARCHAR(255);
```

### 5. 添加统计功能

```javascript
// 统计合成次数、字数等
GET /api/dsp/voice/tts/stats
```

## 部署说明

### 1. API 端

无需重启，Hyperf 支持热重载。

如需手动重启：

```bash
php bin/hyperf.php server:restart
```

### 2. 手机端

重新编译应用：

```bash
cd hb_id
npm run build:app-plus
```

或使用 HBuilderX 重新打包。

### 3. 验证

1. 手机端重新登录
2. 进入语音合成页面
3. 点击"📝 记录"按钮
4. 验证功能是否正常

## 总结

本次更新实现了：

1. ✅ 合成记录查询接口（API 端）
2. ✅ 合成记录页面（手机端）
3. ✅ 音频播放功能（使用代理下载）
4. ✅ 音频下载功能
5. ✅ 用于视频合成功能
6. ✅ 分页浏览功能

**修改文件：**

- API 端：2 个文件
- 手机端：4 个文件（1 个新建）

**新增代码：**

- API 端：约 100 行
- 手机端：约 400 行

**风险评估：**

- 低风险
- 向后兼容
- 不影响现有功能
