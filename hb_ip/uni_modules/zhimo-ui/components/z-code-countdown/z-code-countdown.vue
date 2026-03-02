<template>
  <view
    class="zcc"
    :class="[
      `zcc--${mode}`,
      `zcc--${size}`,
      { 'zcc--block': block, 'zcc--disabled': isDisabled, 'zcc--counting': state==='counting', 'zcc--sending': state==='sending', 'zcc--glass': glass }
    ]"
    :style="wrapStyle"
    @tap.stop="onTap"
    @click.stop="onTap"
  >
    <view class="zcc__inner" :style="innerStyle">
      <view v-if="showSpinner" class="zcc__spinner" aria-hidden="true"></view>
      <text class="zcc__text" :style="textStyleComputed">{{ displayText }}</text>
    </view>

    <!-- hairline border -->
    <!-- #ifndef APP-NVUE -->
    <view class="zcc__hairline" :style="hairlineStyle" />
    <!-- #endif -->
  </view>
</template>

<script setup>
import { computed, getCurrentInstance, onBeforeUnmount, reactive, ref, watch, nextTick } from 'vue'

const props = defineProps({
  /** idle text */
  text: { type: String, default: '发送验证码' },
  /** sending text */
  sendingText: { type: String, default: '正在发送…' },
  /** countdown suffix, e.g. "s后重发" */
  countdownSuffix: { type: String, default: 's后重发' },
  /** total seconds */
  seconds: { type: [Number, String], default: 60 },
  /** start immediately (e.g. page enters already in countdown) */
  autoStart: { type: Boolean, default: false },

  /** disabled */
  disabled: { type: Boolean, default: false },

  /** style: filled | outlined | soft | ghost */
  mode: { type: String, default: 'soft' },
  /** size: sm | md | lg */
  size: { type: String, default: 'md' },
  /** full width */
  block: { type: Boolean, default: false },

  /** iOS-ish glass effect (best on H5) */
  glass: { type: Boolean, default: true },

  /** colors */
  color: { type: String, default: '' },
  background: { type: String, default: '' },
  borderColor: { type: String, default: '' },
  disabledColor: { type: String, default: '' },
  disabledBackground: { type: String, default: '' },
  disabledBorderColor: { type: String, default: '' },

  /** radius rpx */
  radius: { type: [Number, String], default: 18 },
  /** custom padding (rpx) - default from size */
  paddingX: { type: [Number, String], default: '' },
  paddingY: { type: [Number, String], default: '' },

  /** width/height rpx (optional) */
  width: { type: [Number, String], default: '' },
  height: { type: [Number, String], default: '' },

  /** extra param passed to events */
  param: { type: [String, Number, Object], default: 0 },

  /**
   * optional async request handler:
   * if provided, component will call it on tap and auto start/reset based on resolve/reject
   * return true/void for success, throw/return false for failure.
   */
  request: { type: Function, default: null },

  /** formatter(remainingSeconds, state): string */
  formatter: { type: Function, default: null },

  /** show spinner when sending */
  loading: { type: Boolean, default: true },

  /** custom styles (object) */
  wrapStyle: { type: Object, default: null },
  innerStyle: { type: Object, default: null },
  textStyle: { type: Object, default: null },
  hairlineStyle: { type: Object, default: null }
})

const emit = defineEmits(['send', 'countdown', 'end', 'change'])

const state = ref('idle') // idle | sending | counting
const remain = ref(0)
let timer = null

const isDisabled = computed(() => props.disabled || state.value !== 'idle')
const showSpinner = computed(() => props.loading && state.value === 'sending')

const _seconds = computed(() => {
  const n = Number(props.seconds)
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : 60
})

function clearTimer() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function reset() {
  clearTimer()
  remain.value = 0
  state.value = 'idle'
  emit('change', { state: state.value, remaining: remain.value, param: props.param })
}

function start(total = _seconds.value) {
  clearTimer()
  const s = Number(total)
  remain.value = Number.isFinite(s) && s > 0 ? Math.floor(s) : _seconds.value
  state.value = 'counting'
  emit('change', { state: state.value, remaining: remain.value, param: props.param })

  timer = setInterval(() => {
    if (remain.value > 1) {
      remain.value -= 1
      emit('countdown', { seconds: remain.value, param: props.param })
      emit('change', { state: state.value, remaining: remain.value, param: props.param })
    } else {
      reset()
      emit('end', { param: props.param })
    }
  }, 1000)
}

async function onTap() {
  if (isDisabled.value) return

  clearTimer()
  state.value = 'sending'
  emit('change', { state: state.value, remaining: remain.value, param: props.param })
  emit('send', { param: props.param })

  // allow external handler
  if (typeof props.request === 'function') {
    try {
      const ret = await props.request({ param: props.param })
      // if handler returns false => treat as failure
      if (ret === false) {
        reset()
      } else {
        start()
      }
    } catch (e) {
      reset()
    }
  }
}

function success() {
  start()
}

function stop() {
  clearTimer()
  // keep state as is (caller can reset)
}

defineExpose({ start, success, reset, stop, getState: () => state.value, getRemaining: () => remain.value })

const displayText = computed(() => {
  if (typeof props.formatter === 'function') {
    return props.formatter(remain.value, state.value) || ''
  }
  if (state.value === 'sending') return props.sendingText
  if (state.value === 'counting') return `${remain.value}${props.countdownSuffix}`
  return props.text
})

// style helpers
const sizeMap = {
  sm: { font: 24, px: 22, py: 14, h: 64 },
  md: { font: 26, px: 26, py: 16, h: 72 },
  lg: { font: 28, px: 30, py: 18, h: 80 }
}

const themeColor = computed(() => props.color || 'var(--z-color-primary, #465CFF)')
const _radius = computed(() => Number(props.radius) || 18)

const wrapStyle = computed(() => ({
  width: props.width !== '' ? `${Number(props.width)}rpx` : (props.block ? '100%' : 'auto'),
  height: props.height !== '' ? `${Number(props.height)}rpx` : 'auto',
  borderRadius: `${_radius.value}rpx`,
  ...(props.wrapStyle || {})
}))

const innerStyle = computed(() => {
  const conf = sizeMap[props.size] || sizeMap.md
  const px = props.paddingX !== '' ? Number(props.paddingX) : conf.px
  const py = props.paddingY !== '' ? Number(props.paddingY) : conf.py
  const h = props.height !== '' ? Number(props.height) : conf.h

  const mode = props.mode
  const bgByMode = {
    filled: props.background || themeColor.value,
    soft: props.background || 'rgba(70, 92, 255, 0.12)',
    outlined: props.background || 'rgba(255,255,255,0.001)',
    ghost: props.background || 'transparent'
  }[mode] || (props.background || 'rgba(70, 92, 255, 0.12)')

  const disabledBg = props.disabledBackground || 'rgba(0,0,0,0.06)'

  return {
    minHeight: `${h}rpx`,
    padding: `${py}rpx ${px}rpx`,
    background: isDisabled.value ? disabledBg : bgByMode,
    ...(props.innerStyle || {})
  }
})

const textStyleComputed = computed(() => {
  const conf = sizeMap[props.size] || sizeMap.md
  const mode = props.mode

  const colorByMode = {
    filled: '#fff',
    soft: themeColor.value,
    outlined: themeColor.value,
    ghost: themeColor.value
  }[mode] || themeColor.value

  const disabledColor = props.disabledColor || 'rgba(0,0,0,0.35)'

  return {
    fontSize: `${conf.font}rpx`,
    color: isDisabled.value ? disabledColor : (props.color || colorByMode),
    ...(props.textStyle || {})
  }
})

const hairlineStyle = computed(() => {
  const mode = props.mode
  const bcByMode = {
    filled: 'rgba(255,255,255,0.18)',
    soft: 'rgba(70, 92, 255, 0.25)',
    outlined: props.borderColor || themeColor.value,
    ghost: 'transparent'
  }[mode] || (props.borderColor || 'rgba(70, 92, 255, 0.25)')

  const disabledBc = props.disabledBorderColor || 'rgba(0,0,0,0.10)'

  return {
    borderRadius: `${_radius.value * 2}rpx`,
    borderColor: isDisabled.value ? disabledBc : (props.borderColor || bcByMode),
    ...(props.hairlineStyle || {})
  }
})

watch(() => props.autoStart, (v) => {
  if (v) nextTick(() => start())
  else reset()
})

if (props.autoStart) {
  nextTick(() => start())
}

onBeforeUnmount(() => {
  clearTimer()
})
</script>

<style scoped>
.zcc{
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}
.zcc--block{ display:flex; width:100%; }
.zcc__inner{
  width:100%;
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 12rpx;
  box-sizing:border-box;
  border-radius: inherit;
  /* iOS soft shadow */
  box-shadow: 0 10rpx 24rpx rgba(0,0,0,0.06);
}
.zcc--ghost .zcc__inner{ box-shadow:none; }
.zcc--outlined .zcc__inner{ box-shadow: 0 10rpx 24rpx rgba(0,0,0,0.04); }

.zcc--glass .zcc__inner{
  /* best effort glass */
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.zcc--disabled .zcc__inner{
  box-shadow:none;
}

.zcc__text{
  font-weight: 600;
  letter-spacing: 0.2rpx;
}

.zcc__hairline{
  position:absolute;
  left:0; top:0;
  width:200%;
  height:200%;
  transform: scale(0.5,0.5) translateZ(0);
  transform-origin: 0 0;
  border: 1px solid rgba(0,0,0,0.08);
  box-sizing:border-box;
  pointer-events:none;
}

.zcc__spinner{
  width: 26rpx;
  height: 26rpx;
  border-radius: 50%;
  border: 3rpx solid rgba(255,255,255,0.55);
  border-top-color: rgba(255,255,255,0.95);
  box-sizing: border-box;
  animation: zccspin 0.9s linear infinite;
}
.zcc--soft .zcc__spinner,
.zcc--outlined .zcc__spinner,
.zcc--ghost .zcc__spinner{
  border-color: rgba(70,92,255,0.25);
  border-top-color: rgba(70,92,255,0.95);
}
.zcc--disabled .zcc__spinner{
  border-color: rgba(0,0,0,0.15);
  border-top-color: rgba(0,0,0,0.25);
}

@keyframes zccspin{
  from{ transform: rotate(0deg); }
  to{ transform: rotate(360deg); }
}
</style>
