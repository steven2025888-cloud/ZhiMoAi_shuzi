<template>
  <view class="z-in" :class="[sizeClass, disabled ? 'is-disabled' : '']" :style="rootStyle">
    <view
      v-if="controls"
      class="btn"
      :class="['btn-left', (disabled || isMinusDisabled) ? 'btn-disabled' : '']"
      @touchstart.stop.prevent="onPressStart(-1)"
      @touchend.stop.prevent="onPressEnd"
      @touchcancel.stop.prevent="onPressEnd"
      @mousedown.stop.prevent="onMouseDown(-1)"
      @mouseup.stop.prevent="onPressEnd"
      @mouseleave.stop.prevent="onPressEnd"
    >
      <text class="btn-text">−</text>
    </view>

    <view class="field">
      <input
        class="input"
        :disabled="disabled"
        :value="textValue"
        :type="inputType"
        :placeholder="placeholder"
        :placeholder-style="placeholderStyle"
        :maxlength="maxlength"
        @input="onInput"
        @blur="onBlur"
        @focus="onFocus"
      />
      <view v-if="showUnit" class="unit">
        <slot name="unit">{{ unit }}</slot>
      </view>
    </view>

    <view
      v-if="controls"
      class="btn"
      :class="['btn-right', (disabled || isPlusDisabled) ? 'btn-disabled' : '']"
      @touchstart.stop.prevent="onPressStart(1)"
      @touchend.stop.prevent="onPressEnd"
      @touchcancel.stop.prevent="onPressEnd"
      @mousedown.stop.prevent="onMouseDown(1)"
      @mouseup.stop.prevent="onPressEnd"
      @mouseleave.stop.prevent="onPressEnd"
    >
      <text class="btn-text">+</text>
    </view>
  </view>

  <view v-if="hint" class="hint">{{ hint }}</view>
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  /** v-model */
  modelValue: { type: Number, default: 0 },

  /** 范围与步长 */
  min: { type: Number, default: Number.NEGATIVE_INFINITY },
  max: { type: Number, default: Number.POSITIVE_INFINITY },
  step: { type: Number, default: 1 },
  precision: { type: Number, default: 0 },

  /** 展示/交互 */
  disabled: { type: Boolean, default: false },
  controls: { type: Boolean, default: true },
  size: { type: String, default: 'md' }, // sm | md | lg
  /** 宽度（可选），例如：'220rpx' / '260rpx' */
  width: { type: String, default: '200rpx' },
  /** 最小宽度（可选），默认适合 3 位数 */
  minWidth: { type: String, default: '50rpx' },
  placeholder: { type: String, default: '' },
  maxlength: { type: Number, default: 50 },

  /** 单位 */
  unit: { type: String, default: '' },

  /** 输入类型：digit(整数)/number(含小数)/text(自定义格式化显示) */
  type: { type: String, default: 'number' },

  /** 文本格式化与解析（可选） */
  formatter: { type: Function, default: null },
  parser: { type: Function, default: null },

  /** 长按连续加减 */
  longPress: { type: Boolean, default: true },
  pressInterval: { type: Number, default: 120 },

  /** 提示文案（演示用） */
  hint: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

const sizeClass = computed(() => {
  if (props.size === 'sm') return 'z-in-sm'
  if (props.size === 'lg') return 'z-in-lg'
  return 'z-in-md'
})

const showUnit = computed(() => !!props.unit)
// 注意：部分端 input type=number/digit 不支持展示格式化文本（例如 '¥ 1,200'），会导致“看不到数字”。
// 当使用 formatter/parser 或显式 type='text' 时，自动切换为 text。
const inputType = computed(() => {
  if (props.type === 'digit') return 'digit'
  if (props.type === 'text') return 'text'
  if (props.formatter && typeof props.formatter === 'function') return 'text'
  return 'number'
})

const rootStyle = computed(() => {
  const st = {}
  if (props.minWidth) st['min-width'] = props.minWidth
  if (props.width) st['width'] = props.width
  return st
})
const placeholderStyle = 'color: #9AA3B2;'

const clamp = (n) => {
  let v = n
  if (v < props.min) v = props.min
  if (v > props.max) v = props.max
  return v
}

const round = (n) => {
  const p = Number(props.precision || 0)
  if (p <= 0) return Math.round(n)
  const m = Math.pow(10, p)
  return Math.round(n * m) / m
}

const parseText = (s) => {
  const raw = (s == null) ? '' : String(s)
  if (props.parser && typeof props.parser === 'function') {
    const out = props.parser(raw)
    const num = Number(out)
    return Number.isFinite(num) ? num : null
  }
  // 默认解析：过滤非法字符
  const cleaned = raw
    .replace(/[^\d\.\-]/g, '')
    .replace(/(?!^)-/g, '') // 只保留开头的 -
  // 只保留一个小数点
  const parts = cleaned.split('.')
  const joined = parts.length <= 1 ? cleaned : (parts[0] + '.' + parts.slice(1).join(''))
  const num = Number(joined)
  return Number.isFinite(num) ? num : null
}

const formatValue = (n) => {
  if (!Number.isFinite(n)) return ''
  const fixed = round(n)
  if (props.formatter && typeof props.formatter === 'function') {
    return String(props.formatter(fixed))
  }
  // 默认：按精度展示
  const p = Number(props.precision || 0)
  return p > 0 ? fixed.toFixed(p) : String(fixed)
}

const internal = ref(clamp(round(props.modelValue)))
const isEditing = ref(false)
const textValue = ref(formatValue(internal.value))

watch(
  () => props.modelValue,
  (v) => {
    const next = clamp(round(Number(v)))
    internal.value = next
    if (!isEditing.value) textValue.value = formatValue(next)
  }
)

const isMinusDisabled = computed(() => clamp(internal.value - props.step) === internal.value)
const isPlusDisabled = computed(() => clamp(internal.value + props.step) === internal.value)

const commit = (n, trigger = 'change') => {
  const next = clamp(round(n))
  internal.value = next
  textValue.value = formatValue(next)
  emit('update:modelValue', next)
  emit(trigger, next)
}

const onInput = (e) => {
  const v = (e && e.detail) ? e.detail.value : ''
  textValue.value = v

  const num = parseText(v)
  if (num == null) return

  // typing 时尽量不强制格式化，先 clamp + round
  const next = clamp(round(num))
  internal.value = next
  emit('update:modelValue', next)
}

const onFocus = () => {
  isEditing.value = true
  emit('focus')
  // 聚焦时把格式化后的文本保留；如需“原始输入”可自行 formatter/parser
}

const onBlur = () => {
  isEditing.value = false
  // 失焦时统一格式化并触发 change
  const num = parseText(textValue.value)
  const next = (num == null) ? internal.value : clamp(round(num))
  commit(next, 'change')
  emit('blur')
}

/** 步进 */
const stepBy = (dir) => {
  if (props.disabled) return
  if (dir < 0 && isMinusDisabled.value) return
  if (dir > 0 && isPlusDisabled.value) return
  commit(internal.value + dir * props.step, 'change')
}

/** 长按（按下立即步进一次，然后延迟进入连发） */
let repeatTimer = null
let delayTimer = null
let pressDir = 0

const clearTimer = () => {
  if (delayTimer) {
    clearTimeout(delayTimer)
    delayTimer = null
  }
  if (repeatTimer) {
    clearInterval(repeatTimer)
    repeatTimer = null
  }
  pressDir = 0
}

const onPressStart = (dir) => {
  if (props.disabled) return
  if (dir < 0 && isMinusDisabled.value) return
  if (dir > 0 && isPlusDisabled.value) return

  // 单击也能立刻生效
  stepBy(dir)

  if (!props.longPress) return

  pressDir = dir
  clearTimer()

  // 长按延迟触发连发，避免“点一下就多跳”
  delayTimer = setTimeout(() => {
    repeatTimer = setInterval(() => {
      stepBy(pressDir)
    }, Math.max(60, Number(props.pressInterval || 120)))
  }, 320)
}

const onPressEnd = () => {
  clearTimer()
}

/** PC 鼠标长按 */
const onMouseDown = (dir) => {
  onPressStart(dir)
}

onBeforeUnmount(() => clearTimer())
</script>

<style scoped>
.z-in{
  display:inline-flex;
  align-items:stretch;
  /* 默认宽度适合 3 位数；可通过 width/minWidth 或外层 style 调整 */
  min-width:210rpx;
  border-radius:14rpx;
  background:#FFFFFF;
  border:1px solid #E6EAF2;
  overflow:hidden;
}

.z-in.is-disabled{
  opacity:0.6;
}

.field{
  flex:1;
  min-width:82rpx;
  display:flex;
  align-items:center;
  padding:0 10rpx;
  gap:10rpx;
}

.input{
  flex:1;
  min-width:0;
  width:1%;
  height:100%;
  padding:0;
  margin:0;
  font-size:28rpx;
  line-height:1.2;
  color:#111827;
  text-align:center;
  background:transparent;
}

.unit{
  font-size:24rpx;
  color:#6B7280;
  flex:0 0 auto;
}

.btn{
  width:64rpx;
  display:flex;
  align-items:center;
  justify-content:center;
  background:#F6F8FC;
  border-right:1px solid #E6EAF2;
  user-select:none;
}

.btn-right{
  border-right:none;
  border-left:1px solid #E6EAF2;
}

.btn-disabled{
  background:#F1F3F7;
}

.btn-text{
  font-size:36rpx;
  color:#334155;
  font-weight:600;
}

.z-in-sm{ height:68rpx; }
.z-in-md{ height:76rpx; }
.z-in-lg{ height:88rpx; }

.hint{
  margin-top:10rpx;
  font-size:24rpx;
  color:#6B7280;
}
</style>
