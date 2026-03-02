<template>
  <view class="z-progress" :class="{ 'is-disabled': disabled }">
    <view
      class="z-progress__track"
      :style="trackStyle"
      @tap.stop="onTrackTap"
    >
      <!-- #ifndef APP-NVUE -->
      <view
        class="z-progress__bar"
        :class="barClass"
        :style="barStyle"
      >
        <view v-if="striped" class="z-progress__stripes" :class="{ 'is-stripes-ani': stripeAnimated && animated }" />
      </view>
      <!-- #endif -->

      <!-- #ifdef APP-NVUE -->
      <view
        ref="barRef"
        class="z-progress__bar"
        :class="barClass"
        :style="barNvueStyle"
      >
        <view v-if="striped" class="z-progress__stripes" :class="{ 'is-stripes-ani': stripeAnimated && animated }" />
      </view>
      <!-- #endif -->

      <!-- inside label -->
      <view v-if="showInside && (showText || $slots.inside)" class="z-progress__inside" :style="insideStyle">
        <slot name="inside">
          <text class="z-progress__inside-text" :style="insideTextStyle">{{ displayText }}</text>
        </slot>
      </view>
    </view>

    <!-- right text -->
    <text
      v-if="showText && !showInside"
      class="z-progress__text"
      :style="textStyle"
    >
      <slot name="text">{{ displayText }}</slot>
    </text>
  </view>
</template>

<script setup>
/**
 * z-progress 线性进度条（Vue3 / uni-app）
 * - 支持 H5 / 小程序 / App-NVUE
 * - 支持动画、条纹、点击跳转、右侧文本/内部文本
 */

// #ifdef APP-NVUE
const animation = uni.requireNativePlugin('animation')
// #endif

import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** 进度（0-100） */
  percent: { type: [Number, String], default: 0 },

  /** 轨道高度（rpx） */
  height: { type: [Number, String], default: 10 },

  /** 圆角（rpx） */
  radius: { type: [Number, String], default: 999 },

  /** 轨道背景色 */
  background: { type: String, default: 'var(--z-color-border, #E5E7EB)' },

  /** 进度条颜色（支持渐变） */
  color: { type: String, default: '' },

  /** 是否显示文本 */
  showText: { type: Boolean, default: false },

  /** 文本颜色 */
  textColor: { type: String, default: 'var(--z-color-text, #334155)' },

  /** 文本大小（rpx） */
  textSize: { type: [Number, String], default: 26 },

  /** 文本宽度（rpx） */
  textWidth: { type: [Number, String], default: 96 },

  /** 是否显示在内部（右侧不显示） */
  showInside: { type: Boolean, default: false },

  /** 内部文本颜色 */
  insideTextColor: { type: String, default: '#ffffff' },

  /** 内部文本大小（rpx） */
  insideTextSize: { type: [Number, String], default: 22 },

  /** 内部最小显示宽度（%），避免太短看不到字 */
  insideMinPercent: { type: [Number, String], default: 18 },

  /** 是否启用动画 */
  animated: { type: Boolean, default: true },

  /** 动画时长（ms） */
  duration: { type: [Number, String], default: 360 },

  /** 条纹 */
  striped: { type: Boolean, default: false },

  /** 条纹动画 */
  stripeAnimated: { type: Boolean, default: true },

  /** 点击轨道更新进度（配合 v-model 更好用） */
  clickable: { type: Boolean, default: false },

  /** 禁用 */
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['change', 'end', 'activeend', 'update:percent'])

const barRef = ref(null)

const percentClamped = computed(() => {
  let p = Number(props.percent)
  if (Number.isNaN(p)) p = 0
  if (p < 0) p = 0
  if (p > 100) p = 100
  return p
})

const activeColor = computed(() => {
  const c = props.color
  if (c && c !== 'true') return c
  return 'var(--z-color-primary, #465CFF)'
})

const displayText = computed(() => `${Math.round(percentClamped.value)}%`)

const trackStyle = computed(() => ({
  height: `${Number(props.height)}rpx`,
  borderRadius: `${Number(props.radius)}rpx`,
  background: props.background
}))

const barClass = computed(() => ({
  'is-animated': props.animated,
  'is-striped': props.striped
}))

const translateX = computed(() => `${100 - percentClamped.value}%`)

const barStyle = computed(() => ({
  background: activeColor.value,
  transform: `translate3d(-${translateX.value},0,0)`,
  transitionDuration: props.animated ? `${Number(props.duration)}ms` : '0ms'
}))

const barNvueStyle = computed(() => ({
  background: activeColor.value
}))

const insideStyle = computed(() => {
  const minP = Math.max(0, Math.min(100, Number(props.insideMinPercent)))
  const p = percentClamped.value
  const showP = p > 0 ? Math.max(p, minP) : 0
  return {
    width: `${showP}%`,
    borderRadius: `${Number(props.radius)}rpx`
  }
})

const insideTextStyle = computed(() => ({
  color: props.insideTextColor,
  fontSize: `${Number(props.insideTextSize)}rpx`
}))

const textStyle = computed(() => ({
  width: `${Number(props.textWidth)}rpx`,
  fontSize: `${Number(props.textSize)}rpx`,
  color: props.textColor
}))

let tmr = null

function emitEndLater(ms) {
  if (tmr) clearTimeout(tmr)
  tmr = setTimeout(() => {
    emit('end', { percent: percentClamped.value })
    emit('activeend', {})
  }, Math.max(0, ms))
}

// #ifdef APP-NVUE
function nvueAnimateToPercent() {
  const el = barRef.value && barRef.value.ref
  if (!el) return
  const ms = props.animated ? Number(props.duration) : 0
  const x = 100 - percentClamped.value
  animation.transition(
    el,
    {
      styles: { transform: `translateX(-${x}%)` },
      duration: ms,
      timingFunction: 'linear',
      needLayout: false,
      delay: 0
    },
    () => {
      emit('end', { percent: percentClamped.value })
      emit('activeend', {})
    }
  )
}
// #endif

function refresh() {
  // 仅用于外部手动触发动画重算（例如 percent 同值重复赋值）
  nextTick(() => {
    // #ifndef APP-NVUE
    emitEndLater(props.animated ? Number(props.duration) : 0)
    // #endif
    // #ifdef APP-NVUE
    nvueAnimateToPercent()
    // #endif
  })
}

defineExpose({ refresh })

watch(
  () => props.percent,
  () => {
    nextTick(() => {
      // #ifndef APP-NVUE
      emitEndLater(props.animated ? Number(props.duration) : 0)
      // #endif
      // #ifdef APP-NVUE
      nvueAnimateToPercent()
      // #endif
    })
  }
)

onMounted(() => {
  nextTick(() => {
    // #ifndef APP-NVUE
    emitEndLater(props.animated ? Number(props.duration) : 0)
    // #endif
    // #ifdef APP-NVUE
    nvueAnimateToPercent()
    // #endif
  })
})

function onTrackTap(e) {
  if (!props.clickable || props.disabled) return
  // #ifndef APP-NVUE
  try {
    const x = (e && e.detail && (e.detail.x ?? e.detail.clientX)) || 0
    const q = uni.createSelectorQuery()
    q.in?.(getCurrentInstance()?.proxy || null)
    q.select('.z-progress__track').boundingClientRect()
    q.exec((res) => {
      const rect = res && res[0]
      if (!rect || !rect.width) {
        emit('change', { percent: percentClamped.value })
        return
      }
      const p = Math.max(0, Math.min(100, Math.round(((x - rect.left) / rect.width) * 100)))
      emit('update:percent', p)
      emit('change', { percent: p })
    })
  } catch (err) {
    emit('change', { percent: percentClamped.value })
  }
  // #endif

  // #ifdef APP-NVUE
  // nvue 端坐标/测量差异较大：直接抛出 change，交给外部决定
  emit('change', { percent: percentClamped.value })
  // #endif
}
</script>

<style scoped>
.z-progress{
  width: 100%;
  /* #ifndef APP-NVUE */
  display:flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
}
.z-progress.is-disabled{ opacity: .6; }

.z-progress__track{
  flex: 1;
  position: relative;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  width: 100%;
  transform: translateZ(0);
  /* #endif */
}

/* nvue android overflow hidden 有问题：保持与原组件一致的实现方式 */
.z-progress__bar{
  position: absolute;
  left: 0; right: 0; top: 0; bottom: 0;
  /* #ifndef APP-NVUE */
  width: 100%;
  z-index: 2;
  transform: translate3d(-100%, 0, 0);
  transition-property: transform;
  transition-timing-function: linear;
  transition-duration: 0ms;
  /* #endif */

  /* #ifdef APP-NVUE */
  transform: translateX(-100%);
  /* #endif */
}
.z-progress__bar.is-animated{
  /* 具体时长由内联 style 控制 */
}
.z-progress__text{
  text-align: center;
  /* #ifndef APP-NVUE */
  display:block;
  flex-shrink: 0;
  /* #endif */
}

.z-progress__stripes{
  position:absolute;
  left:0; right:0; top:0; bottom:0;
  opacity: .35;
  background-image: repeating-linear-gradient(
    45deg,
    rgba(255,255,255,.75) 0,
    rgba(255,255,255,.75) 10px,
    rgba(255,255,255,0) 10px,
    rgba(255,255,255,0) 20px
  );
  transform: translateX(0);
}
.z-progress__stripes.is-stripes-ani{
  /* #ifndef APP-NVUE */
  animation: z-progress-stripes 1.2s linear infinite;
  /* #endif */
}

@keyframes z-progress-stripes {
  from { transform: translateX(0); }
  to { transform: translateX(40px); }
}

.z-progress__inside{
  position:absolute;
  left:0; top:0; bottom:0;
  z-index: 3;
  /* #ifndef APP-NVUE */
  display:flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: flex-end;
  padding-right: 10rpx;
  pointer-events: none;
}
.z-progress__inside-text{
  /* #ifndef APP-NVUE */
  display:block;
  /* #endif */
  line-height: 1;
}
</style>