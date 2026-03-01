<template>
  <view
    v-if="visible"
    class="z-dialog-wrapper"
    :style="wrapperStyle"
  >
    <!-- 遮罩层 -->
    <view
      class="z-dialog-mask"
      :class="{ 'is-closing': isClosing }"
      :style="maskStyle"
      @tap="handleMaskClick"
    />

    <!-- 对话框 -->
    <view
      class="z-dialog"
      :class="[`is-${theme}`, { 'is-closing': isClosing }]"
      :style="dialogStyle"
      @tap.stop
    >
      <!-- 关闭按钮 -->
      <view v-if="closable" class="z-dialog__close" @tap="close">
        <z-icon name="mdi:close" :size="36" color="#9ca3af" />
      </view>

      <!-- 图标 -->
      <view v-if="icon || theme !== 'default'" class="z-dialog__icon">
        <view class="z-dialog__icon-wrap" :style="iconWrapStyle">
          <z-icon :name="iconName" :size="48" :color="iconColor" />
        </view>
      </view>

      <!-- 标题 -->
      <text v-if="title" class="z-dialog__title" :style="{ color: titleColor }">
        {{ title }}
      </text>

      <!-- 内容区域 -->
      <view class="z-dialog__content" :class="{ 'no-title': !title }">
        <text v-if="content" class="z-dialog__text" :style="{ color: contentColor }">
          {{ content }}
        </text>
        <slot />
      </view>

      <!-- 按钮组 -->
      <view v-if="buttons && buttons.length > 0" class="z-dialog__footer" :class="[`is-${buttonLayout}`]">
        <view
          v-for="(button, index) in buttons"
          :key="index"
          class="z-dialog__button"
          :class="[
            button.type ? `is-${button.type}` : '',
            { 'is-primary': index === buttons.length - 1 && !button.type }
          ]"
          :style="getButtonStyle(button, index)"
          @tap="handleButtonClick(index)"
        >
          <z-icon v-if="button.icon" :name="button.icon" :size="32" :color="getButtonTextColor(button, index)" class="z-dialog__button-icon" />
          <text class="z-dialog__button-text" :style="{ color: getButtonTextColor(button, index) }">
            {{ button.text }}
          </text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'

interface DialogButton {
  text: string
  color?: string
  type?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
  icon?: string
}

interface Props {
  show?: boolean
  title?: string
  titleColor?: string
  content?: string
  contentColor?: string
  buttons?: DialogButton[]
  background?: string
  borderRadius?: number | string
  maskColor?: string
  maskOpacity?: number
  maskClosable?: boolean
  closable?: boolean
  theme?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  icon?: string
  buttonLayout?: 'horizontal' | 'vertical'
  width?: string
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  show: false,
  title: '',
  titleColor: '#1e293b',
  content: '',
  contentColor: '#64748b',
  buttons: () => [
    { text: '取消' },
    { text: '确定', type: 'primary' }
  ],
  background: '#ffffff',
  borderRadius: 20,
  maskColor: '#000000',
  maskOpacity: 0.8,
  maskClosable: true,
  closable: false,
  theme: 'default',
  icon: '',
  buttonLayout: 'horizontal',
  width: '600rpx',
  duration: 200
})

const emit = defineEmits<{
  click: [event: { index: number; text: string; type?: string }]
  close: []
  closed: []
}>()

const visible = ref(false)
const isClosing = ref(false)

watch(
  () => props.show,
  (v) => {
    if (v) {
      isClosing.value = false
      visible.value = true
    } else if (visible.value) {
      isClosing.value = true
      setTimeout(() => {
        visible.value = false
        isClosing.value = false
        emit('closed')
      }, props.duration)
    }
  },
  { immediate: true }
)

const themeConfig = {
  default: { icon: '', color: '#6366f1', bg: 'rgba(99, 102, 241, 0.1)' },
  success: { icon: 'mdi:check-circle', color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' },
  warning: { icon: 'mdi:alert-circle', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' },
  danger: { icon: 'mdi:close-circle', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' },
  info: { icon: 'mdi:information', color: '#0ea5e9', bg: 'rgba(14, 165, 233, 0.1)' }
}

const iconName = computed(() => props.icon || themeConfig[props.theme]?.icon || '')
const iconColor = computed(() => themeConfig[props.theme]?.color || '#6366f1')
const iconWrapStyle = computed(() => ({
  background: themeConfig[props.theme]?.bg || 'rgba(99, 102, 241, 0.1)'
}))

const wrapperStyle = computed(() => ({
  '--z-dialog-duration': `${props.duration}ms`,
  zIndex: 9999
}))

const maskStyle = computed(() => ({
  '--mask-opacity': String(props.maskOpacity),
  background: props.maskColor
}))

const dialogStyle = computed(() => ({
  '--z-dialog-duration': `${props.duration}ms`,
  background: props.background,
  borderRadius: `${props.borderRadius}rpx`,
  width: props.width
}))

function getButtonStyle(button: DialogButton, index: number) {
  const isLast = index === props.buttons.length - 1
  const type = button.type || (isLast ? 'primary' : 'default')

  const colors: Record<string, { bg: string; border: string }> = {
    default: { bg: '#f1f5f9', border: 'transparent' },
    primary: { bg: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', border: 'transparent' },
    success: { bg: 'linear-gradient(135deg, #10b981 0%, #34d399 100%)', border: 'transparent' },
    warning: { bg: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)', border: 'transparent' },
    danger: { bg: 'linear-gradient(135deg, #ef4444 0%, #f87171 100%)', border: 'transparent' }
  }

  const config = colors[type] || colors.default
  return {
    background: config.bg
  }
}

function getButtonTextColor(button: DialogButton, index: number) {
  if (button.color) return button.color
  const isLast = index === props.buttons.length - 1
  const type = button.type || (isLast ? 'primary' : 'default')
  return type === 'default' ? '#475569' : '#ffffff'
}

function handleButtonClick(index: number) {
  const button = props.buttons[index]
  emit('click', {
    index,
    text: button.text,
    type: button.type
  })
}

function handleMaskClick() {
  if (!props.maskClosable) return
  close()
}

function close() {
  emit('close')
}
</script>

<style scoped>
.z-dialog-wrapper {
  position: fixed;
  z-index: 9999;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-dialog-mask {
  position: absolute;
  inset: 0;
  animation: fadeIn var(--z-dialog-duration, 200ms) ease forwards;
}

.z-dialog-mask.is-closing {
  animation: fadeOut var(--z-dialog-duration, 200ms) ease forwards;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: var(--mask-opacity, 0.3); }
}

@keyframes fadeOut {
  from { opacity: var(--mask-opacity, 0.3); }
  to { opacity: 0; }
}

.z-dialog {
  position: relative;
  z-index: 1;
  max-width: 90%;
  max-height: 80%;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 20rpx 60rpx rgba(0, 0, 0, 0.15);
  animation: scaleIn var(--z-dialog-duration, 200ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

.z-dialog.is-closing {
  animation: scaleOut var(--z-dialog-duration, 200ms) cubic-bezier(0.32, 0.72, 0, 1) forwards;
}

@keyframes scaleIn {
  from {
    transform: scale(0.9);
  }
  to {
    transform: scale(1);
  }
}

@keyframes scaleOut {
  from {
    transform: scale(1);
  }
  to {
    transform: scale(0.9);
  }
}

.z-dialog__close {
  position: absolute;
  right: 16rpx;
  top: 16rpx;
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  z-index: 1;
  transition: background 0.2s ease;
}

.z-dialog__close:active {
  background: rgba(0, 0, 0, 0.05);
}

.z-dialog__icon {
  display: flex;
  justify-content: center;
  padding-top: 40rpx;
}

.z-dialog__icon-wrap {
  width: 88rpx;
  height: 88rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-dialog__title {
  display: block;
  padding: 32rpx 40rpx 0;
  font-weight: 700;
  font-size: 34rpx;
  text-align: center;
  line-height: 1.4;
}

.z-dialog__content {
  padding: 20rpx 40rpx 32rpx;
}

.z-dialog__content.no-title {
  padding-top: 40rpx;
}

.z-dialog__text {
  display: block;
  font-size: 28rpx;
  text-align: center;
  line-height: 1.6;
}

.z-dialog__footer {
  display: flex;
  padding: 0 24rpx 24rpx;
  gap: 16rpx;
}

.z-dialog__footer.is-horizontal {
  flex-direction: row;
}

.z-dialog__footer.is-vertical {
  flex-direction: column;
}

.z-dialog__button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  height: 88rpx;
  border-radius: 14rpx;
  transition: all 0.2s ease;
}

.z-dialog__footer.is-vertical .z-dialog__button {
  flex: none;
}

.z-dialog__button:active {
  transform: scale(0.96);
  opacity: 0.9;
}

.z-dialog__button-icon {
  flex-shrink: 0;
}

.z-dialog__button-text {
  font-size: 30rpx;
  font-weight: 600;
  line-height: 1;
}
</style>
