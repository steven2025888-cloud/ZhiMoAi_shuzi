# z-spin 旋转动画组件

## 简介

`z-spin` 是一个通用的旋转动画组件，可以让任意元素进行旋转动画，常用于加载状态展示。

## 特性

- 🎯 支持自定义宽高
- ⏱️ 支持自定义动画时长
- 🎨 支持多种动画曲线
- ↻ 支持正向/反向旋转
- ⏸️ 支持暂停/播放控制
- 📱 兼容 Vue3 + uni-app

## 使用方式

### 基础用法

```vue
<z-spin>
  <view>旋转内容</view>
</z-spin>
```

### 自定义大小

```vue
<z-spin :width="60" :height="60">
  <view>内容</view>
</z-spin>
```

### 自定义速度

```vue
<!-- 慢速旋转 -->
<z-spin :duration="2000">
  <view>慢速</view>
</z-spin>

<!-- 快速旋转 -->
<z-spin :duration="400">
  <view>快速</view>
</z-spin>
```

### 动画曲线

```vue
<z-spin timing="ease">
  <view>缓动</view>
</z-spin>
```

### 反向旋转

```vue
<z-spin direction="reverse">
  <view>逆时针</view>
</z-spin>
```

### 暂停控制

```vue
<z-spin :paused="isPaused">
  <view>可控旋转</view>
</z-spin>
```

## Props 属性

| 属性名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| width | Number/String | 0 | 宽度，单位rpx，0为auto |
| height | Number/String | 0 | 高度，单位rpx，0为auto |
| duration | Number | 850 | 动画时长，单位ms |
| timing | String | 'linear' | 动画曲线，可选：linear/ease/ease-in/ease-out/ease-in-out |
| paused | Boolean | false | 是否暂停动画 |
| direction | String | 'normal' | 旋转方向，可选：normal(顺时针)/reverse(逆时针) |

## Slots 插槽

| 插槽名 | 说明 |
|--------|------|
| default | 需要旋转的内容 |

## 示例

### 加载图标

```vue
<z-spin>
  <view class="loading-icon"></view>
</z-spin>

<style>
.loading-icon {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  border: 4rpx solid #5b7fff;
  border-left-color: transparent;
}
</style>
```

### 图片旋转

```vue
<z-spin :duration="1500">
  <image src="/static/logo.png" style="width: 60rpx; height: 60rpx;"></image>
</z-spin>
```

### 组合效果

```vue
<!-- 双层旋转 -->
<view class="container">
  <z-spin :duration="3000">
    <view class="outer-ring"></view>
  </z-spin>
  <z-spin :duration="1500" direction="reverse">
    <view class="inner-ring"></view>
  </z-spin>
</view>
```

## 注意事项

1. 组件默认为 `inline-flex` 布局
2. 在 nvue 环境下使用原生动画，性能更优
3. `paused` 属性在 nvue 环境下可能有延迟
4. 建议加载动画时长设置在 500ms-1500ms 之间

## 兼容性

- ✅ H5
- ✅ 微信小程序
- ✅ App (vue/nvue)
- ✅ 支付宝小程序
- ✅ 其他小程序平台
