<template>
  <view
    class="z-alert"
    :class="[ `z-alert--${type}`, `z-alert--${variant}`, disabled ? 'z-alert--disabled' : '' ]"
    :style="wrapStyle"
  >
    <!-- left / icon area -->
    <view class="z-alert__left" @tap.stop="onIconAreaTap">
      <slot name="left">
        <view v-if="showIcon" class="z-alert__icon">
          <z-icon :name="resolvedIcon" :size="iconSize" :color="resolvedIconColor" />
        </view>
      </slot>
    </view>

    <!-- content -->
    <view class="z-alert__main" :class="[{ 'z-alert__main--pad-left': padLeft, 'z-alert__main--pad-right': closable }]">
      <view class="z-alert__text" @tap.stop="onBodyTap">
        <text v-if="title" class="z-alert__title" :style="titleStyle">{{ title }}</text>
        <text
          v-if="desc"
          class="z-alert__desc"
          :class="[ singleLine ? 'z-alert__desc--single' : '' ]"
          :style="descStyle"
        >{{ desc }}</text>
        <slot name="content" />
      </view>
    </view>

    <!-- right slot -->
    <view class="z-alert__right">
      <slot name="right" />
    </view>

    <!-- close -->
    <view v-if="closable" class="z-alert__close" :class="{ 'z-alert__close--with-desc': !!desc }" @tap.stop="onCloseTap">
      <z-icon :name="closeIcon" :size="closeSize" :color="resolvedCloseColor" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type AlertType = 'info' | 'success' | 'warning' | 'error'
type AlertVariant = 'solid' | 'soft' | 'outline'

const props = withDefaults(defineProps<{
  type?: AlertType
  variant?: AlertVariant

  title?: string
  desc?: string

  /** background color (overrides type color) */
  background?: string
  /** text color (overrides default) */
  color?: string
  /** desc color (overrides default) */
  descColor?: string

  /** icon */
  showIcon?: boolean
  icon?: string
  iconColor?: string
  iconSize?: number

  /** close */
  closable?: boolean
  closeIcon?: string
  closeColor?: string
  closeSize?: number

  /** layout */
  radius?: string
  padding?: string | (string | number)[]
  marginTop?: string | number
  marginBottom?: string | number
  /** when true, add a small gap between custom left slot and content */
  spacing?: boolean
  /** desc single line ellipsis */
  singleLine?: boolean

  /** disabled: no click / close */
  disabled?: boolean

  /** tag: return in events */
  tag?: any
}>(), {
  type: 'info',
  variant: 'solid',

  title: '',
  desc: '',

  background: '',
  color: '',
  descColor: '',

  showIcon: true,
  icon: '',
  iconColor: '',
  iconSize: 22,

  closable: false,
  closeIcon: 'mdi:close',
  closeColor: '',
  closeSize: 22,

  radius: '16rpx',
  padding: '20rpx 32rpx',
  marginTop: 0,
  marginBottom: 0,
  spacing: false,
  singleLine: false,

  disabled: false,
  tag: 0
})

const emit = defineEmits<{
  (e: 'click', payload: { tag: any }): void
  (e: 'iconClick', payload: { tag: any }): void
  (e: 'close', payload: { tag: any }): void
}>()

const typeColor = computed(() => {
  const map: Record<AlertType, string> = {
    info: '#465CFF',
    success: '#09BE4F',
    warning: '#FFB703',
    error: '#FF2B2B'
  }
  return map[props.type]
})

const bgColor = computed(() => {
  if (props.background) return props.background
  if (props.variant === 'solid') return typeColor.value
  if (props.variant === 'soft') return hexToRgba(typeColor.value, 0.12)
  return 'transparent'
})

const borderColor = computed(() => {
  if (props.variant === 'outline') return typeColor.value
  return 'transparent'
})

const resolvedTextColor = computed(() => {
  if (props.color) return props.color
  if (props.variant === 'solid') return '#ffffff'
  return typeColor.value
})

const resolvedDescColor = computed(() => {
  if (props.descColor) return props.descColor
  if (props.variant === 'solid') return 'rgba(255,255,255,0.92)'
  return 'rgba(0,0,0,0.62)'
})

const resolvedIcon = computed(() => {
  if (props.icon) return props.icon
  const map: Record<AlertType, string> = {
    info: 'mdi:information',
    success: 'mdi:check-circle',
    warning: 'mdi:alert',
    error: 'mdi:close-circle'
  }
  return map[props.type]
})

const resolvedIconColor = computed(() => {
  if (props.iconColor) return props.iconColor
  if (props.variant === 'solid') return '#ffffff'
  return typeColor.value
})

const resolvedCloseColor = computed(() => {
  if (props.closeColor) return props.closeColor
  if (props.variant === 'solid') return 'rgba(255,255,255,0.95)'
  return 'rgba(0,0,0,0.62)'
})

const padLeft = computed(() => props.spacing || props.showIcon || !!props.icon || !!slots.left)

const wrapStyle = computed(() => {
  const pad = normalizePadding(props.padding)
  return {
    background: bgColor.value,
    borderRadius: props.radius,
    borderWidth: props.variant === 'outline' ? '1px' : '0px',
    borderStyle: 'solid',
    borderColor: borderColor.value,
    paddingTop: pad[0],
    paddingRight: pad[1],
    paddingBottom: pad[2],
    paddingLeft: pad[3],
    marginTop: toRpxOrPx(props.marginTop),
    marginBottom: toRpxOrPx(props.marginBottom),
    opacity: props.disabled ? 0.7 : 1
  } as any
})

const titleStyle = computed(() => ({
  color: resolvedTextColor.value
}))

const descStyle = computed(() => ({
  color: resolvedDescColor.value
}))

function onBodyTap() {
  if (props.disabled) return
  emit('click', { tag: props.tag })
}
function onIconAreaTap() {
  if (props.disabled) return
  emit('iconClick', { tag: props.tag })
}
function onCloseTap() {
  if (props.disabled) return
  emit('close', { tag: props.tag })
}

/** helpers */
function normalizePadding(p: any): [string, string, string, string] {
  // string "20rpx 32rpx"
  if (typeof p === 'string') {
    const parts = p.trim().split(/\s+/).filter(Boolean)
    if (parts.length === 1) return [parts[0], parts[0], parts[0], parts[0]]
    if (parts.length === 2) return [parts[0], parts[1], parts[0], parts[1]]
    if (parts.length === 3) return [parts[0], parts[1], parts[2], parts[1]]
    return [parts[0], parts[1], parts[2], parts[3]]
  }
  // array: [top,right,bottom,left] or [top,right]
  const arr = Array.isArray(p) ? p : []
  const top = arr[0] != null ? String(arr[0]) : '0'
  const right = arr[1] != null ? String(arr[1]) : '0'
  const bottom = arr[2] != null ? String(arr[2]) : top
  const left = arr[3] != null ? String(arr[3]) : right
  return [top, right, bottom, left]
}

function toRpxOrPx(v: any) {
  if (v == null || v === '') return '0'
  const s = String(v)
  if (s.endsWith('rpx') || s.endsWith('px') || s.endsWith('%')) return s
  // default rpx for numeric-like values (as in original)
  if (/^\d+(\.\d+)?$/.test(s)) return s + 'rpx'
  return s
}

function hexToRgba(hex: string, a = 1) {
  const h = hex.replace('#', '').trim()
  const full = h.length === 3 ? h.split('').map(x => x + x).join('') : h
  const n = parseInt(full, 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  return `rgba(${r},${g},${b},${a})`
}
</script>

<style scoped>
.z-alert{
  /* #ifndef APP-NVUE */
  display:flex;
  width:100%;
  box-sizing:border-box;
  /* #endif */
  flex-direction:row;
  align-items:center;
  position:relative;
}

.z-alert__left{
  /* #ifndef APP-NVUE */
  flex-shrink:0;
  display:flex;
  align-items:center;
  justify-content:center;
  /* #endif */
}

.z-alert__icon{
  /* #ifndef APP-NVUE */
  display:flex;
  align-items:center;
  justify-content:center;
  /* #endif */
}

.z-alert__main{
  flex:1;
  flex-direction:column;
  /* #ifndef APP-NVUE */
  overflow:hidden;
  /* #endif */
}

.z-alert__main--pad-left{ padding-left: 20rpx; }
.z-alert__main--pad-right{ padding-right: 56rpx; }

.z-alert__text{
  flex-direction:column;
  /* #ifndef APP-NVUE */
  display:block;
  width:100%;
  box-sizing:border-box;
  /* #endif */
}

.z-alert__title{
  font-size: 28rpx;
  font-weight: 700;
  /* #ifndef APP-NVUE */
  display:block;
  word-break: break-all;
  /* #endif */
}
.z-alert__desc{
  font-size: 24rpx;
  margin-top: 6rpx;
  /* #ifndef APP-NVUE */
  display:block;
  word-break: break-all;
  /* #endif */
}

.z-alert__desc--single{
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  width:100%;
  white-space: nowrap;
  overflow:hidden;
  text-overflow: ellipsis;
  /* #endif */
}

.z-alert__right{
  /* #ifndef APP-NVUE */
  flex-shrink:0;
  display:flex;
  align-items:center;
  justify-content:center;
  /* #endif */
}

.z-alert__close{
  position:absolute;
  right: 24rpx;
  top: 18rpx;
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}
.z-alert__close--with-desc{ top: 16rpx; }

.z-alert--disabled{
  /* #ifndef APP-NVUE */
  filter: saturate(0.9);
  /* #endif */
}
</style>
