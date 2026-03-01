# z-backtop fix13

解决你遇到的两个报错：
1) onPageScroll is not defined：已在演示页 `import { onPageScroll } from '@dcloudio/uni-app'`
2) Cannot read property 'length' of undefined：演示页不再依赖你项目里可能有问题的 z-button / z-icon，避免触发旧组件 bug。

组件本身也不再强依赖 z-icon，默认用文本箭头 “↑”，你仍可用 slot 自定义。
