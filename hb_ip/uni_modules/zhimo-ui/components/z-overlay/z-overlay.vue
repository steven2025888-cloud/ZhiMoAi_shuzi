<template>
  <view
    v-if="visible"
    class="z-overlay"
    :class="[animClass, { 'is-closing': isClosing }]"
    :style="rootStyle"
    @touchmove.stop.prevent="onTouchMove"
  >
    <!-- mask -->
    <view
      class="z-overlay__mask"
      :class="{ 'has-blur': blur }"
      :style="maskStyle"
      @tap="handleMaskTap"
    />

    <!-- content wrapper -->
    <view
      class="z-overlay__content"
      :class="[contentClass]"
      :style="contentStyle"
      @tap.stop
    >
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick } from 'vue'

type Placement = 'center' | 'top' | 'bottom' | 'left' | 'right'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    /** z-index */
    zIndex?: number
    /** 遮罩颜色 */
    maskColor?: string
    /** 遮罩透明度 */
    maskOpacity?: number
    /** 点击遮罩关闭 */
    closeOnClick?: boolean
    /** 阻止背景滚动 */
    preventScroll?: boolean
    /** 内容位置 */
    placement?: Placement
    /** 内容内边距 */
    padding?: string
    /** 内容最大宽度 */
    maxWidth?: string
    /** 内容宽度 */
    width?: string
    /** 内容高度 */
    height?: string
    /** 内容圆角 */
    radius?: string
    /** 内容背景 */
    background?: string
    /** 启用模糊（毛玻璃效果） */
    blur?: boolean
    /** 模糊强度 */
    blurPx?: number
    /** 顶部安全区 */
    safeTop?: boolean
    /** 底部安全区 */
    safeBottom?: boolean
    /** 纯净模式（无背景/边框/阴影） */
    plain?: boolean
    /** 动画时长(ms) */
    duration?: number
    /** 内容阴影 */
    shadow?: boolean
  }>(),
  {
    zIndex: 9999,
    maskColor: 'rgba(0, 0, 0, 0.5)',
    maskOpacity: 1,
    closeOnClick: true,
    preventScroll: true,
    placement: 'center',
    padding: '24rpx',
    maxWidth: '640rpx',
    width: 'calc(100% - 64rpx)',
    height: 'auto',
    radius: '24rpx',
    background: '#ffffff',
    blur: false,
    blurPx: 10,
    safeTop: true,
    safeBottom: true,
    plain: false,
    duration: 250,
    shadow: true,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'open'): void
  (e: 'close'): void
  (e: 'closed'): void
  (e: 'mask-click'): void
}>()

const visible = ref(false)
const isClosing = ref(false)

watch(
  () => props.modelValue,
  async (v) => {
    if (v) {
      isClosing.value = false
      visible.value = true
      await nextTick()
      emit('open')
      lockScroll(true)
    } else {
      isClosing.value = true
      lockScroll(false)
      emit('close')
      setTimeout(() => {
        visible.value = false
        isClosing.value = false
        emit('closed')
      }, props.duration)
    }
  },
  { immediate: true }
)

function lockScroll(lock: boolean) {
  // #ifdef H5
  try {
    const body = document.body
    if (!body) return
    if (lock) {
      body.dataset.zOverlayLocked = '1'
      body.style.overflow = 'hidden'
      body.style.touchAction = 'none'
    } else {
      if (body.dataset.zOverlayLocked === '1') {
        body.style.overflow = ''
        body.style.touchAction = ''
        delete body.dataset.zOverlayLocked
      }
    }
  } catch {}
  // #endif
}

function close() {
  emit('update:modelValue', false)
}

function handleMaskTap() {
  emit('mask-click')
  if (props.closeOnClick) close()
}

function onTouchMove() {}

const animClass = computed(() => `anim-${props.placement}`)

const rootStyle = computed(() => ({
  zIndex: String(props.zIndex),
  '--z-overlay-duration': `${props.duration}ms`,
}))

const maskStyle = computed(() => {
  // 使用 rgba 背景色，这样跨平台兼容性最好
  const style: Record<string, string> = {
    background: props.maskColor,
    opacity: String(props.maskOpacity),
  }

  // 毛玻璃效果：使用 backdrop-filter（H5/部分小程序支持）
  if (props.blur && props.blurPx > 0) {
    style['--blur-value'] = `${props.blurPx}px`
  }

  return style
})

const contentClass = computed(() => ({
  [`is-${props.placement}`]: true,
  'has-safe-top': props.safeTop,
  'has-safe-bottom': props.safeBottom,
  'is-plain': props.plain,
  'has-shadow': props.shadow && !props.plain,
}))

const contentStyle = computed(() => {
  const style: Record<string, string> = {
    padding: props.padding,
    borderRadius: props.radius,
  }

  // 宽高根据位置设置
  if (props.placement === 'left' || props.placement === 'right') {
    style.width = props.width === 'calc(100% - 64rpx)' ? '80%' : props.width
    style.height = '100%'
    style.maxWidth = 'none'
  } else if (props.placement === 'top' || props.placement === 'bottom') {
    style.width = '100%'
    style.maxWidth = 'none'
    style.height = props.height
  } else {
    style.width = props.width
    style.maxWidth = props.maxWidth
    style.height = props.height
  }

  if (!props.plain) {
    style.background = props.background
  } else {
    style.background = 'transparent'
  }

  return style
})
</script>

<style scoped>
.z-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Mask */
.z-overlay__mask {
  position: absolute;
  inset: 0;
  transition: opacity var(--z-overlay-duration, 250ms) ease;
}

/* 毛玻璃效果 - 使用 backdrop-filter */
.z-overlay__mask.has-blur {
  -webkit-backdrop-filter: blur(var(--blur-value, 10px));
  backdrop-filter: blur(var(--blur-value, 10px));
}

.z-overlay.is-closing .z-overlay__mask {
  opacity: 0 !important;
}

/* Content base */
.z-overlay__content {
  position: absolute;
  box-sizing: border-box;
  transition: all var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1);
}

.z-overlay__content.has-shadow {
  box-shadow: 0 8rpx 40rpx rgba(0, 0, 0, 0.12);
}

.z-overlay__content.is-plain {
  box-shadow: none;
}

/* Center placement */
.z-overlay__content.is-center {
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%) scale(1);
  opacity: 1;
}

.z-overlay.anim-center .z-overlay__content {
  animation: fadeScaleIn var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-overlay.anim-center.is-closing .z-overlay__content {
  animation: fadeScaleOut var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes fadeScaleIn {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

@keyframes fadeScaleOut {
  from {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
  to {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.9);
  }
}

/* Top placement */
.z-overlay__content.is-top {
  left: 0;
  right: 0;
  top: 0;
  border-radius: 0 0 24rpx 24rpx;
}

.z-overlay__content.is-top.has-safe-top {
  padding-top: calc(24rpx + env(safe-area-inset-top));
}

.z-overlay.anim-top .z-overlay__content {
  animation: slideInTop var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-overlay.anim-top.is-closing .z-overlay__content {
  animation: slideOutTop var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes slideInTop {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}

@keyframes slideOutTop {
  from { transform: translateY(0); }
  to { transform: translateY(-100%); }
}

/* Bottom placement */
.z-overlay__content.is-bottom {
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 24rpx 24rpx 0 0;
}

.z-overlay__content.is-bottom.has-safe-bottom {
  padding-bottom: calc(24rpx + env(safe-area-inset-bottom));
}

.z-overlay.anim-bottom .z-overlay__content {
  animation: slideInBottom var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-overlay.anim-bottom.is-closing .z-overlay__content {
  animation: slideOutBottom var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes slideInBottom {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes slideOutBottom {
  from { transform: translateY(0); }
  to { transform: translateY(100%); }
}

/* Left placement */
.z-overlay__content.is-left {
  left: 0;
  top: 0;
  bottom: 0;
  border-radius: 0 24rpx 24rpx 0;
}

.z-overlay.anim-left .z-overlay__content {
  animation: slideInLeft var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-overlay.anim-left.is-closing .z-overlay__content {
  animation: slideOutLeft var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes slideInLeft {
  from { transform: translateX(-100%); }
  to { transform: translateX(0); }
}

@keyframes slideOutLeft {
  from { transform: translateX(0); }
  to { transform: translateX(-100%); }
}

/* Right placement */
.z-overlay__content.is-right {
  right: 0;
  top: 0;
  bottom: 0;
  border-radius: 24rpx 0 0 24rpx;
}

.z-overlay.anim-right .z-overlay__content {
  animation: slideInRight var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-overlay.anim-right.is-closing .z-overlay__content {
  animation: slideOutRight var(--z-overlay-duration, 250ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes slideOutRight {
  from { transform: translateX(0); }
  to { transform: translateX(100%); }
}
</style>
