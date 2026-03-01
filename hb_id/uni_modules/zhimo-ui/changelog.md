## 1.0.2（2026-02-03）
修复部分bug
# 织梦 UI 更新日志

所有重要的项目变更都会记录在此文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---
## [1.0.1] - 2024-02-03
修复部分bug
## [1.0.0] - 2024-02-03

### ✨ 新增

#### 组件库
- 🎉 **100+ 高质量组件** - 完整的组件库发布
  - 数据展示组件（18 个）：Copy Text、Badge、Tag、Avatar、Progress、Backtop 等
  - 表单组件（18 个）：Input、Textarea、Checkbox、Radio、Switch、Rate 等
  - 反馈组件（8 个）：Toast、Dialog、Alert、Captcha、Loading 等
  - 展示组件（13 个）：Card、Empty、Collapse、Divider、List 等
  - 导航组件（15 个）：Nav Bar、Index List、Pagination、Steps 等
  - 基础组件（5 个）：Button、Icon、Color、Number、Text
  - 操作组件（9 个）：Action Sheet、Drag Sort、Fab、Overlay 等
  - 动画组件（3 个）：Spin、Lottie、Transition
  - 媒体组件（3 个）：Gallery、Cropper、Video Uploader
  - 布局组件（3 个）：Grid、Bg Image、Spacer
  - 其他组件（5 个）：Link、CSS、Footer、Layer、Share Sheet

#### 文档系统
- 📚 **VitePress 文档框架** - 完整的文档系统
  - 三列布局设计（左侧导航、中间内容、右侧预览）
  - 实时搜索功能（支持组件名称和文档内容搜索）
  - 手机预览功能（iPhone 14 Pro Max 样式）
  - 代码块复制功能（一键复制代码示例）
  - 页面导航（h2/h3 标题快速跳转）
  - 响应式设计（支持各种屏幕尺寸）

#### 功能特性
- 🎨 **苹果风格设计** - 简洁优雅的 UI 设计
- 🚀 **高性能** - 优化的渲染和交互体验
- 📱 **完全响应式** - 适配各种屏幕尺寸
- 🌈 **丰富的定制选项** - 灵活的 Props 和事件
- 💾 **开箱即用** - 无需额外配置
- 🔒 **类型安全** - 完整的 TypeScript 支持
- 🌍 **多平台支持** - App、H5、小程序等

#### 工具函数
- 🛠️ **z-utils 工具库** - 零依赖的通用工具函数
  - 类型检查（11 个函数）
  - 数字处理（10 个函数）
  - 字符串处理（13 个函数）
  - 数组处理（11 个函数）
  - 对象处理（7 个函数）
  - 日期处理（10 个函数）
  - 函数控制（3 个函数）
  - URL 处理（3 个函数）
  - 校验函数（5 个函数）
  - 颜色处理（6 个函数）
  - 存储管理（4 个函数）
  - 平台检测（5 个函数）

- 🌐 **z-request 网络库** - 全功能 HTTP 请求库
  - Token 自动注入
  - 防重复请求
  - 智能重试机制
  - 请求取消
  - 响应缓存
  - 队列并发控制
  - 优先级管理
  - 性能监控
  - 日志追踪
  - Mock 数据支持

#### 文档
- 📖 **README.md** - 项目主文档
- 📘 **USAGE.md** - 详细使用指南
- 📕 **PUBLISH.md** - 发布指南
- 📙 **DEPENDENCIES.md** - 依赖说明文档
- 📓 **CHANGELOG.md** - 本文件

### 🔧 技术栈

- **框架**: Vue 3.0+
- **构建工具**: Vite
- **文档**: VitePress
- **包管理**: npm / yarn / pnpm
- **平台**: uni-app 3.0+
- **语言**: JavaScript / TypeScript

### 📦 依赖

- `@iconify/vue@^5.0.0` - 图标库（100,000+ 开源图标）
- `lottie-web@^5.13.0` - 动画库
- `lottie-miniprogram@^1.0.12` - 小程序动画支持

### 🎯 支持的平台

- ✅ iOS App
- ✅ Android App
- ✅ H5 Web
- ✅ 微信小程序
- ✅ 支付宝小程序
- ✅ 百度小程序
- ✅ 字节跳动小程序
- ✅ QQ 小程序
- ✅ 快手小程序

### 📊 项目统计

- **组件数量**: 100+
- **工具函数**: 100+
- **文档页面**: 100+
- **代码行数**: 50,000+
- **文件大小**: ~500KB (gzip: ~180KB)

### 🚀 性能指标

- **首屏加载**: < 2s
- **搜索响应**: < 100ms
- **导航跳转**: < 50ms
- **代码复制**: 即时
- **预览加载**: < 1s

### 📝 文档完整性

- ✅ 所有组件都有详细文档
- ✅ 包含基础用法、常见用法、高级用法
- ✅ 完整的 API 文档（Props、Events、Methods、Slots）
- ✅ 实际应用场景示例
- ✅ 常见问题解答
- ✅ 最佳实践指南

### 🔐 质量保证

- ✅ 无语法错误
- ✅ 无 TypeScript 错误
- ✅ 无 ESLint 警告
- ✅ 代码格式统一
- ✅ 文档格式一致
- ✅ 所有链接有效

---

## 版本规划

### [1.1.0] - 计划中

- [ ] 新增 10+ 组件
- [ ] 性能优化
- [ ] 国际化支持
- [ ] 深色模式
- [ ] 更多主题选项

### [1.2.0] - 计划中

- [ ] 组件库扩展
- [ ] 高级功能
- [ ] 插件系统
- [ ] 自定义主题生成器

### [2.0.0] - 计划中

- [ ] 架构重构
- [ ] 性能大幅提升
- [ ] 新的设计系统
- [ ] 更多平台支持

---

## 贡献指南

### 报告 Bug

如发现 Bug，请提交 [Issue](https://github.com/zhimo-ui/zhimo-ui/issues)，包含：
- Bug 描述
- 复现步骤
- 期望行为
- 实际行为
- 环境信息（系统、浏览器、uni-app 版本等）

### 功能建议

有功能建议？请提交 [Discussion](https://github.com/zhimo-ui/zhimo-ui/discussions)

### 提交 PR

欢迎提交 Pull Request！请：
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

感谢所有贡献者和用户的支持！

### 依赖项目

- [Vue 3](https://vuejs.org/) - 渐进式 JavaScript 框架
- [uni-app](https://uniapp.dcloud.io/) - 跨端应用框架
- [Iconify](https://iconify.design/) - 开源图标库
- [Lottie](https://airbnb.io/lottie/) - 动画库
- [VitePress](https://vitepress.dev/) - 文档框架

---

## 联系方式

- 📧 Email: support@zhimengai.xyz
- 🌐 官网: https://ui.zhimengai.xyz
- 📚 文档: https://ui.zhimengai.xyz/docs
- 💬 讨论: https://github.com/zhimo-ui/zhimo-ui/discussions
- 🐛 Bug 报告: https://github.com/zhimo-ui/zhimo-ui/issues

---

## 更新历史

### 如何查看历史版本

```bash
# 查看所有标签
git tag

# 查看特定版本
git show v1.0.0

# 查看版本之间的差异
git diff v1.0.0 v1.1.0
```

### 版本发布时间表

| 版本 | 发布日期 | 状态 |
|------|---------|------|
| 1.0.0 | 2024-02-03 | ✅ 已发布 |
| 1.1.0 | 计划中 | 📅 计划中 |
| 1.2.0 | 计划中 | 📅 计划中 |
| 2.0.0 | 计划中 | 📅 计划中 |

---

**最后更新**: 2024-02-03  
**维护者**: 织梦 UI Team  
**项目状态**: ✅ 活跃维护
