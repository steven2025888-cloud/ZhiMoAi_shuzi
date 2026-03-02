<template>
  <view class="z-timeline" :style="wrapStyle">
    <view
      v-for="(item, index) in itemsSafe"
      :key="getKey(item, index)"
      class="z-timeline__row"
    >
      <!-- left side (split / alternate) -->
      <view
        v-if="showLeft(index)"
        class="z-timeline__left"
        :style="{ width: toRpx(leftWidth) }"
      >
        <slot name="left" :item="item" :index="index">
          <view v-if="item.time" class="z-timeline__time">{{ item.time }}</view>
        </slot>
      </view>
      <view v-else-if="mode !== 'right'" class="z-timeline__left" :style="{ width: toRpx(leftWidth) }" />

      <!-- node column -->
      <view class="z-timeline__node-col" :style="{ width: toRpx(nodeWidth) }">
        <!-- line (behind dot, extends through row) -->
        <view
          v-if="shouldShowLine(index)"
          class="z-timeline__line"
          :class="{
            'z-timeline__line--first': index === 0,
            'z-timeline__line--last': index === itemsSafe.length - 1
          }"
          :style="lineStyle(item, index)"
        />
        <!-- dot (on top of line) -->
        <view class="z-timeline__dot-wrap" :style="{ width: toRpx(nodeWidth) }">
          <view class="z-timeline__dot-hit" @tap="onNodeTap(item, index)">
            <slot name="dot" :item="item" :index="index" :active="isActive(index)">
              <view class="z-timeline__dot" :style="dotStyle(item, index)">
                <text v-if="showNumber" class="z-timeline__dot-number" :style="dotNumberStyle(item, index)">
                  {{ index + 1 }}
                </text>
              </view>
            </slot>
          </view>
        </view>
      </view>

      <!-- right side -->
      <view class="z-timeline__right">
        <view v-if="isAlternate && index % 2 === 1" class="z-timeline__alt-spacer" />
        <slot name="right" :item="item" :index="index" :active="isActive(index)">
          <view class="z-timeline__content" :style="contentStyle(item, index)" @tap="onItemTap(item, index)">
            <view class="z-timeline__title" :style="titleStyle(item, index)">
              {{ item.title || item.text || ('节点 ' + (index + 1)) }}
            </view>
            <view v-if="item.desc" class="z-timeline__desc">{{ item.desc }}</view>
            <view v-if="item.extra" class="z-timeline__extra">{{ item.extra }}</view>
          </view>
        </slot>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type TimelineItem = {
  key?: string | number
  title?: string
  text?: string
  desc?: string
  extra?: string
  time?: string
  color?: string // active or highlight color for this item
  lineColor?: string
  dotBg?: string
  dotBorder?: string
  dotBorderWidth?: number | string
}

const props = defineProps({
  items: { type: Array as any, default: () => [] },

  /** right: only show right content; split: left + right; alternate: left/right alternate */
  mode: { type: String, default: 'right' },

  /** highlight nodes <= active */
  active: { type: Number, default: -1 },

  /** padding can be number/string (rpx/px) or array like [t,r,b,l] */
  padding: { type: [Array, Number, String] as any, default: () => [] },

  background: { type: String, default: 'transparent' },

  /** for split/alternate mode */
  leftWidth: { type: [Number, String], default: 200 },

  /** node column width */
  nodeWidth: { type: [Number, String], default: 48 },

  lineWidth: { type: [Number, String], default: 2 },
  lineColor: { type: String, default: '#E5E7EB' },
  activeColor: { type: String, default: '#465CFF' },

  dotSize: { type: [Number, String], default: 20 },
  dotBg: { type: String, default: '' },
  dotBorderColor: { type: String, default: '' },
  dotBorderWidth: { type: [Number, String], default: 3 },

  /** filled dot style (solid color) vs hollow (white bg with border) */
  dotFilled: { type: Boolean, default: false },

  /** show number inside dot */
  showNumber: { type: Boolean, default: false },

  /** content styling */
  contentBorder: { type: Boolean, default: true },
  contentFontSize: { type: [Number, String], default: 32 },
  contentColor: { type: String, default: '' },

  clickable: { type: Boolean, default: false },
  tag: { type: [String, Number, Object] as any, default: 0 }
})

const emit = defineEmits<{
  (e: 'node-click', payload: { item: TimelineItem; index: number; tag: any }): void
  (e: 'item-click', payload: { item: TimelineItem; index: number; tag: any }): void
  (e: 'change', payload: { active: number; tag: any }): void
}>()

const itemsSafe = computed<TimelineItem[]>(() => Array.isArray(props.items) ? props.items : [])

const isAlternate = computed(() => props.mode === 'alternate')
const isSplit = computed(() => props.mode === 'split')

function toRpx(v: any): string {
  if (v === 0) return '0'
  if (v == null || v === '') return '0'
  if (typeof v === 'number') return `${v}rpx`
  const s = String(v).trim()
  if (/(rpx|px|%|vw|vh)$/.test(s)) return s
  // treat plain numeric strings as rpx
  if (/^\d+(\.\d+)?$/.test(s)) return `${s}rpx`
  return s
}

function normPadding(p: any): string {
  if (Array.isArray(p)) {
    const t = p[0] ?? 0
    const r = p[1] ?? 0
    const b = p[2] ?? p[0] ?? 0
    const l = p[3] ?? p[1] ?? 0
    return `${toRpx(t)} ${toRpx(r)} ${toRpx(b)} ${toRpx(l)}`
  }
  return toRpx(p)
}

const wrapStyle = computed(() => ({
  background: props.background,
  padding: normPadding(props.padding)
}))

function getKey(item: TimelineItem, index: number) {
  return item?.key ?? `${index}`
}

function isActive(index: number) {
  return props.active >= 0 && index <= props.active
}

function showLeft(index: number) {
  if (isSplit.value) return true
  if (isAlternate.value) return index % 2 === 1
  return false
}

function shouldShowLine(index: number) {
  // Need at least 2 items to show any line
  if (itemsSafe.value.length < 2) return false

  // Always show all lines (color will differ based on active state)
  return true
}

function lineStyle(item: TimelineItem, index: number) {
  // Line at node i connects node i to node i+1
  // Line should be active color only if we've COMPLETED this segment
  // When active is N, we've reached node N, so lines 0 to N-1 are completed
  // Therefore: line is blue if index < active (not index <= active)
  const active = props.active >= 0 && index < props.active
  const color = item?.lineColor || (active ? props.activeColor : props.lineColor)
  const width = typeof props.lineWidth === 'number' ? `${props.lineWidth}rpx` : String(props.lineWidth)

  return {
    background: color,
    width: width
  }
}

function dotStyle(item: TimelineItem, index: number) {
  const active = isActive(index)
  const color = item?.color || props.activeColor

  // Determine background based on dotFilled prop
  let bg: string
  if (item?.dotBg) {
    bg = item.dotBg
  } else if (props.dotFilled) {
    // Filled style: active dots use color, inactive use gray
    bg = active ? color : '#D1D5DB'
  } else {
    // Hollow style: always white background
    bg = '#FFFFFF'
  }

  const bd = item?.dotBorder || (active ? color : '#D1D5DB')
  const bdw = item?.dotBorderWidth ?? props.dotBorderWidth

  return {
    width: toRpx(props.dotSize),
    height: toRpx(props.dotSize),
    background: bg,
    borderColor: bd,
    borderWidth: typeof bdw === 'number' ? `${bdw}rpx` : String(bdw)
  }
}

function dotNumberStyle(item: TimelineItem, index: number) {
  const active = isActive(index)
  const color = item?.color || props.activeColor

  // For filled dots, use white text; for hollow dots, use colored text
  let textColor: string
  if (props.dotFilled) {
    textColor = active ? '#FFFFFF' : '#6B7280'
  } else {
    textColor = active ? color : '#9CA3AF'
  }

  return {
    color: textColor
  }
}

function contentStyle(item: TimelineItem, index: number) {
  const style: any = {}
  if (!props.contentBorder) {
    style.border = 'none'
    style.boxShadow = 'none'
  }
  return style
}

function titleStyle(item: TimelineItem, index: number) {
  const active = isActive(index)
  const color = props.contentColor || (item?.color ? (active ? item.color : '#111827') : (active ? props.activeColor : '#111827'))
  const fontSize = typeof props.contentFontSize === 'number' ? `${props.contentFontSize}rpx` : String(props.contentFontSize)

  return {
    color: color,
    fontSize: fontSize
  }
}

function onNodeTap(item: TimelineItem, index: number) {
  emit('node-click', { item, index, tag: props.tag })
  if (props.clickable) {
    emit('change', { active: index, tag: props.tag })
  }
}

function onItemTap(item: TimelineItem, index: number) {
  emit('item-click', { item, index, tag: props.tag })
}
</script>

<style scoped>
.z-timeline {
  width: 100%;
  box-sizing: border-box;
}

.z-timeline__row {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  position: relative;
}

.z-timeline__left {
  flex-shrink: 0;
  box-sizing: border-box;
  padding-top: 4rpx;
}

.z-timeline__node-col {
  position: relative;
  flex-shrink: 0;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.z-timeline__line {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  top: 0;
  bottom: 0;
  z-index: 1;
}

.z-timeline__line--first {
  top: 18rpx;
}

.z-timeline__line--last {
  bottom: auto;
  height: 18rpx;
}

.z-timeline__dot-wrap {
  display: flex;
  flex-direction: row;
  justify-content: center;
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.z-timeline__dot-hit {
}

.z-timeline__dot {
  border-style: solid;
  border-radius: 50%;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
  /* #ifndef APP-NVUE */
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  /* #endif */
}

.z-timeline__dot-number {
  font-size: 24rpx;
  font-weight: 600;
  line-height: 1;
}

.z-timeline__dot:active {
  /* #ifndef APP-NVUE */
  transform: scale(0.95);
  /* #endif */
}

.z-timeline__right {
  flex: 1;
  box-sizing: border-box;
  padding-top: 4rpx;
}

.z-timeline__content {
  padding-left: 20rpx;
  padding-right: 20rpx;
  padding-bottom: 48rpx;
  box-sizing: border-box;
  background: #FFFFFF;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 32rpx;
  margin-left: 20rpx;
  /* #ifndef APP-NVUE */
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.06);
  border: 1rpx solid #F3F4F6;
  transition: all 0.3s ease;
  /* #endif */
}

.z-timeline__content:hover {
  /* #ifndef APP-NVUE */
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.1);
  transform: translateY(-2rpx);
  /* #endif */
}

.z-timeline__title {
  font-size: 32rpx;
  line-height: 40rpx;
  font-weight: 700;
  margin-bottom: 8rpx;
}

.z-timeline__desc {
  font-size: 28rpx;
  line-height: 40rpx;
  padding-top: 8rpx;
  color: #6B7280;
}

.z-timeline__extra {
  font-size: 24rpx;
  line-height: 36rpx;
  padding-top: 8rpx;
  color: #9CA3AF;
  padding: 12rpx 16rpx;
  background: #F9FAFB;
  border-radius: 8rpx;
  margin-top: 12rpx;
}

.z-timeline__time {
  font-size: 28rpx;
  line-height: 36rpx;
  text-align: right;
  padding-right: 20rpx;
  color: #6B7280;
  font-weight: 600;
}

.z-timeline__alt-spacer {
  height: 0;
}
</style>
