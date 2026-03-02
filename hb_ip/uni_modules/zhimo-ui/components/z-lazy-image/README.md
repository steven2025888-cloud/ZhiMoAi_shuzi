# z-lazy-image

图片懒加载组件（Vue3 / uni-app），带骨架屏、占位图、错误兜底与苹果风格 UI。

## Props（常用）
- src: 图片地址
- placeholder: 占位图（建议小图，可模糊）
- errorSrc: 失败兜底图
- width: rpx，-1 为 100%
- height: rpx，0/-1 为 auto
- radius: 圆角 rpx
- preloadBottom: 进入视口前的预加载距离（px）
- skeleton: 是否显示骨架闪光
- fade/fadeDuration: 渐显
- shadow/border: 阴影/描边

## Events
- visible: 图片进入视口（开始加载）
- load/error/click
