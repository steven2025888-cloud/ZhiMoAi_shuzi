<template>
  <view
    class="z-avatar"
    :class="rootClass"
    :style="rootStyle"
    @tap="onTap"
  >
    <!-- content -->
    <view class="z-avatar__inner" :style="innerStyle">
      <image
        v-if="showImage"
        class="z-avatar__img"
        :src="props.src"
        :mode="props.mode"
        @error="onImgError"
        @load="onImgLoad"
      />
      <view v-else class="z-avatar__fallback" :style="fallbackStyle">
        <slot>
          <z-icon
            v-if="props.icon"
            :name="props.icon"
            :size="fallbackIconSize"
            :color="resolvedTextColor"
          />
          <text v-else class="z-avatar__txt" :style="textStyle">{{ displayText }}</text>
        </slot>
      </view>
    </view>

    <!-- badge -->
	
    <view
      v-if="showBadge"
      class="z-avatar__badge"
      :class="badgeClass"
      :style="badgeStyle"
    >
		<z-badge :value="props.badge" type="primary" :background="props.badgeBg" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type AvatarShape = 'circle' | 'rounded' | 'square'
type AvatarSize = 'xs' | 'sm' | 'md' | 'lg'
type BadgeType = 'dot' | 'text'

const props = withDefaults(defineProps<{
  /** image url */
  src?: string
  /** fallback text (usually name) */
  text?: string
  /** fallback icon (z-icon name) */
  icon?: string

  /** size preset or rpx number */
  size?: AvatarSize | number
  /** custom width/height (rpx/px/%) */
  width?: string | number
  height?: string | number

  /** shape */
  shape?: AvatarShape
  /** force radius when shape=rounded */
  radius?: string | number

  /** background / text color (for fallback) */
  bg?: string
  color?: string

  /** border */
  border?: boolean
  borderColor?: string
  borderWidth?: string | number

  /** ring (outer stroke) */
  ring?: boolean
  ringColor?: string
  ringWidth?: string | number

  /** shadow */
  shadow?: boolean

  /** badge */
  badge?: string | number
  badgeType?: BadgeType
  badgeBg?: string
  badgeColor?: string
  badgeSize?: string | number
  badgeOffsetX?: string | number
  badgeOffsetY?: string | number

  /** image mode */
  mode?: string

  /** disabled: no click */
  disabled?: boolean

  /** tag for events */
  tag?: any
}>(), {
  src: '',
  text: '',
  icon: '',

  size: 'md',
  width: '',
  height: '',

  shape: 'circle',
  radius: 16,

  bg: '#EEF2FF',
  color: '#465CFF',

  border: false,
  borderColor: 'rgba(0,0,0,0.10)',
  borderWidth: 2,

  ring: false,
  ringColor: 'rgba(70,92,255,0.22)',
  ringWidth: 6,

  shadow: false,

  badge: '',
  badgeType: 'dot',
  badgeBg: '#EF4444',
  badgeColor: '#FFFFFF',
  badgeSize: 24,
  badgeOffsetX: 0,
  badgeOffsetY: 0,

  mode: 'aspectFill',

  disabled: false,
  tag: 0
})

const emit = defineEmits<{
  (e: 'click', payload: { tag: any }): void
  (e: 'error', payload: { tag: any }): void
  (e: 'load', payload: { tag: any }): void
}>()

function toUnit(v: any, fallbackUnit = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${fallbackUnit}`
  return String(v)
}

const sizeMap: Record<AvatarSize, number> = {
  xs: 56,
  sm: 72,
  md: 92,
  lg: 120
}

const imgFailed = ref(false)
watch(() => props.src, () => { imgFailed.value = false })

const resolvedSize = computed(() => {
  if (typeof props.size === 'number') return props.size
  return sizeMap[props.size] ?? sizeMap.md
})

const resolvedW = computed(() => props.width !== '' ? toUnit(props.width) : `${resolvedSize.value}rpx`)
const resolvedH = computed(() => props.height !== '' ? toUnit(props.height) : `${resolvedSize.value}rpx`)

const resolvedRadius = computed(() => {
  if (props.shape === 'circle') return '9999rpx'
  if (props.shape === 'square') return '0rpx'
  return toUnit(props.radius)
})

const resolvedBg = computed(() => props.bg || '#EEF2FF')
const resolvedTextColor = computed(() => props.color || '#465CFF')

const showImage = computed(() => !!(props.src && !imgFailed.value))

const displayText = computed(() => {
  const t = (props.text || '').trim()
  if (!t) return 'A'
  // prefer first 2 chars (works for CN/EN)
  return t.length >= 2 ? t.slice(0, 2) : t.slice(0, 1)
})

const fallbackIconSize = computed(() => {
  const s = resolvedSize.value
  return Math.max(22, Math.floor(s * 0.46))
})

const rootClass = computed(() => [
  props.shadow ? 'z-avatar--shadow' : '',
  props.border ? 'z-avatar--border' : '',
  props.ring ? 'z-avatar--ring' : '',
  props.disabled ? 'z-avatar--disabled' : ''
].filter(Boolean))

const rootStyle = computed(() => {
  const bw = toUnit(props.borderWidth)
  const rw = toUnit(props.ringWidth)
  const ringPad = props.ring ? rw : '0rpx'

  // ring uses padding + background clip, safer than pseudo elements on some runtimes
  const style: Record<string, any> = {
    width: resolvedW.value,
    height: resolvedH.value,
    borderRadius: resolvedRadius.value,
    padding: ringPad,
    boxSizing: 'border-box',
    background: props.ring ? props.ringColor : 'transparent'
  }

  if (props.border) {
    style.borderWidth = bw || '2rpx'
    style.borderStyle = 'solid'
    style.borderColor = props.borderColor
  } else {
    style.borderWidth = '0'
  }

  return style
})

const innerStyle = computed(() => ({
  width: '100%',
  height: '100%',
  borderRadius: resolvedRadius.value,
  overflow: 'hidden',
  background: resolvedBg.value
}))

const fallbackStyle = computed(() => ({
  width: '100%',
  height: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: resolvedBg.value
}))

const textStyle = computed(() => {
  const s = resolvedSize.value
  const fs = Math.max(22, Math.floor(s * 0.34))
  return {
    fontSize: `${fs}rpx`,
    color: resolvedTextColor.value,
    fontWeight: 700,
    lineHeight: 1
  }
})

const showBadge = computed(() => {
  const v = props.badge
  if (v === '' || v === null || v === undefined) return false
  if (props.badgeType === 'dot') return true
  // text badge: allow 0 too
  return String(v).length > 0
})

const badgeIsText = computed(() => props.badgeType === 'text')

const badgeClass = computed(() => [
  props.badgeType === 'dot' ? 'z-avatar__badge--dot' : 'z-avatar__badge--text'
])

const badgeStyle = computed(() => {
  const s = toUnit(props.badgeSize) || '24rpx'
  const ox = toUnit(props.badgeOffsetX) || '0rpx'
  const oy = toUnit(props.badgeOffsetY) || '0rpx'

  // Calculate position based on whether there's a ring
  let rightPos = '0rpx'
  let topPos = '0rpx'

  if (props.ring) {
    rightPos = '0rpx'
    topPos = '0rpx'
  } else {
    rightPos = '-10rpx'
    topPos = '-20rpx'
  }

  const style: Record<string, any> = {
    right: ox !== '0rpx' ? `calc(${rightPos} + ${ox})` : rightPos,
    top: oy !== '0rpx' ? `calc(${topPos} + ${oy})` : topPos,
  }

  // 文本角标需要调整字体大小以适应圆形
  if (props.badgeType === 'text') {
    style.padding = '0'
  } else {
    style.padding = '0'
  }

  return style
})

const badgeTextStyle = computed(() => ({
  fontSize: '20rpx',  // 增大字体
  fontWeight: 700,
  color: props.badgeColor,
  lineHeight: 1,
  transform: 'scale(0.9)',  // 稍微缩小以确保文字不溢出
  whiteSpace: 'nowrap'
}))

function onTap() {
  if (props.disabled) return
  emit('click', { tag: props.tag })
}

function onImgError() {
  imgFailed.value = true
  emit('error', { tag: props.tag })
}

function onImgLoad() {
  emit('load', { tag: props.tag })
}
</script>

<style scoped>
.z-avatar{
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.z-avatar__inner{
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}

.z-avatar__img{
  width: 100%;
  height: 100%;
}

.z-avatar__fallback{
  box-sizing: border-box;
}

.z-avatar__txt{
  text-align: center;
}

.z-avatar--shadow{
  box-shadow: 0 14rpx 30rpx rgba(0,0,0,0.10);
}

.z-avatar--disabled{
  opacity: 0.55;
}

.z-avatar__badge{
  box-sizing: border-box;
  position: absolute;
  z-index: 2;
  /* #ifndef APP-NVUE */
  display: flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  /* #endif */
}

.z-avatar__badge--dot{
  padding: 0;
}

.z-avatar__badge--text{
  /* Ensure text badges have proper pill shape */
  /* #ifndef APP-NVUE */
  display: inline-flex;
  /* #endif */
}

.z-avatar__badge-txt{
  /* #ifndef APP-NVUE */
  display: block;
  white-space: nowrap;
  /* #endif */
}
</style>
