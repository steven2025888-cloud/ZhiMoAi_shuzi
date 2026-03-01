<template>
  <view class="z-list__wrap" :style="{ marginTop: toRpx(marginTop) }">
    <!-- Title -->
    <view
      v-if="title"
      class="z-list__title"
      :style="{
        paddingTop: titlePad.top,
        paddingRight: titlePad.right,
        paddingBottom: titlePad.bottom,
        paddingLeft: titlePad.left,
        background: titleBackground
      }"
    >
      <text :style="{ color: titleColor, fontSize: toRpx(titleSize) }">{{ title }}</text>
    </view>

    <!-- Container -->
    <view class="z-list__container">
      <view
        v-if="topBorder"
        class="z-list__border-top"
        :class="{ 'z-list__border-default': !borderColor }"
        :style="{ background: borderColor || undefined, left: toRpx(topLeft), right: toRpx(topRight) }"
      />

      <!-- Cells (items mode) -->
      <view v-if="items && items.length">
        <view
          v-for="(it, idx) in items"
          :key="it.key ?? it.id ?? idx"
          class="z-cell"
          :class="{
            'z-cell--press': getHighlight(it),
            'z-cell--bg-default': !getBackground(it)
          }"
          :style="cellInlineStyle(it)"
          @tap="onTap(it, idx)"
        >
          <!-- cell top divider (absolute, no layout shift) -->
          <view
            v-if="!!it.topBorder"
            class="z-cell__border-top"
            :class="{ 'z-list__border-default': !getBorderColor(it) }"
            :style="{ background: getBorderColor(it) || undefined, left: toRpx(it.topLeft ?? 0), right: toRpx(it.topRight ?? 0) }"
          />
          <!-- cell bottom divider (absolute, no layout shift) -->
          <view
            v-if="getBottomBorder(it, idx)"
            class="z-cell__border-bottom"
            :class="{ 'z-list__border-default': !getBorderColor(it) }"
            :style="{ background: getBorderColor(it) || undefined, left: toRpx(getBottomLeft(it)), right: toRpx(it.bottomRight ?? 0) }"
          />

          <!-- content -->
          <slot name="cell" :item="it" :index="idx">
            <view class="z-cell__left">
              <image v-if="it.icon" class="z-cell__icon" :src="it.icon" mode="widthFix" />
              <view class="z-cell__texts">
                <text class="z-cell__title">{{ it.title ?? '' }}</text>
                <text v-if="it.desc" class="z-cell__desc">{{ it.desc }}</text>
              </view>
            </view>

            <view class="z-cell__right">
              <text v-if="it.rightText" class="z-cell__right-text">{{ it.rightText }}</text>

              <view v-if="it.badge !== undefined && it.badge !== null && String(it.badge).length"
                    class="z-badge"
                    :class="{ 'z-badge--dot': isDotBadge(it), 'z-badge--circle': isCircleBadge(it) }">
                <text class="z-badge__text">{{ badgeText(it) }}</text>
              </view>

              <view v-if="!!it.arrow" class="z-cell__arrow" :style="{ borderColor: getArrowColor(it) }" />
            </view>
          </slot>

        </view>
      </view>

      <!-- Slot mode (advanced): if you want fully custom children -->
      <slot v-else />
    </view>

    <!-- Footer -->
    <view
      v-if="footer"
      class="z-list__footer"
      :style="{
        paddingTop: footerPad.top,
        paddingRight: footerPad.right,
        paddingBottom: footerPad.bottom,
        paddingLeft: footerPad.left
      }"
    >
      <text :style="{ color: footerColor, fontSize: toRpx(footerSize) }">{{ footer }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

defineOptions({ name: 'z-list' })

const emit = defineEmits(['cellClick', 'click'])

const props = defineProps({
  /** list margin-top（rpx） */
  marginTop: { type: [Number, String], default: 0 },

  /** title */
  title: { type: String, default: '' },
  titleColor: { type: String, default: '#7F7F7F' },
  titleSize: { type: [Number, String], default: 28 },
  /** title padding: [top,right,bottom,left] */
  titlePadding: { type: Array, default: () => ['32rpx', '32rpx', '20rpx', '32rpx'] },
  titleBackground: { type: String, default: 'transparent' },

  /** footer */
  footer: { type: String, default: '' },
  footerColor: { type: String, default: '#7F7F7F' },
  footerSize: { type: [Number, String], default: 28 },
  footerPadding: { type: Array, default: () => ['20rpx', '32rpx', '0', '32rpx'] },

  /** list borders */
  topBorder: { type: Boolean, default: true },
  bottomBorder: { type: Boolean, default: false },
  borderColor: {
    type: String,
    // #ifdef APP-NVUE
    default: '#EEEEEE'
    // #endif
    // #ifndef APP-NVUE
    default: ''
    // #endif
  },
  topLeft: { type: [Number, String], default: 0 },
  topRight: { type: [Number, String], default: 0 },
  bottomLeft: { type: [Number, String], default: 0 },
  bottomRight: { type: [Number, String], default: 0 },

  /** items mode: render cells automatically */
  items: { type: Array, default: () => [] },

  /** defaults for cell (when item doesn't provide) */
  cellPadding: { type: Array, default: () => [] },          // [] -> use default ['32rpx','32rpx']
  cellBackground: { type: String, default: '' },            // '' -> use CSS var default
  cellHighlight: { type: Boolean, default: true },
  cellArrowColor: { type: String, default: '' },
  cellBorderColor: { type: String, default: '' },
  cellBottomLeft: { type: [Number, String], default: -1 },  // -1 -> default 32
})

function toRpx(v) {
  if (v == null || v === '') return '0'
  if (typeof v === 'number') return `${v}rpx`
  const s = String(v).trim()
  if (/(rpx|px|rem|em|vh|vw|%)$/.test(s)) return s
  if (/^-?\d+(\.\d+)?$/.test(s)) return `${s}rpx`
  return s
}

function normalizePad(arr, fallback) {
  const a = Array.isArray(arr) && arr.length ? arr : fallback
  const top = a[0] ?? 0
  const right = a[1] ?? 0
  const bottom = a[2] ?? a[0] ?? 0
  const left = a[3] ?? a[1] ?? 0
  return { top: top || 0, right: right || 0, bottom: bottom || 0, left: left || 0 }
}

const titlePad = computed(() => normalizePad(props.titlePadding, ['32rpx', '32rpx', '20rpx', '32rpx']))
const footerPad = computed(() => normalizePad(props.footerPadding, ['20rpx', '32rpx', '0', '32rpx']))

function getPadding(it) {
  const p = it?.padding
  // item padding priority > list cellPadding > default
  if (Array.isArray(p) && p.length) return p
  if (Array.isArray(props.cellPadding) && props.cellPadding.length) return props.cellPadding
  return ['32rpx', '32rpx']
}

function getBackground(it) {
  // #ifdef APP-NVUE
  // nvue default bg should be white to avoid transparent issues
  const nvDefault = '#fff'
  // #endif
  // #ifndef APP-NVUE
  const nvDefault = ''
  // #endif
  const bg = it?.background
  if (bg !== undefined && bg !== null && String(bg).length) return bg
  if (props.cellBackground) return props.cellBackground
  return nvDefault
}

function getHighlight(it) {
  return it?.highlight !== undefined ? !!it.highlight : props.cellHighlight
}

function getArrowColor(it) {
  return it?.arrowColor || props.cellArrowColor || '#B2B2B2'
}

function getBorderColor(it) {
  // #ifdef APP-NVUE
  let c = it?.borderColor ?? props.cellBorderColor
  if (!c || c === true) c = '#EEEEEE'
  return c
  // #endif
  // #ifndef APP-NVUE
  return it?.borderColor || props.cellBorderColor || ''
  // #endif
}

function getBottomLeft(it) {
  const left = it?.bottomLeft
  if (left !== undefined && left !== null) {
    if (left === -1) return 32
    return left
  }
  if (props.cellBottomLeft === -1) return 32
  return props.cellBottomLeft
}

function getBottomBorder(it, idx) {
  // item bottomBorder has highest priority
  if (it?.bottomBorder !== undefined) return !!it.bottomBorder
  // default: show divider except last item
  return idx < props.items.length - 1
}

function cellInlineStyle(it) {
  const pad = normalizePad(getPadding(it), ['32rpx', '32rpx'])
  const bg = getBackground(it)
  return {
    paddingTop: pad.top || 0,
    paddingRight: pad.right || 0,
    paddingBottom: pad.bottom || pad.top || 0,
    paddingLeft: pad.left || pad.right || 0,
    background: bg || undefined,
    marginTop: toRpx(it?.marginTop ?? 0),
    marginBottom: toRpx(it?.marginBottom ?? 0),
    borderRadius: it?.radius ?? '0'
  }
}

function onTap(it, idx) {
  if (it?.disabled) return
  const payload = { item: it, index: idx }
  emit('cellClick', payload)
  emit('click', payload) // compatible name
}

/** badge helpers */
function isDotBadge(it) {
  // if badge is true or 'dot' -> dot
  return it?.badge === true || it?.badge === 'dot'
}
function badgeText(it) {
  if (isDotBadge(it)) return ''
  return String(it.badge)
}
function isCircleBadge(it) {
  const t = badgeText(it)
  return t.length === 1
}
</script>

<style scoped>
/* ========== List ========== */
.z-list__wrap {
  /* #ifndef APP-NVUE */
  width: 100%;
  /* #endif */
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
}

.z-list__title,
.z-list__footer {
  line-height: 1;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  word-break: break-all;
  /* #endif */
}

.z-list__container {
  position: relative;
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  width: 100%;
  /* #endif */
}

.z-list__border-top,
.z-list__border-bottom {
  position: absolute;
  /* #ifdef APP-NVUE */
  height: 0.5px;
  z-index: -1;
  /* #endif */
  /* #ifndef APP-NVUE */
  height: 1px;
  transform: scaleY(0.5);
  z-index: 1;
  /* #endif */
}
.z-list__border-top { top: 0; transform-origin: 0 0; }
.z-list__border-bottom { bottom: 0; transform-origin: 0 100%; }

/* #ifndef APP-NVUE */
.z-list__border-default {
  background-color: var(--z-border-color, #EEEEEE) !important;
}
/* #endif */

/* ========== Cell ========== */
.z-cell {
  position: relative;
  flex: 1;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;

  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  box-sizing: border-box;
  /* #endif */
}

/* default bg (when background not provided) */
/* #ifndef APP-NVUE */
.z-cell--bg-default {
  background-color: var(--z-bg-color, #fff);
}
/* #endif */

/* press feedback (keeps original feel) */
.z-cell--press:active {
  /* #ifdef APP-NVUE */
  background-color: rgba(0, 0, 0, 0.2) !important;
  /* #endif */
  /* #ifndef APP-NVUE */
  background-color: var(--z-bg-color-hover, rgba(0, 0, 0, 0.06)) !important;
  /* #endif */
}

/* dividers inside cell (absolute, no height impact) */
.z-cell__border-top,
.z-cell__border-bottom {
  position: absolute;
  /* #ifdef APP-NVUE */
  height: 0.5px;
  z-index: -1;
  /* #endif */
  /* #ifndef APP-NVUE */
  height: 1px;
  transform: scaleY(0.5) translateZ(0);
  z-index: 1;
  /* #endif */
}
.z-cell__border-top { top: 0; transform-origin: 0 0; }
.z-cell__border-bottom { bottom: 0; transform-origin: 0 100%; }

/* content layout */
.z-cell__left {
  flex-direction: row;
  align-items: center;
  /* #ifndef APP-NVUE */
  display: flex;
  min-width: 0;
  /* #endif */
}

.z-cell__icon {
  width: 48rpx;
  height: 48rpx;
  margin-right: 24rpx;
  flex-shrink: 0;
}

.z-cell__texts {
  /* #ifndef APP-NVUE */
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
  /* #endif */
}

.z-cell__title {
  font-size: 28rpx;
  color: var(--z-text-color, #181818);
  /* #ifndef APP-NVUE */
  line-height: 1.2;
  /* #endif */
}

.z-cell__desc {
  margin-top: 8rpx;
  font-size: 24rpx;
  color: var(--z-text-muted, #7F7F7F);
  /* #ifndef APP-NVUE */
  line-height: 1.2;
  /* #endif */
}

.z-cell__right {
  flex-direction: row;
  align-items: center;
  /* #ifndef APP-NVUE */
  display: flex;
  flex-shrink: 0;
  /* #endif */
}

.z-cell__right-text {
  font-size: 24rpx;
  color: var(--z-text-muted, #7F7F7F);
  margin-left: 16rpx;
  margin-right: 16rpx;
  /* #ifndef APP-NVUE */
  line-height: 1;
  /* #endif */
}

/* arrow (same feel as original) */
.z-cell__arrow {
  height: 40rpx;
  width: 40rpx;
  border-width: 3px 3px 0 0;
  border-style: solid;
  transform: rotate(45deg) scale(0.5);
  transform-origin: center center;
  flex-shrink: 0;
  margin-left: auto;
  margin-right: -5.8579rpx;
  /* #ifndef APP-NVUE */
  border-radius: 4rpx;
  box-sizing: border-box;
  /* #endif */
  /* #ifdef APP-NVUE */
  border-top-right-radius: 3rpx;
  /* #endif */
}

/* ========== Badge ========== */
.z-badge {
  min-width: 32rpx;
  height: 32rpx;
  padding: 0 10rpx;
  border-radius: 999rpx;
  background-color: var(--z-danger, #FF3B30);
  margin-left: 16rpx;
  margin-right: 16rpx;

  /* #ifndef APP-NVUE */
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  /* #endif */
}

.z-badge--circle {
  width: 32rpx;
  padding: 0;
}

.z-badge--dot {
  width: 16rpx;
  min-width: 16rpx;
  height: 16rpx;
  padding: 0;
}

.z-badge__text {
  color: #fff;
  font-size: 22rpx;
  /* #ifndef APP-NVUE */
  line-height: 1;
  /* #endif */
}
</style>
