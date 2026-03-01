<template>
  <view
    class="z-title"
    :class="[compact ? 'is-compact' : '', clickable ? 'is-clickable' : '']"
    :style="rootStyle"
    :hover-class="clickable ? 'z-title--hover' : ''"
    hover-stay-time="80"
    @tap="onTap"
  >
    <view class="z-title__row">
      <!-- 标题左侧 -->
      <view v-if="$slots.left" class="z-title__left">
        <slot name="left" />
      </view>

      <!-- 标题主体 -->
      <view class="z-title__main">
        <view class="z-title__headline">
          <!-- 装饰线 -->
          <view v-if="line" class="z-title__line" :style="lineStyle" />

          <!-- 标题 + after（after 紧挨标题） -->
          <view class="z-title__titlewrap">
            <text
              class="z-title__text"
              :style="titleTextStyle"
              :class="[ellipsis ? 'is-ellipsis' : '']"
            >
              <slot>{{ title }}</slot>
            </text>

            <view v-if="$slots.after" class="z-title__after">
              <slot name="after" />
            </view>
          </view>
        </view>

        <!-- 描述 -->
        <text
          v-if="desc"
          class="z-title__desc"
          :style="descTextStyle"
          :class="[descEllipsis ? 'is-ellipsis' : '']"
        >
          {{ desc }}
        </text>
      </view>

      <!-- 靠右 -->
      <view v-if="$slots.right" class="z-title__right">
        <slot name="right" />
      </view>
    </view>

    <!-- 底部分割线 -->
    <view v-if="divider" class="z-title__divider" :style="dividerStyle" />
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type U = number | string

const props = withDefaults(defineProps<{
  title?: string
  desc?: string

  // 外观
  bg?: string
  padding?: U | [U, U]          // 数字= rpx，或 [上下, 左右]
  radius?: U
  marginTop?: U
  marginBottom?: U
  marginLeft?: U
  marginRight?: U
  
  // 标题
  size?: number                 // 只传数字，默认 rpx
  weight?: number | string
  color?: string
  ellipsis?: boolean

  // 描述
  descSize?: number             // 只传数字，默认 rpx
  descScale?: number            // 视觉缩放(突破12px限制)：1=不缩放，0.83≈10px效果
  descColor?: string
  descEllipsis?: boolean

  // 装饰线
  line?: boolean
  lineWidth?: number            // 只传数字，默认 rpx
  lineHeight?: number           // 只传数字，默认 rpx
  lineRadius?: number           // 只传数字，默认 rpx
  lineColor?: string
  lineGradient?: string
  lineGap?: number              // 只传数字，默认 rpx

  // 底部分割线
  divider?: boolean
  dividerColor?: string
  dividerThickness?: number     // 只传数字，默认 rpx
  dividerInset?: number         // 只传数字，默认 rpx

  // 行为
  clickable?: boolean
  compact?: boolean
}>(), {
  title: '',
  desc: '',
  bg: 'transparent',
  padding: 0,
  radius: 0,
  marginTop: 20,
  marginBottom: 20,
  marginLeft: 0,
  marginRight: 0,

  
  size: 30,
  weight: 600,
  color: '#111827',
  ellipsis: false,

  descSize: 18,
  descScale: 1,
  descColor: '#6B7280',
  descEllipsis: true,

  line: false,
  lineWidth: 6,
  lineHeight: 30,
  lineRadius: 8,
  lineColor: '#7C3AED',
  lineGradient: '',
  lineGap: 14,

  divider: false,
  dividerColor: 'rgba(17,24,39,0.08)',
  dividerThickness: 2,
  dividerInset: 0,

  clickable: false,
  compact: false
})

const emit = defineEmits<{ (e: 'click'): void }>()

const rpx = (v: U) => (typeof v === 'number' ? `${v}rpx` : v)

const rootStyle = computed(() => {
  let pad = '0'
  if (Array.isArray(props.padding)) {
    pad = `${rpx(props.padding[0])} ${rpx(props.padding[1])}`
  } else {
    pad = rpx(props.padding)
  }
  return {
    background: props.bg,
    padding: pad,
    borderRadius: rpx(props.radius),
    marginTop: rpx(props.marginTop),
    marginBottom: rpx(props.marginBottom),
    // ✅ 新增
    marginLeft: rpx(props.marginLeft),
    marginRight: rpx(props.marginRight)
  } as Record<string, string>
})


const lineStyle = computed(() => ({
  width: `${props.lineWidth}rpx`,
  height: `${props.lineHeight}rpx`,
  borderRadius: `${props.lineRadius}rpx`,
  marginRight: `${props.lineGap}rpx`,
  background: props.lineGradient && props.lineGradient.length > 0
    ? props.lineGradient
    : props.lineColor
}))

const titleTextStyle = computed(() => ({
  fontSize: `${props.size}rpx`,
  fontWeight: String(props.weight),
  color: props.color
}))

const descTextStyle = computed(() => ({
  fontSize: `${props.descSize}rpx`,
  color: props.descColor,
  display: 'inline-block',
  transform: props.descScale && props.descScale !== 1 ? `scale(${props.descScale})` : 'scale(1)',
  transformOrigin: 'left top'
}))

const dividerStyle = computed(() => ({
  height: `${props.dividerThickness}rpx`,
  background: props.dividerColor,
  marginLeft: `${props.dividerInset}rpx`,
  marginRight: `${props.dividerInset}rpx`,
  marginTop: props.compact ? '10rpx' : '16rpx'
}))

function onTap() {
  if (!props.clickable) return
  emit('click')
}
</script>

<style lang="scss" scoped>
.z-title {
  width: 100%;
  box-sizing: border-box;
}

.z-title__row {
  display: flex;
  align-items: center;
}

.z-title__left,
.z-title__right {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}

.z-title__left { margin-right: 14rpx; }
.z-title__right { margin-left: 14rpx; }

.z-title__main {
  flex: 1 1 auto;
  min-width: 0;
}

.z-title__headline {
  display: flex;
  align-items: center;
  min-width: 0;
}

.z-title__line { flex: 0 0 auto; }

/* 关键：titlewrap 承担“可压缩空间”，after紧跟标题 */
.z-title__titlewrap {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
}

.z-title__text {
  /* 关键：不再 flex:1 grow，避免把 after 顶到最右 */
  flex: 0 1 auto;
  min-width: 0;
  line-height: 1.22;
}

.z-title__after {
  flex: 0 0 auto;
  margin-left: 10rpx;
  display: flex;
  align-items: center;
}

.z-title__desc {
  margin-top: 8rpx;
  line-height: 1.25;
}

.z-title__divider { width: 100%; }

.is-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.z-title--hover { opacity: 0.92; }
.is-compact .z-title__desc { margin-top: 6rpx; }
</style>
