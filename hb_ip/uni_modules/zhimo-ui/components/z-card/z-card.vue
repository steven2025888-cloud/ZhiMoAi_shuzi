<template>
  <view
    class="z-card"
    :class="{
      'z-card--full': full,
      'z-card--border': showBorder
    }"
    :style="wrapStyle"
    @tap="onTap"
  >
    <!-- Cover: big image (top) -->
    <view v-if="cover && coverPlacement === 'top'" class="z-card__cover-wrap">
  <image
    class="z-card__cover"
    :src="cover"
    :mode="coverMode"
    :style="coverStyleTop"
  />
  <view v-if="hasCoverOverlay" class="z-card__cover-overlay" :style="coverOverlayStyle">
    <slot name="cover-overlay">
      <view class="z-card__cover-overlay-inner" :style="coverOverlayInnerStyle">
        <text
          v-if="coverOverlayText"
          class="z-card__cover-overlay-title"
          :style="coverOverlayTextStyle"
        >{{ coverOverlayText }}</text>
        <text
          v-if="coverOverlaySubtext"
          class="z-card__cover-overlay-sub"
          :style="coverOverlaySubtextStyle"
        >{{ coverOverlaySubtext }}</text>
      </view>
    </slot>
  </view>
</view>
    <view
      v-if="tag || title || src"
      class="z-card__header"
      :class="{ 'z-card__divider': headerLine }"
      :style="headerStyle"
    >
      <view class="z-card__header-left">
        <image
          v-if="src"
          class="z-card__thumb"
          :src="src"
          :style="thumbStyle"
          mode="aspectFill"
        />
        <text v-if="title" class="z-card__title" :style="titleStyle">{{ title }}</text>
      </view>

      <view v-if="tag" class="z-card__header-right">
        <text class="z-card__tag" :style="tagStyle">{{ tag }}</text>
      </view>
    </view>

    <!-- Cover: big image (after header) -->
    <view v-if="cover && coverPlacement === 'afterHeader'" class="z-card__cover-wrap">
  <image
    class="z-card__cover"
    :src="cover"
    :mode="coverMode"
    :style="coverStyleAfterHeader"
  />
  <view v-if="hasCoverOverlay" class="z-card__cover-overlay" :style="coverOverlayStyle">
    <slot name="cover-overlay">
      <view class="z-card__cover-overlay-inner" :style="coverOverlayInnerStyle">
        <text
          v-if="coverOverlayText"
          class="z-card__cover-overlay-title"
          :style="coverOverlayTextStyle"
        >{ coverOverlayText }</text>
        <text
          v-if="coverOverlaySubtext"
          class="z-card__cover-overlay-sub"
          :style="coverOverlaySubtextStyle"
        >{ coverOverlaySubtext }</text>
      </view>
    </slot>
  </view>
</view>

    <view class="z-card__body" :class="{ 'z-card__divider': footerLine }">
      <slot />
    </view>

    <view class="z-card__footer" :style="footerStyle">
      <slot name="footer" />
    </view>

    <!-- Cover: big image (bottom) -->
    <view v-if="cover && coverPlacement === 'bottom'" class="z-card__cover-wrap">
  <image
    class="z-card__cover"
    :src="cover"
    :mode="coverMode"
    :style="coverStyleBottom"
  />
  <view v-if="hasCoverOverlay" class="z-card__cover-overlay" :style="coverOverlayStyle">
    <slot name="cover-overlay">
      <view class="z-card__cover-overlay-inner" :style="coverOverlayInnerStyle">
        <text
          v-if="coverOverlayText"
          class="z-card__cover-overlay-title"
          :style="coverOverlayTextStyle"
        >{ coverOverlayText }</text>
        <text
          v-if="coverOverlaySubtext"
          class="z-card__cover-overlay-sub"
          :style="coverOverlaySubtextStyle"
        >{ coverOverlaySubtext }</text>
      </view>
    </slot>
  </view>
</view>
  </view>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const emit = defineEmits(['click'])

const props = defineProps({
  /** card margin: [top, right, bottom, left] */
  margin: { type: Array, default: () => ['0', '0'] },
  /** header padding: [top, right, bottom, left] */
  padding: { type: Array, default: () => ['20rpx', '20rpx'] },

  full: { type: Boolean, default: false },
  /** full 模式下，突破父级 padding 的偏移量（如父级 padding: 20px，则设为 '20px'） */
  fullOffset: { type: String, default: '0' },

  background: { type: String, default: '#fff' },
  headerBackground: { type: String, default: '#fff' },

  radius: { type: String, default: '16rpx' },

  /** nvue box shadow */
  shadow: { type: String, default: '0 2rpx 4rpx 0 rgba(2, 4, 38, 0.05)' },

  showBorder: { type: Boolean, default: false },
  borderColor: { type: String, default: '#E5E7EB' },

  headerLine: { type: Boolean, default: true },
  footerLine: { type: Boolean, default: false },
  /** nvue divider color */
  lineColor: { type: String, default: '#E5E7EB' },

  src: { type: String, default: '' },

  /** big cover image */
  cover: { type: String, default: '' },
  /** cover placement: top | afterHeader | bottom */
  coverPlacement: { type: String, default: 'afterHeader' },
  /** cover height */
  coverHeight: { type: [Number, String], default: 320 },
  /** cover image mode */
  coverMode: { type: String, default: 'aspectFill' },

  /** cover overlay title */
  coverOverlayText: { type: String, default: '' },
  /** cover overlay subtitle */
  coverOverlaySubtext: { type: String, default: '' },
  /** cover overlay height */
  coverOverlayHeight: { type: [Number, String], default: 120 },
  /** cover overlay padding */
  coverOverlayPadding: { type: [Number, String], default: 24 },
  /** cover overlay align: left | center | right */
  coverOverlayAlign: { type: String, default: 'left' },
  /** cover overlay background: css color or gradient */
  coverOverlayBg: { type: String, default: 'linear-gradient(to top, rgba(0,0,0,.9), rgba(0,0,0,0))' },
  /** cover overlay title color */
  coverOverlayTextColor: { type: String, default: '#fff' },
  /** cover overlay subtitle color */
  coverOverlaySubtextColor: { type: String, default: 'rgba(255,255,255,0.85)' },

  width: { type: [Number, String], default: 64 },
  height: { type: [Number, String], default: 64 },
  imageRadius: { type: String, default: '8rpx' },

  title: { type: String, default: '' },
  size: { type: [Number, String], default: 30 },
  color: { type: String, default: '#7F7F7F' },

  tag: { type: String, default: '' },
  tagSize: { type: [Number, String], default: 24 },
  tagColor: { type: String, default: '#b2b2b2' },

  index: { type: Number, default: 0 }
})

/** nvue flag (compile-time) */
const isNvue = (() => {
  let v = false
  // #ifdef APP-NVUE
  v = true
  // #endif
  return v
})
const slots = useSlots()

const hasCoverOverlay = computed(() => {
  return !!(slots['cover-overlay'] || props.coverOverlayText || props.coverOverlaySubtext)
})

const coverOverlayStyle = computed(() => {
  const bg = (props.coverOverlayBg || '').trim()
  const isGradient = bg.startsWith('linear-gradient')
  return {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: toUnit(props.coverOverlayHeight, 'rpx'),
    display: 'flex',
    alignItems: 'flex-end',
    pointerEvents: 'none',

    backgroundImage: isGradient ? bg : 'none',
    backgroundColor: isGradient ? 'transparent' : (bg || 'rgba(0,0,0,.55)'),
  }
})


const coverOverlayInnerStyle = computed(() => ({
  paddingLeft: toUnit(props.coverOverlayPadding, 'rpx'),
  paddingRight: toUnit(props.coverOverlayPadding, 'rpx'),
  paddingBottom: toUnit(props.coverOverlayPadding, 'rpx'),
  textAlign: props.coverOverlayAlign
}))

const coverOverlayTextStyle = computed(() => ({
  color: props.coverOverlayTextColor,
  fontSize: '30rpx',
  fontWeight: 600
}))

const coverOverlaySubtextStyle = computed(() => ({
  marginTop: '8rpx',
  color: props.coverOverlaySubtextColor,
  fontSize: '24rpx',
  marginLeft:'20rpx'
}))


function normalizeBox(arr, fallback = ['0', '0', '0', '0']) {
  if (!Array.isArray(arr) || arr.length === 0) return fallback
  const a = arr.map(v => (v == null || v === '' ? null : String(v)))
  if (a.length === 1) return [a[0] ?? fallback[0], a[0] ?? fallback[1], a[0] ?? fallback[2], a[0] ?? fallback[3]]
  if (a.length === 2) return [a[0] ?? fallback[0], a[1] ?? fallback[1], a[0] ?? fallback[2], a[1] ?? fallback[3]]
  if (a.length === 3) return [a[0] ?? fallback[0], a[1] ?? fallback[1], a[2] ?? fallback[2], a[1] ?? fallback[3]]
  return [
    a[0] ?? fallback[0],
    a[1] ?? fallback[1],
    a[2] ?? fallback[2],
    a[3] ?? fallback[3]
  ]
}

function toUnit(v, unit = 'rpx') {
  if (v == null) return `0${unit}`
  const s = String(v).trim()
  if (s === '') return `0${unit}`
  // already has unit
  if (/[a-z%]+$/i.test(s)) return s
  // numeric string
  if (/^-?\d+(\.\d+)?$/.test(s)) return `${s}${unit}`
  return s
}

const margin4 = computed(() => normalizeBox(props.margin, ['0', '0', '0', '0']))
const padding4 = computed(() => normalizeBox(props.padding, ['20rpx', '20rpx', '20rpx', '20rpx']))

const cardRadius = computed(() => (props.full ? '0' : props.radius))

const wrapStyle = computed(() => {
  const [mt, mr, mb, ml] = margin4.value
  const radius = cardRadius.value

  // 应用上下左右 margin
  const style = {
    marginTop: mt || 0,
    marginBottom: mb || mt || 0,
    marginLeft: ml || mr || 0,
    marginRight: mr || 0,

    background: props.background,
    borderRadius: radius,
    boxSizing: 'border-box',

    // share radius to pseudo elements
    '--z-card-radius': radius,
    '--z-card-border': isNvue ? props.borderColor : 'var(--z-color-border, #EEEEEE)',
    '--z-card-divider': isNvue ? props.lineColor : 'var(--z-color-border, #EEEEEE)',

    boxShadow: props.showBorder ? 'none' : props.shadow,
    borderColor: isNvue ? props.borderColor : 'transparent'
  }

  // full：左右 margin 失效，使用负 margin 突破父级 padding
  if (props.full) {
    const offset = props.fullOffset || '0'
    // 如果有 fullOffset，使用负 margin 突破父级 padding
    const negativeOffset = offset === '0' ? 0 : `-${offset}`

    Object.assign(style, {
      marginLeft: negativeOffset,
      marginRight: negativeOffset,
      borderRadius: 0
    })
  }

  return style
})

const headerStyle = computed(() => {
  const [pt, pr, pb, pl] = padding4.value
  const topRadius = props.cover && props.coverPlacement === 'top' ? '0' : cardRadius.value
  return {
    background: props.headerBackground,
    paddingTop: pt || 0,
    paddingRight: pr || 0,
    paddingBottom: pb || pt || 0,
    paddingLeft: pl || pr || 0,
    borderTopLeftRadius: topRadius,
    borderTopRightRadius: topRadius,
    borderBottomColor: isNvue && props.headerLine ? props.lineColor : 'transparent'
  }
})

const footerStyle = computed(() => {
  // if cover is at bottom, footer is no longer the last element
  const bottomRadius = props.cover && props.coverPlacement === 'bottom' ? '0' : cardRadius.value
  return {
    borderBottomLeftRadius: bottomRadius,
    borderBottomRightRadius: bottomRadius
  }
})

const coverBase = computed(() => ({
  width: '100%',
  height: toUnit(props.coverHeight, 'rpx')
}))

const coverStyleTop = computed(() => ({
  ...coverBase.value,
  borderTopLeftRadius: cardRadius.value,
  borderTopRightRadius: cardRadius.value,
  borderBottomLeftRadius: '0',
  borderBottomRightRadius: '0'
}))

const coverStyleAfterHeader = computed(() => ({
  ...coverBase.value,
  borderRadius: '0'
}))

const coverStyleBottom = computed(() => ({
  ...coverBase.value,
  borderTopLeftRadius: '0',
  borderTopRightRadius: '0',
  borderBottomLeftRadius: cardRadius.value,
  borderBottomRightRadius: cardRadius.value
}))

const thumbStyle = computed(() => ({
  width: toUnit(props.width, 'rpx'),
  height: toUnit(props.height, 'rpx'),
  borderRadius: props.imageRadius
}))

const titleStyle = computed(() => ({
  fontSize: toUnit(props.size, 'rpx'),
  color: props.color
}))

const tagStyle = computed(() => ({
  fontSize: toUnit(props.tagSize, 'rpx'),
  color: props.tagColor
}))

function onTap() {
  emit('click', { index: props.index })
}
</script>

<style scoped>
.z-card {
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
  overflow: hidden;
}

.z-card--full {
  /* #ifndef APP-NVUE */
  border-radius: 0 !important;
  /* #endif */
}

.z-card--border {
  position: relative;
  box-shadow: none !important;
  /* #ifdef APP-NVUE */
  border-width: 0.5px;
  border-style: solid;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-card--border::after {
  content: ' ';
  position: absolute;
  height: 200%;
  width: 200%;
  border: 1px solid var(--z-card-border, #EEEEEE);
  transform-origin: 0 0;
  -webkit-transform-origin: 0 0;
  -webkit-transform: scale(0.5);
  transform: scale(0.5);
  left: 0;
  top: 0;
  border-radius: calc(var(--z-card-radius, 16rpx) * 2);
  box-sizing: border-box;
  pointer-events: none;
}
/* #endif */

.z-card__header {
  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  box-sizing: border-box;
  overflow: hidden;
  /* #endif */
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.z-card__header-left {
  /* #ifndef APP-NVUE */
  display: flex;
  white-space: nowrap;
  /* #endif */
  flex-direction: row;
  align-items: center;
}

.z-card__divider {
  position: relative;
  /* #ifdef APP-NVUE */
  border-bottom-width: 0.5px;
  border-bottom-style: solid;
  border-bottom-color: #EEEEEE;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-card__divider::after {
  content: '';
  position: absolute;
  border-bottom: 1px solid var(--z-card-divider, #EEEEEE);
  -webkit-transform: scaleY(0.5);
  transform: scaleY(0.5);
  transform-origin: 0 100%;
  bottom: 0;
  right: 0;
  left: 0;
  pointer-events: none;
}
/* #endif */

.z-card__thumb {
  /* #ifndef APP-NVUE */
  vertical-align: middle;
  flex-shrink: 0;
  /* #endif */
  margin-right: 20rpx;
}

.z-card__cover {
  /* #ifndef APP-NVUE */
  display: block;
  /* #endif */
  width: 100%;
}

.z-card__title {
  /* #ifndef APP-NVUE */
  display: inline-block;
  vertical-align: middle;
  max-width: 380rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  /* #endif */
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
}

.z-card__header-right {
  text-align: right;
  /* #ifndef APP-NVUE */
  flex-shrink: 0;
  /* #endif */
}

.z-card__body {
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  width: 100%;
  box-sizing: border-box;
  /* #endif */
}

.z-card__footer {
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  width: 100%;
  box-sizing: border-box;
  /* #endif */
}

.z-card__cover-wrap{
  position: relative;
  width: 100%;
}
.z-card__cover-overlay{
  pointer-events: none;
}
.z-card__cover-overlay-inner{
  width: 100%;
  box-sizing: border-box;
}
.z-card__cover-overlay-title,
.z-card__cover-overlay-sub{
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
}

</style>
