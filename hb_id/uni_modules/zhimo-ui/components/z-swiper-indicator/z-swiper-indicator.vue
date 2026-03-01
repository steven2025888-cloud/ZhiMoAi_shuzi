<template>
  <view class="z-si">
    <slot></slot>

    <!-- dots -->
    <view
      v-if="modeNum === 1"
      class="z-si__bar"
      :style="barStyle"
    >
      <view
        v-for="(_, index) in props.items"
        :key="index"
        class="z-si__dot"
        :class="{ 'z-si__dot--on': index === cur }"
        :style="dotStyle(index)"
        @tap.stop="onPick(index)"
      />
    </view>

    <!-- number -->
    <view
      v-else-if="modeNum === 2"
      class="z-si__bar"
      :style="barStyle"
    >
      <text
        v-for="(_, index) in props.items"
        :key="index"
        class="z-si__num"
        :class="{ 'z-si__num--on': index === cur }"
        :style="numStyle(index)"
        @tap.stop="onPick(index)"
      >{{ index + 1 }}</text>
    </view>

    <!-- title -->
    <view
      v-else-if="modeNum === 3"
      class="z-si__titlebar"
      :style="titleBarStyle"
    >
      <text
        class="z-si__title"
        :style="titleStyle"
        @tap.stop="onPick(cur)"
      >{{ titleText }}</text>
    </view>

    <!-- fraction -->
    <view
      v-else-if="modeNum === 4"
      class="z-si__fraction"
      :style="fractionStyle"
    >
      <text class="z-si__fraction-txt" :style="fractionTxtStyle" @tap.stop="onPick(cur)">
        {{ cur + 1 }}/{{ props.items.length }}
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, watchEffect } from 'vue'

type Mode = 1 | 2 | 3 | 4 | 'dot' | 'number' | 'title' | 'fraction'

type IndicatorStyle = {
  left?: number
  right?: number
  bottom?: number

  width?: number
  activeWidth?: number
  height?: number
  round?: boolean

  background?: string
  activeBackground?: string

  color?: string
  activeColor?: string
  size?: number

  margin?: number
  padding?: number

  /** only for title mode */
  barHeight?: number
}

const props = withDefaults(defineProps<{
  /** swiper items */
  items?: any[]
  /** current index from swiper */
  current?: number | string
  /** 1 dots / 2 number / 3 title / 4 fraction */
  mode?: Mode
  /** title field name in items */
  field?: string

  /** style options */
  styles?: IndicatorStyle

  /** when activeBackground empty, use this color for active state */
  primary?: string

  /** tag passthrough */
  tag?: any
}>(), {
  items: () => [],
  current: 0,
  mode: 1,
  field: 'title',
  styles: () => ({}),
  primary: '#465CFF',
  tag: 0
})

const emit = defineEmits<{
  (e: 'click', payload: { index: number }): void
}>()

function toNum(v: any, def = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : def
}

/** rpx->px to avoid border-radius deformation; fallback to rpx when unavailable */
function rpxToPxStr(rpx: number) {
  try {
    // @ts-ignore
    const px = uni && uni.upx2px ? uni.upx2px(rpx) : null
    if (typeof px === 'number') {
      const even = Math.floor(px) % 2 === 0 ? Math.floor(px) : Math.floor(px) + 1
      return `${even}px`
    }
  } catch (e) {}
  return `${rpx}rpx`
}

const cur = computed(() => {
  const max = Math.max(0, (props.items?.length || 0) - 1)
  const n = Math.max(0, Math.min(max, toNum(props.current, 0)))
  return n
})

const modeNum = computed(() => {
  const m = props.mode as any
  if (m === 'dot') return 1
  if (m === 'number') return 2
  if (m === 'title') return 3
  if (m === 'fraction') return 4
  return toNum(m, 1) as 1 | 2 | 3 | 4
})

const opt = computed(() => {
  // base defaults
  let primaryColor = props.primary
  // #ifdef APP-NVUE
  // Use default primary color for APP-NVUE
  if (!primaryColor) {
    primaryColor = '#465CFF'
  }
  // #endif

  const d: Required<IndicatorStyle> = {
    left: 0,
    right: 0,
    bottom: 28,

    width: 16,
    activeWidth: 16,
    height: 16,
    round: true,

    background: 'rgba(0,0,0,0.45)',
    activeBackground: '',

    color: '#FFFFFF',
    activeColor: '#FFFFFF',
    size: 28,

    margin: 8,
    padding: 28,
    barHeight: 80
  }
  return { ...d, ...(props.styles || {}), __primary: primaryColor } as any
})

const dotW = computed(() => rpxToPxStr(opt.value.width))
const dotAW = computed(() => rpxToPxStr(opt.value.activeWidth))
const dotH = computed(() => rpxToPxStr(opt.value.height))
const radius = computed(() => rpxToPxStr(opt.value.round ? opt.value.width : 0))

const barStyle = computed(() => ({
  left: `${opt.value.left}rpx`,
  right: `${opt.value.right}rpx`,
  bottom: `${opt.value.bottom}rpx`
}))

const titleBarStyle = computed(() => ({
  left: `${opt.value.left}rpx`,
  right: `${opt.value.right}rpx`,
  bottom: `${opt.value.bottom}rpx`,
  height: `${Math.max(64, opt.value.barHeight)}rpx`,
  background: opt.value.background,
  paddingLeft: `${opt.value.padding}rpx`,
  paddingRight: `${opt.value.padding}rpx`
}))

const fractionStyle = computed(() => ({
  right: `${opt.value.right}rpx`,
  bottom: `${opt.value.bottom}rpx`
}))

function activeBg() {
  return opt.value.activeBackground || opt.value.__primary
}

function dotStyle(index: number) {
  const on = index === cur.value
  return {
    width: on ? dotAW.value : dotW.value,
    height: dotH.value,
    borderRadius: opt.value.round ? radius.value : '0',
    background: on ? activeBg() : opt.value.background,
    marginLeft: `${opt.value.margin}rpx`,
    marginRight: `${opt.value.margin}rpx`
  }
}

function numStyle(index: number) {
  const on = index === cur.value
  return {
    width: dotW.value,
    height: dotH.value,
    borderRadius: opt.value.round ? radius.value : '0',
    background: on ? activeBg() : opt.value.background,
    marginLeft: `${opt.value.margin}rpx`,
    marginRight: `${opt.value.margin}rpx`,
    color: on ? opt.value.activeColor : opt.value.color,
    fontSize: `${opt.value.size}rpx`
  }
}

const titleText = computed(() => {
  const items = props.items || []
  const it = items[cur.value]
  if (!it) return ''
  const f = props.field || 'title'
  const t = it && it[f] != null ? it[f] : ''
  return String(t || '')
})

const titleStyle = computed(() => ({
  fontSize: `${opt.value.size}rpx`,
  color: opt.value.color
}))

const fractionTxtStyle = computed(() => ({
  width: dotW.value,
  height: dotH.value,
  borderTopLeftRadius: opt.value.round ? radius.value : '0',
  borderBottomLeftRadius: opt.value.round ? radius.value : '0',
  background: opt.value.background,
  color: opt.value.color,
  fontSize: `${opt.value.size}rpx`
}))

function onPick(index: number) {
  emit('click', { index })
}
</script>

<style scoped>
.z-si{
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex: 1;
  flex-direction: column;
  position: relative;
  overflow: hidden;
}

.z-si__bar,
.z-si__titlebar,
.z-si__fraction{
  position: absolute;
  /* #ifndef APP-NVUE */
  display:flex;
  box-sizing: border-box;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  z-index: 2;
  overflow: hidden;
}

.z-si__dot,
.z-si__num{
  /* #ifndef APP-NVUE */
  flex-shrink: 0;
  display:flex;
  box-sizing: border-box;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.z-si__title{
  flex: 1;
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  display:block;
  white-space: nowrap;
  /* #endif */
  overflow: hidden;
  text-overflow: ellipsis;
}

.z-si__fraction-txt{
  /* #ifndef APP-NVUE */
  display:flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  text-align: center;
}
</style>
