<template>
  <!-- Wrapper mode: if there is default slot, act as a badge container -->
  <view v-if="hasSlot" class="z-badge-host" :style="hostStyle">
    <slot />
    <text
      v-if="visible"
      class="z-badge"
      :class="badgeClass"
      :style="badgeStyle"
      @tap="onTap"
    >{{ dot ? '' : displayText }}</text>
  </view>

  <!-- Standalone mode -->
  <text
    v-else
    v-if="visible"
    class="z-badge"
    :class="badgeClass"
    :style="standaloneStyle"
    @tap="onTap"
  >{{ dot ? '' : displayText }}</text>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'

type BadgeType = 'primary' | 'success' | 'warning' | 'danger' | 'purple' | 'white' | 'neutral' | 'gradient-red' | 'gradient-blue' | 'gradient-purple' | 'gradient-green'
type BadgeSize = 'small' | 'medium' | 'large'
type BadgeAnimation = 'none' | 'pulse' | 'bounce' | 'shake' | 'glow'

const props = withDefaults(defineProps<{
  /** Badge value */
  value?: string | number
  /** When value is number and max > -1, display as "max+" */
  max?: string | number
  /** Preset color type */
  type?: BadgeType
  /** Custom background color (overrides type) */
  background?: string
  /** Text color */
  color?: string
  /** Dot mode (no text) */
  dot?: boolean
  /** Hide badge */
  hidden?: boolean
  /** Show when value is 0 */
  showZero?: boolean
  /** Show even when value is empty string */
  showEmpty?: boolean
  /** Absolute positioning (mainly used in wrapper mode) */
  absolute?: boolean
  top?: string
  right?: string
  /** Extra offset in rpx (works in both wrapper + standalone) */
  marginTop?: number | string
  marginLeft?: number | string
  marginRight?: number | string
  /** Scale ratio */
  scale?: number
  /** Z-index */
  zIndex?: number | string
  /** Only for standalone: render as block/inline */
  inline?: boolean
  /** Size variant */
  size?: BadgeSize
  /** Border style */
  bordered?: boolean
  /** Border color */
  borderColor?: string
  /** Shadow effect */
  shadow?: boolean
  /** Animation effect */
  animation?: BadgeAnimation
  /** Bold text */
  bold?: boolean
  /** Ribbon style */
  ribbon?: boolean
}>(), {
  value: '',
  max: -1,
  type: 'danger',
  background: '',
  color: '#FFFFFF',
  dot: false,
  hidden: false,
  showZero: false,
  showEmpty: false,
  absolute: false,
  top: '-8rpx',
  right: '-18rpx',
  marginTop: 0,
  marginLeft: 0,
  marginRight: 0,
  scale: 1,
  zIndex: 10,
  inline: true,
  size: 'medium',
  bordered: false,
  borderColor: '#FFFFFF',
  shadow: false,
  animation: 'none',
  bold: true,
  ribbon: false
})

const emit = defineEmits<{
  (e: 'click'): void
}>()

const slots = useSlots()
const hasSlot = computed(() => !!slots.default)

const isNvue = (() => {
  let v = false
  // #ifdef APP-NVUE
  v = true
  // #endif
  return v
})()

const num = computed(() => {
  const v = Number(props.value)
  return Number.isFinite(v) ? v : NaN
})

const displayText = computed(() => {
  const max = Number(props.max)
  const n = num.value
  if (!Number.isFinite(n) || max === -1) return String(props.value ?? '')
  return n > max ? `${max}+` : String(n)
})

const hasText = computed(() => {
  if (props.dot) return false
  const raw = props.value
  const txt = displayText.value
  if (txt === '' || txt == null) return !!props.showEmpty
  if (raw === 0 || raw === '0') return !!props.showZero
  return true
})

const visible = computed(() => {
  if (props.hidden) return false
  return props.dot || hasText.value
})

const badgeClass = computed(() => {
  return [
    props.dot ? 'z-badge--dot' : 'z-badge--pill',
    props.background ? '' : `z-badge--${props.type}`,
    `z-badge--${props.size}`,
    props.bordered ? 'z-badge--bordered' : '',
    props.shadow ? 'z-badge--shadow' : '',
    props.animation !== 'none' ? `z-badge--${props.animation}` : '',
    props.ribbon ? 'z-badge--ribbon' : ''
  ]
})

const bgColor = computed(() => {
  if (props.background) return props.background
  // #ifndef APP-NVUE
  // Use CSS variables on non-nvue for theme override
  return ''
  // #endif
  // #ifdef APP-NVUE
  const colors: Record<string, string> = {
    primary: '#465CFF',
    success: '#09BE4F',
    warning: '#FFB703',
    danger: '#FF2B2B',
    purple: '#6831FF',
    white: '#FFFFFF',
    neutral: '#64748B',
    'gradient-red': 'linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%)',
    'gradient-blue': 'linear-gradient(135deg, #667EEA 0%, #764BA2 100%)',
    'gradient-purple': 'linear-gradient(135deg, #A855F7 0%, #EC4899 100%)',
    'gradient-green': 'linear-gradient(135deg, #10B981 0%, #059669 100%)'
  }
  return colors[props.type] || colors.danger
  // #endif
})

const basePositionStyle = computed(() => ({
  marginTop: `${props.marginTop}rpx`,
  marginLeft: `${props.marginLeft}rpx`,
  marginRight: `${props.marginRight}rpx`,
  zIndex: props.zIndex as any
}))

const scaleStyle = computed(() => {
  const s = props.scale
  if (s === 1) return {}
  // zoom is not reliable, use transform for all
  return {
    transform: `scale(${s})`,
    transformOrigin: 'center center'
  } as any
})

const badgeStyle = computed(() => ({
  ...basePositionStyle.value,
  color: props.color,
  background: bgColor.value || undefined,
  top: props.absolute ? props.top : 'auto',
  right: props.absolute ? props.right : 'auto',
  position: props.absolute ? 'absolute' : 'relative',
  borderColor: props.bordered ? props.borderColor : 'transparent',
  fontWeight: props.bold ? '600' : '400',
  ...scaleStyle.value
}))

const standaloneStyle = computed(() => {
  // If absolute is true, respect the absolute positioning even in standalone mode
  if (props.absolute) {
    return {
      ...badgeStyle.value,
      display: props.inline ? 'inline-flex' : 'flex'
    }
  }
  // Otherwise, use relative positioning for normal standalone usage
  return {
    ...badgeStyle.value,
    position: 'relative',
    top: 'auto',
    right: 'auto',
    display: props.inline ? 'inline-flex' : 'flex'
  }
})

const hostStyle = computed(() => ({
  position: 'relative',
  display: 'inline-flex',
  alignItems: 'center'
}))

function onTap() {
  emit('click')
}
</script>

<style scoped>
.z-badge-host{
  position: relative;
  display: inline-flex;
  align-items: center;
}

/* base */
.z-badge{
  box-sizing: border-box;
  font-weight: 600;
  text-align: center;
  z-index: 10;
  transition: all 0.3s ease;
  /* #ifndef APP-NVUE */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  /* #endif */
}

/* pill */
.z-badge--pill{
  height: 36rpx;
  min-width: 36rpx;
  padding: 0 12rpx;
  font-size: 24rpx;
  line-height: 36rpx;
  border-radius: 999px;
}

/* dot */
.z-badge--dot{
  width: 16rpx;
  height: 16rpx;
  border-radius: 999px;
}

/* Size variants */
.z-badge--small.z-badge--pill{
  height: 28rpx;
  min-width: 28rpx;
  padding: 0 8rpx;
  font-size: 20rpx;
  line-height: 28rpx;
}

.z-badge--small.z-badge--dot{
  width: 12rpx;
  height: 12rpx;
}

.z-badge--medium.z-badge--pill{
  height: 36rpx;
  min-width: 36rpx;
  padding: 0 12rpx;
  font-size: 24rpx;
  line-height: 36rpx;
}

.z-badge--medium.z-badge--dot{
  width: 16rpx;
  height: 16rpx;
}

.z-badge--large.z-badge--pill{
  height: 44rpx;
  min-width: 44rpx;
  padding: 0 16rpx;
  font-size: 28rpx;
  line-height: 44rpx;
}

.z-badge--large.z-badge--dot{
  width: 20rpx;
  height: 20rpx;
}

/* Border style */
.z-badge--bordered{
  border: 2rpx solid;
}

/* Shadow effect */
.z-badge--shadow{
  /* #ifndef APP-NVUE */
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.15);
  /* #endif */
}

/* Ribbon style */
.z-badge--ribbon{
  border-radius: 8rpx 8rpx 8rpx 0;
  /* #ifndef APP-NVUE */
  position: relative;
  /* #endif */
}

/* Animations */
/* #ifndef APP-NVUE */
@keyframes badge-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.9;
  }
}

@keyframes badge-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6rpx);
  }
}

@keyframes badge-shake {
  0%, 100% {
    transform: translateX(0);
  }
  25% {
    transform: translateX(-4rpx);
  }
  75% {
    transform: translateX(4rpx);
  }
}

@keyframes badge-glow {
  0%, 100% {
    box-shadow: 0 0 8rpx currentColor;
  }
  50% {
    box-shadow: 0 0 20rpx currentColor;
  }
}

.z-badge--pulse{
  animation: badge-pulse 2s ease-in-out infinite;
}

.z-badge--bounce{
  animation: badge-bounce 1s ease-in-out infinite;
}

.z-badge--shake{
  animation: badge-shake 0.5s ease-in-out infinite;
}

.z-badge--glow{
  animation: badge-glow 2s ease-in-out infinite;
}
/* #endif */

/* Presets (non-nvue uses CSS vars, nvue uses inline background) */
/* #ifndef APP-NVUE */
.z-badge--primary{ background-color: var(--z-color-primary, #465CFF); }
.z-badge--success{ background-color: var(--z-color-success, #09BE4F); }
.z-badge--warning{ background-color: var(--z-color-warning, #FFB703); }
.z-badge--danger{ background-color: var(--z-color-danger, #FF2B2B); }
.z-badge--purple{ background-color: var(--z-color-purple, #6831FF); }
.z-badge--neutral{ background-color: var(--z-color-text-2, #64748B); }
.z-badge--white{ background-color: #FFFFFF; color: var(--z-color-danger, #FF2B2B); border: 1px solid rgba(0,0,0,.06); }

/* Gradient types */
.z-badge--gradient-red{ background: linear-gradient(135deg, #FF6B6B 0%, #EE5A6F 100%); }
.z-badge--gradient-blue{ background: linear-gradient(135deg, #667EEA 0%, #764BA2 100%); }
.z-badge--gradient-purple{ background: linear-gradient(135deg, #A855F7 0%, #EC4899 100%); }
.z-badge--gradient-green{ background: linear-gradient(135deg, #10B981 0%, #059669 100%); }
/* #endif */

/* #ifdef APP-NVUE */
.z-badge--white{ background-color: #FFFFFF; color: #FF2B2B; }
/* #endif */
</style>
