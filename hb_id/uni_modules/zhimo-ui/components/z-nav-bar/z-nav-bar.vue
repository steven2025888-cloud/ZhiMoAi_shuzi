<template>
  <view class="znb" :style="wrapStyle">
    <!-- 占位元素：fixed 时保持页面布局稳定 -->
    <view v-if="fixed && placeholder" class="znb__ph" :style="phStyle" />

    <!-- 导航栏主体 -->
    <view
      class="znb__bar"
      :class="barClass"
      :style="barStyle"
    >
      <!-- 状态栏安全区 -->
      <view v-if="safeTop" class="znb__safe" :style="safeStyle" />

      <!-- 内容行 -->
      <view class="znb__row" :style="rowStyle">
        <!-- 左侧区域 -->
        <view class="znb__left" @tap="onLeftTap">
          <slot name="left">
            <view v-if="showBack || leftText" class="znb__left-inner">
              <view v-if="showBack" class="znb__icon" :style="iconBgStyle">
                <z-icon :name="leftIcon" :size="iconSize" :color="color" />
              </view>
              <text v-if="leftText" class="znb__left-text" :style="{ color }">{{ leftText }}</text>
            </view>
          </slot>
        </view>

        <!-- 中间区域 -->
        <view class="znb__center" @tap="onTitleTap">
          <slot name="center">
            <view class="znb__title-wrap">
              <text v-if="title" class="znb__title" :style="{ color }">{{ title }}</text>
              <text v-if="subtitle" class="znb__sub" :style="{ color: subColor }">{{ subtitle }}</text>
            </view>
          </slot>
        </view>

        <!-- 右侧区域 -->
        <view class="znb__right" @tap="onRightTap">
          <slot name="right">
            <view v-if="rightText || rightIcon" class="znb__right-inner">
              <text v-if="rightText" class="znb__right-text" :style="{ color }">{{ rightText }}</text>
              <view v-if="rightIcon" class="znb__icon znb__icon--right">
                <z-icon :name="rightIcon" :size="iconSize" :color="color" />
              </view>
            </view>
          </slot>
        </view>
      </view>

      <!-- 底部分割线 -->
      <view v-if="splitLine" class="znb__line" :style="{ background: lineColor }" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Props 定义
const props = withDefaults(
  defineProps<{
    /** 标题文字 */
    title?: string
    /** 副标题 */
    subtitle?: string

    /** 背景色/渐变 */
    background?: string
    /** 主文字颜色 */
    color?: string
    /** 副标题颜色 */
    subColor?: string
    /** 分割线颜色 */
    lineColor?: string

    /** 是否固定在顶部 */
    fixed?: boolean
    /** 固定时是否显示占位元素 */
    placeholder?: boolean
    /** 是否包含状态栏安全区 */
    safeTop?: boolean
    /** 导航栏高度(px) */
    height?: number
    /** 左右内边距(px) */
    padding?: number
    /** z-index 层级 */
    zIndex?: number
    /** 是否显示底部分割线 */
    splitLine?: boolean

    /** 是否显示返回按钮 */
    showBack?: boolean
    /** 是否自动返回上一页 */
    autoBack?: boolean
    /** 左侧图标名称 */
    leftIcon?: string
    /** 左侧文字 */
    leftText?: string

    /** 右侧文字 */
    rightText?: string
    /** 右侧图标名称 */
    rightIcon?: string

    /** 是否启用毛玻璃效果 */
    blur?: boolean
    /** 毛玻璃模糊程度(px) */
    blurPx?: number
    /** 是否显示阴影 */
    shadow?: boolean
    /** 是否显示底部圆角 */
    rounded?: boolean
    /** 图标大小 */
    iconSize?: number
    /** 是否显示图标背景 */
    iconBg?: boolean
  }>(),
  {
    title: '',
    subtitle: '',
    background: '#ffffff',
    color: '#0f172a',
    subColor: '#64748b',
    lineColor: 'rgba(0,0,0,0.08)',

    fixed: false,
    placeholder: true,
    safeTop: true,
    height: 44,
    padding: 12,
    zIndex: 2000,
    splitLine: false,

    showBack: true,
    autoBack: true,
    leftIcon: 'lucide:chevron-left',
    leftText: '',

    rightText: '',
    rightIcon: '',

    blur: true,
    blurPx: 10,
    shadow: false,
    rounded: false,
    iconSize: 40,
    iconBg: true,
  }
)

// 事件定义
const emit = defineEmits<{
  (e: 'left-click'): void
  (e: 'right-click'): void
  (e: 'title-click'): void
}>()

// 获取状态栏高度
const safeTopPx = (() => {
  try {
    const info = uni.getSystemInfoSync()
    return Number(info.statusBarHeight) || 0
  } catch {
    return 0
  }
})()

// 计算属性
const heightPx = computed(() => Math.max(36, Number(props.height) || 44))
const padPx = computed(() => Math.max(0, Number(props.padding) || 0))

// CSS 变量
const wrapStyle = computed(() => ({
  '--znb-bg': props.background,
  '--znb-color': props.color,
  '--znb-sub': props.subColor,
}))

// 占位元素高度
const phStyle = computed(() => {
  const h = (props.safeTop ? safeTopPx : 0) + heightPx.value + (props.splitLine ? 1 : 0)
  return { height: `${h}px` }
})

// 状态栏安全区样式
const safeStyle = computed(() => ({
  height: `${safeTopPx}px`,
}))

// 内容行样式
const rowStyle = computed(() => ({
  height: `${heightPx.value}px`,
  paddingLeft: `${padPx.value}px`,
  paddingRight: `${padPx.value}px`,
}))

// 导航栏 class
const barClass = computed(() => ({
  'is-fixed': props.fixed,
  'has-line': props.splitLine,
  'has-shadow': props.shadow,
  'has-rounded': props.rounded,
  'has-blur': props.blur,
}))

// 导航栏样式
const barStyle = computed(() => {
  const style: Record<string, string> = {
    zIndex: String(props.zIndex),
    background: props.background,
  }

  // 毛玻璃效果
  if (props.blur) {
    const blurValue = `blur(${props.blurPx}px)`
    style.backdropFilter = blurValue
    style.webkitBackdropFilter = blurValue
    // 纯色背景时添加透明度以显示毛玻璃效果
    if (props.background.startsWith('#') && props.background.length <= 7) {
      style.background = 'rgba(255,255,255,0.86)'
    }
  }

  // 阴影
  if (props.shadow) {
    style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)'
  }

  // 圆角
  if (props.rounded) {
    style.borderRadius = '0 0 20px 20px'
  }

  return style
})

// 图标背景样式
const iconBgStyle = computed(() => {
  if (!props.iconBg) return {}
  // 根据背景色自动调整图标背景
  const isDark = props.background.includes('gradient') ||
    (props.background.startsWith('#') && isColorDark(props.background))
  return {
    // background: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(59,130,246,0.1)',
  }
})

// 判断颜色是否为深色
function isColorDark(hex: string): boolean {
  if (!hex.startsWith('#')) return false
  const color = hex.slice(1)
  const r = parseInt(color.slice(0, 2), 16)
  const g = parseInt(color.slice(2, 4), 16)
  const b = parseInt(color.slice(4, 6), 16)
  // 使用相对亮度公式
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance < 0.5
}

// 事件处理
function onLeftTap() {
  emit('left-click')
  if (!props.autoBack || !props.showBack) return
  try {
    const pages = getCurrentPages?.() ?? []
    if (pages.length > 1) {
      uni.navigateBack()
    }
  } catch {
    // 忽略错误
  }
}

function onTitleTap() {
  emit('title-click')
}

function onRightTap() {
  emit('right-click')
}
</script>

<style scoped>
.znb {
  width: 100%;
}

.znb__ph {
  width: 100%;
}

.znb__bar {
  width: 100%;
  background: var(--znb-bg);
  transition: box-shadow 0.2s ease, border-radius 0.2s ease;
}

.znb__bar.is-fixed {
  position: fixed;
  left: 0;
  top: 0;
}

.znb__bar.has-blur {
  /* 毛玻璃效果通过 JS 设置 */
}

.znb__safe {
  width: 100%;
}

.znb__row {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 三栏布局 */
.znb__left,
.znb__right {
  width: 25%;
  min-width: 100rpx;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.znb__left {
  justify-content: flex-start;
}

.znb__right {
  justify-content: flex-end;
}

.znb__center {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 左右内部容器 */
.znb__left-inner,
.znb__right-inner {
  display: flex;
  gap: 8rpx;
}

.znb__left-inner:active,
.znb__right-inner:active {
  background: rgba(15, 23, 42, 0.08);
}

/* 图标容器 */
.znb__icon {
  width: 40rpx;
  height: 40rpx;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease;
}

.znb__icon:active {
  transform: scale(0.95);
}

.znb__icon--right {
  background: transparent;
}

/* 文字样式 */
.znb__left-text,
.znb__right-text {
  font-size: 26rpx;
  color: var(--znb-color);
  font-weight: 600;
  max-width: 180rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 标题区域 */
.znb__title-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
}

.znb__title {
  font-size: 32rpx;
  font-weight: 700;
  line-height: 1.2;
  max-width: 480rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.znb__sub {
  margin-top: 2rpx;
  font-size: 22rpx;
  font-weight: 500;
  line-height: 1.2;
  max-width: 520rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--znb-sub);
  opacity: 0.85;
}

/* 分割线 */
.znb__line {
  width: 100%;
  height: 1px;
}
</style>
