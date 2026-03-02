<template>
  <view
    class="z-tag"
    :class="rootClass"
    :style="rootStyle"
    @tap="onTap"
  >
    <!-- left icon / dot -->
    <view v-if="showLeft" class="z-tag__left" :style="leftStyle">
      <z-icon v-if="props.icon" :name="props.icon" :size="iconPx" :color="resolvedIconColor" />
      <view v-else class="z-tag__dot" :style="dotStyle" />
    </view>

    <!-- text / default slot -->
    <text
      v-if="hasText"
      class="z-tag__text"
      :class="{ 'z-ellipsis-1': props.ellipsis }"
      :style="textStyle"
    >{{ props.text }}</text>
    <view v-else class="z-tag__slot" :style="slotStyle">
      <slot />
    </view>

    <!-- right close -->
    <view
      v-if="props.closable"
      class="z-tag__close"
      :class="{ 'z-tag__close--disabled': props.disabled }"
      @tap.stop="onCloseTap($event)"
    >
      <z-icon :name="props.closeIcon" :size="closePx" :color="resolvedCloseColor" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type TagTone = 'primary' | 'success' | 'warning' | 'danger' | 'purple' | 'neutral'
type TagVariant = 'solid' | 'soft' | 'outline' | 'text'
type TagSize = 'xs' | 'sm' | 'md' | 'lg'

const props = withDefaults(defineProps<{
  /** text content; if empty, render default slot */
  text?: string

  /** tone color */
  tone?: TagTone
  /** visual style */
  variant?: TagVariant
  /** size preset */
  size?: TagSize

  /** custom colors (override) */
  bg?: string
  color?: string
  borderColor?: string

  /** border on/off (useful for solid/soft too) */
  bordered?: boolean
  borderWidth?: number | string

  /** radius rpx */
  radius?: number | string
  /** padding: css-like [t,r,b,l] (rpx string/number) or string */
  padding?: string | (string | number)[]
  /** scale for compact label */
  scale?: number
  /** transform origin */
  origin?: 'left' | 'center' | 'right'

  /** click feedback */
  highlight?: boolean
  /** single line ellipsis */
  ellipsis?: boolean

  /** left icon or dot */
  showLeft?: boolean
  icon?: string
  iconSize?: number
  iconColor?: string
  dot?: boolean

  /** close */
  closable?: boolean
  closeIcon?: string
  closeSize?: number
  closeColor?: string

  /** disabled */
  disabled?: boolean

  /** spacing */
  gap?: number

  /** margin */
  marginTop?: number | string
  marginRight?: number | string
  marginBottom?: number | string
  marginLeft?: number | string

  /** event tag/index */
  tag?: any
  index?: number
}>(), {
  text: '',
  tone: 'primary',
  variant: 'solid',
  size: 'md',

  bg: '',
  color: '',
  borderColor: '',

  bordered: true,
  borderWidth: 2,

  radius: 10,
  padding: '',
  scale: 1,
  origin: 'center',

  highlight: true,
  ellipsis: true,

  showLeft: false,
  icon: '',
  iconSize: 22,
  iconColor: '',
  dot: true,

  closable: false,
  closeIcon: 'mdi:close',
  closeSize: 22,
  closeColor: '',

  disabled: false,

  gap: 10,

  marginTop: 0,
  marginRight: 0,
  marginBottom: 0,
  marginLeft: 0,

  tag: 0,
  index: 0
})

const emit = defineEmits<{
  (e: 'click', payload: { index: number; tag: any }): void
  (e: 'close', payload: { index: number; tag: any }): void
}>()

function stop(e: any) {
  if (e && typeof e.stopPropagation === 'function') e.stopPropagation()
  if (e && typeof e.preventDefault === 'function') e.preventDefault()
}

function toUnit(v: any, u = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${u}`
  return String(v)
}

function normalizePadding(p: any, fallback: string): string {
  if (!p) return fallback
  if (typeof p === 'string') return p
  if (!Array.isArray(p)) return fallback
  const a = p.map((x) => (typeof x === 'number' ? `${x}rpx` : String(x)))
  if (a.length === 1) return a[0]
  if (a.length === 2) return `${a[0]} ${a[1]}`
  if (a.length === 3) return `${a[0]} ${a[1]} ${a[2]}`
  return `${a[0]} ${a[1]} ${a[2]} ${a[3]}`
}

const toneMap = computed<Record<TagTone, string>>(() => ({
  primary: 'var(--z-color-primary, #465CFF)',
  success: 'var(--z-color-success, #16A34A)',
  warning: 'var(--z-color-warning, #D97706)',
  danger: 'var(--z-color-danger, #DC2626)',
  purple: 'var(--z-color-purple, #7C3AED)',
  neutral: 'var(--z-color-text, #0F172A)'
}))

function hexToRgbStr(hex: string) {
  const h = hex.replace('#', '').trim()
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h
  const n = parseInt(full, 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `${r}, ${g}, ${b}`
}

function resolveCssColorToSoft(c: string) {
  // if it's a css var, we can't convert; fall back to a neutral soft bg
  if (c.includes('var(')) return 'rgba(0,0,0,0.06)'
  if (c.startsWith('#') && (c.length === 4 || c.length === 7)) return `rgba(${hexToRgbStr(c)}, 0.10)`
  // already rgba/other
  return 'rgba(0,0,0,0.06)'
}

const baseTone = computed(() => toneMap.value[props.tone])

const resolvedBg = computed(() => {
  if (props.bg) return props.bg
  if (props.variant === 'solid') return baseTone.value
  if (props.variant === 'soft') return resolveCssColorToSoft(baseTone.value)
  return 'transparent'
})

const resolvedColor = computed(() => {
  if (props.color) return props.color
  if (props.variant === 'solid') return '#FFFFFF'
  if (props.variant === 'text') return baseTone.value
  return baseTone.value
})

const resolvedBorder = computed(() => {
  if (props.borderColor) return props.borderColor
  if (props.variant === 'soft') return resolvedBg.value
  return baseTone.value
})

const resolvedIconColor = computed(() => props.iconColor || resolvedColor.value)
const resolvedCloseColor = computed(() => props.closeColor || resolvedColor.value)

const sizeCfg = computed(() => {
  switch (props.size) {
    case 'xs': return { fs: 22, pad: '10rpx 18rpx', radius: 8, icon: 20 }
    case 'sm': return { fs: 24, pad: '12rpx 22rpx', radius: 9, icon: 20 }
    case 'lg': return { fs: 26, pad: '16rpx 28rpx', radius: 12, icon: 24 }
    default:   return { fs: 24, pad: '14rpx 24rpx', radius: 10, icon: 22 }
  }
})

const hasText = computed(() => !!(props.text && String(props.text).trim().length > 0))
const showLeft = computed(() => props.showLeft && (props.icon || props.dot))
const iconPx = computed(() => props.iconSize || sizeCfg.value.icon)
const closePx = computed(() => props.closeSize || sizeCfg.value.icon)

const rootClass = computed(() => [
  `z-tag--${props.tone}`,
  `z-tag--${props.variant}`,
  `z-tag--${props.size}`,
  props.highlight ? 'z-tag--highlight' : '',
  props.disabled ? 'z-tag--disabled' : '',
  props.closable ? 'z-tag--closable' : ''
].filter(Boolean))

const rootStyle = computed(() => {
  const pad = normalizePadding(props.padding, sizeCfg.value.pad)
  const radius = props.radius !== '' ? toUnit(props.radius) : `${sizeCfg.value.radius}rpx`
  const bw = toUnit(props.borderWidth)

  const style: Record<string, any> = {
    background: resolvedBg.value,
    color: resolvedColor.value,
    borderRadius: radius,
    padding: pad,
    transform: `scale(${props.scale})`,
    transformOrigin: props.origin === 'left' ? '0 center' : props.origin === 'right' ? '100% center' : '50% center',
    marginTop: toUnit(props.marginTop),
    marginRight: toUnit(props.marginRight),
    marginBottom: toUnit(props.marginBottom),
    marginLeft: toUnit(props.marginLeft),
    opacity: props.disabled ? 0.6 : 1
  }

  if (props.bordered && props.variant !== 'text') {
    style.borderStyle = 'solid'
    style.borderColor = resolvedBorder.value
    // #ifdef APP-NVUE
    style.borderWidth = '0.5px'
    // #endif
    // #ifndef APP-NVUE
    style.borderWidth = bw || '2rpx'
    // #endif
  } else {
    style.borderWidth = '0'
  }

  if (props.variant === 'text') {
    style.padding = '0'
  }

  return style
})

const leftStyle = computed(() => ({
  marginRight: `${props.gap}rpx`,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
}))

const dotStyle = computed(() => ({
  width: '14rpx',
  height: '14rpx',
  borderRadius: '9999rpx',
  background: resolvedIconColor.value,
  opacity: props.variant === 'solid' ? 0.9 : 0.85
}))

const textStyle = computed(() => ({
  fontSize: `${sizeCfg.value.fs}rpx`,
  lineHeight: `${sizeCfg.value.fs}rpx`,
  color: resolvedColor.value,
  fontWeight: 500
}))

const slotStyle = computed(() => ({
  display: 'flex',
  alignItems: 'center'
}))

function onTap() {
  if (props.disabled) return
  emit('click', { index: props.index, tag: props.tag })
}

function onCloseTap(e?: any) {
  stop(e)
  if (props.disabled) return
  emit('close', { index: props.index, tag: props.tag })
}
</script>

<style scoped>
.z-tag{
  /* #ifndef APP-NVUE */
  display: inline-flex;
  box-sizing: border-box;
  flex-shrink: 0;
  max-width: 100%;
  white-space: nowrap;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.z-tag__text{
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  white-space: nowrap;
  /* #endif */
  overflow: hidden;
  text-overflow: ellipsis;
}

.z-ellipsis-1{
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.z-tag__close{
  margin-left: 10rpx;
  padding: 6rpx;
  border-radius: 999rpx;
  opacity: 0.95;
}

.z-tag__close--disabled{
  opacity: 0.6;
}

.z-tag--disabled{
  pointer-events: none;
}

.z-tag--highlight:active{
  opacity: 0.55;
}
</style>
