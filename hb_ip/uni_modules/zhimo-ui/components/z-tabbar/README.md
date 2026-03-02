# z-tabbar 底部导航栏组件

高科技风格底部导航栏组件，支持 Vue 3 语法，提供丰富的主题和样式配置。

## 特性

- 🎨 **多种主题**：默认/深色/毛玻璃/渐变/霓虹
- ✨ **凸起按钮**：圆形/方形/菱形/六边形
- 🌊 **凹陷效果**：高科技凹陷背景
- 📍 **选中指示器**：线条/圆点/药丸/发光
- 🔢 **角标支持**：数字角标/红点
- 📱 **安全区适配**：自动适配 iPhone X 等异形屏

## 安装

将 `uni_modules/zhimo-ui` 目录复制到你的项目中。

## 基础用法

```vue
<template>
  <z-tabbar :list="list" v-model:active="active" @change="onChange" />
</template>

<script>
export default {
  data() {
    return {
      active: 0,
      list: [
        { text: '首页', icon: '/static/tabbar/home.png', activeIcon: '/static/tabbar/home_active.png' },
        { text: '分类', icon: '/static/tabbar/category.png', activeIcon: '/static/tabbar/category_active.png' },
        { text: '我的', icon: '/static/tabbar/user.png', activeIcon: '/static/tabbar/user_active.png' }
      ]
    }
  },
  methods: {
    onChange(e) {
      console.log('切换到', e.index)
    }
  }
}
</script>
```

## 中间凸起按钮

```vue
<template>
  <z-tabbar :list="list" center-style="circle" @click="onClick" />
</template>

<script>
export default {
  data() {
    return {
      list: [
        { text: '首页', icon: '/static/tabbar/home.png' },
        { text: '分类', icon: '/static/tabbar/category.png' },
        { 
          center: true,
          icon: '/static/tabbar/add.png',
          size: 100,
          bottom: 30,
          bg: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)'
        },
        { text: '消息', icon: '/static/tabbar/message.png' },
        { text: '我的', icon: '/static/tabbar/user.png' }
      ]
    }
  },
  methods: {
    onClick(e) {
      if (e.isCenter) {
        console.log('点击了中间按钮')
      }
    }
  }
}
</script>
```

## 凹陷效果

```vue
<z-tabbar 
  :list="list" 
  :concave="true"
  concave-bg="#f5f5f5"
  center-style="circle"
/>
```

## API

### Props

| 属性名 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| list | Array | [] | 导航项列表 |
| active | Number | 0 | 当前激活项索引 |
| theme | String | 'default' | 主题：default/dark/glass/gradient/neon |
| fixed | Boolean | true | 是否固定底部 |
| border | Boolean | true | 是否显示顶部边框 |
| borderColor | String | 'rgba(0,0,0,0.05)' | 边框颜色 |
| bgColor | String | '' | 背景色 |
| color | String | '#999' | 文字颜色 |
| activeColor | String | '#6366f1' | 激活颜色 |
| fontSize | Number | 22 | 字体大小(rpx) |
| fontWeight | Number | 400 | 字重 |
| fontWeightActive | Number | 500 | 激活字重 |
| iconSize | Number | 48 | 图标大小(rpx) |
| badgeBg | String | '#ef4444' | 角标背景色 |
| badgeColor | String | '#fff' | 角标文字颜色 |
| zIndex | Number | 999 | z-index |
| safeArea | Boolean | true | 是否适配安全区 |
| concave | Boolean | false | 是否显示凹陷效果 |
| concaveBg | String | '#f5f5f5' | 凹陷背景色 |
| centerStyle | String | 'circle' | 中间按钮风格：circle/square/diamond/hexagon |
| indicator | Boolean | false | 是否显示选中指示器 |
| indicatorStyle | String | 'line' | 指示器风格：line/dot/pill/glow |

### List 项属性

| 属性名 | 类型 | 说明 |
|-------|------|------|
| text | String | 文字 |
| icon | String | 图标路径 |
| activeIcon | String | 激活图标路径 |
| badge | Number/String | 角标内容 |
| dot | Boolean | 是否显示红点 |
| center | Boolean | 是否为中间凸起按钮 |
| size | Number | 中间按钮大小(rpx) |
| bottom | Number | 中间按钮距底部距离(rpx) |
| bg | String | 中间按钮背景色/渐变 |
| iconSize | Number | 中间按钮图标大小(rpx) |
| color | String | 中间按钮文字颜色 |

### Events

| 事件名 | 说明 | 回调参数 |
|-------|------|---------|
| change | 切换时触发 | { index, ...item } |
| click | 点击时触发 | { index, ...item, isCenter? } |
| init | 初始化完成 | { height } |

## 主题效果

### 默认主题 (default)
白色背景，简洁清爽

### 深色主题 (dark)
深蓝渐变背景，适合夜间模式

### 毛玻璃主题 (glass)
半透明磨砂效果，现代感十足

### 渐变主题 (gradient)
紫色渐变背景，活力四射

### 霓虹主题 (neon)
深色背景配合发光效果，科技感爆棚

## 注意事项

1. 图标建议使用 84x84 像素的图片
2. 中间凸起按钮在 nvue 页面可能有兼容性问题
3. 凹陷效果需要配合中间凸起按钮使用
4. 使用 `v-model:active` 可以实现双向绑定

## 静态资源

请在 `/static/images/tabbar/` 目录下准备以下图标：

- home.png / home_active.png - 首页图标
- category.png / category_active.png - 分类图标
- message.png / message_active.png - 消息图标
- user.png / user_active.png - 用户图标
- add.png - 添加图标（用于中间凸起按钮）

## 版本

v1.0.0

## 许可

MIT License
