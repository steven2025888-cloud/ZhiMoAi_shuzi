<template>
  <view class="z-ci__wrap" :style="wrapStyle" @tap="onAliClick">
    <view class="z-ci" :style="innerStyle" :class="{ 'z-ci--disabled': props.disabled }">
      <view
        v-for="(k, index) in keys"
        :key="k"
        class="z-ci__cell"
        :class="{
          'z-ci__cell--active': isActive(index),
          'z-ci__cell--filled': !!chars[index]
        }"
        :style="cellStyle(index)"
        @tap.stop="onTap"
      >
        <text class="z-ci__text" :style="textStyle">{{ showChar(index) }}</text>
        <text v-if="props.placeholder" class="z-ci__ph" :style="phStyle">{{ showPlaceholder(index) }}</text>

        <view
          v-if="props.cursor && !props.disabled"
          class="z-ci__cursor"
          :class="{ 'z-ci__cursor--on': isActive(index) && focused }"
          :style="cursorStyle"
        />
      </view>
    </view>

    <!-- hidden input captures native keyboard -->
    <input
      v-if="props.native"
      ref="inputRef"
      class="z-ci__hidden"
      :class="{ 'z-ci__alizero': aliZero }"
      :value="val"
      :type="props.type"
      :password="props.password"
      :focus="focused"
      :maxlength="props.length"
      :disabled="props.disabled"
      @input="onInput"
      @blur="onBlur"
      @confirm="onConfirm"
      @focus="onTap"
    />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type CodeInputType = 'text' | 'number' | 'idcard' | 'digit' | 'tel' | 'password'

const props = withDefaults(defineProps<{
  /** v-model */
  modelValue?: string

  /** input type (H5: can't dynamically switch in some runtimes) */
  type?: CodeInputType | string
  /** show mask */
  password?: boolean
  /** mask char when password */
  maskChar?: string

  /** disabled */
  disabled?: boolean

  /** auto focus on mount */
  autoFocus?: boolean

  /** use native keyboard */
  native?: boolean

  /** cursor */
  cursor?: boolean
  cursorColor?: string
  cursorHeight?: number | string

  /** total length */
  length?: number

  /** layout */
  cellWidth?: number | string
  cellHeight?: number | string
  gap?: number | string
  padding?: number | string
  marginTop?: number | string
  marginBottom?: number | string

  /** styles */
  background?: string
  /** 1 all border, 2 underline, 3 none */
  border?: number | string
  borderColor?: string
  activeColor?: string
  borderWidth?: number | string
  radius?: number | string

  /** text */
  fontSize?: number | string
  color?: string
  fontWeight?: number | string
  /** placeholder char for empty cells (optional) */
  placeholder?: string

  /** tag passthrough */
  tag?: any
}>(), {
  modelValue: '',
  type: 'number',
  password: false,
  maskChar: '●',

  disabled: false,
  autoFocus: false,

  native: true,

  cursor: true,
  cursorColor: '',
  cursorHeight: 40,

  length: 6,

  cellWidth: 80,
  cellHeight: 80,
  gap: 12,
  padding: 24,
  marginTop: 0,
  marginBottom: 0,

  background: 'transparent',
  border: 2,
  borderColor: 'rgba(0,0,0,0.14)',
  activeColor: '#465CFF',
  borderWidth: 2,
  radius: 16,

  fontSize: 36,
  color: 'rgba(0,0,0,0.88)',
  fontWeight: 700,
  placeholder: '',

  tag: 0
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'input', payload: { value: string }): void
  (e: 'complete', payload: { value: string }): void
  (e: 'focus'): void
  (e: 'blur', payload: { value: string }): void
  (e: 'confirm', payload: any): void
}>()

function toUnit(v: any, unit = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${unit}`
  const s = String(v)
  if (s.includes('rpx') || s.includes('px') || s.includes('%')) return s
  return `${s}${unit}`
}

function clampLen(n: any) {
  const x = Number(n)
  if (!isFinite(x)) return 6
  return Math.max(1, Math.min(12, Math.floor(x)))
}

function genKeys(n: number) {
  return Array.from({ length: n }).map(() => `zci_${Math.ceil(Math.random() * 10e5).toString(36)}`)
}

const inputRef = ref<any>(null)
const focused = ref(false)
const activeIndex = ref(-1)
const aliZero = ref(false)

const val = ref('')
const chars = ref<string[]>([])
const keys = ref<string[]>(genKeys(clampLen(props.length)))

const cursorOpacity = ref(1)
let cursorTimer: any = null

function stopCursor() {
  if (cursorTimer) {
    clearInterval(cursorTimer)
    cursorTimer = null
  }
  cursorOpacity.value = 1
}
function startCursor() {
  stopCursor()
  cursorTimer = setInterval(() => {
    cursorOpacity.value = cursorOpacity.value === 1 ? 0 : 1
  }, 450)
}

watch(
  () => props.length,
  (n) => {
    const len = clampLen(n)
    keys.value = genKeys(len)
    // keep existing value but clamp
    setValue(val.value, true)
  }
)

watch(
  () => props.modelValue,
  (v) => {
    const s = String(v || '').replace(/\s+/g, '')
    if (s === val.value) return
    setValue(s, true)
  }
)

watch(
  () => [activeIndex.value, focused.value, props.cursor, props.disabled],
  () => {
    if (!props.cursor || props.disabled) return stopCursor()
    if (focused.value && activeIndex.value >= 0 && activeIndex.value < clampLen(props.length)) startCursor()
    else stopCursor()
  },
  { deep: true }
)

onMounted(() => {
  setValue(String(props.modelValue || ''), true)
  if (props.autoFocus && !props.disabled) {
    nextTick(() => focus())
  }
})

onBeforeUnmount(() => stopCursor())

function rebuildChars(v: string) {
  const len = clampLen(props.length)
  const arr = v.split('').slice(0, len)
  chars.value = Array.from({ length: len }).map((_, i) => arr[i] || '')
}

function focus() {
  if (props.disabled) return
  focused.value = true
  if (activeIndex.value === -1) activeIndex.value = 0
  if (activeIndex.value >= clampLen(props.length)) activeIndex.value = clampLen(props.length) - 1
  emit('focus')
  // for some platforms
  nextTick(() => {
    try {
      inputRef.value && inputRef.value.focus && inputRef.value.focus()
    } catch (e) {}
  })
  onAliClick()
}

function blur() {
  focused.value = false
  stopCursor()
  nextTick(() => {
    try {
      inputRef.value && inputRef.value.blur && inputRef.value.blur()
    } catch (e) {}
  })
}

function setValue(v: string, silent = false) {
  const s = String(v || '').replace(/\s+/g, '')
  const len = clampLen(props.length)
  const next = s.slice(0, len)
  val.value = next
  rebuildChars(next)

  if (!next) activeIndex.value = silent ? -1 : 0
  else {
    const l = next.length
    activeIndex.value = l >= len ? len : l
    if (l === len) {
      if (!silent) emit('complete', { value: next })
      blur()
      try { uni.hideKeyboard && uni.hideKeyboard() } catch(e) {}
    }
  }

  if (!silent) {
    emit('update:modelValue', next)
    emit('input', { value: next })
  }
}

function clear() {
  setValue('', false)
  nextTick(() => focus())
}

function isActive(i: number) {
  return activeIndex.value === i
}

function onTap() {
  if (props.disabled) return
  focus()
}

function onInput(e: any) {
  const v = (e && e.detail && e.detail.value) ? e.detail.value : ''
  setValue(v, false)
}

function onBlur(e: any) {
  const v = (e && e.detail && e.detail.value) ? e.detail.value : ''
  focused.value = false
  // #ifdef MP-ALIPAY
  aliZero.value = false
  // #endif
  if (!v) activeIndex.value = -1
  emit('blur', { value: String(v || '').replace(/\s+/g, '') })
}

function onConfirm(e: any) {
  focused.value = false
  stopCursor()
  try { uni.hideKeyboard && uni.hideKeyboard() } catch(e2) {}
  emit('confirm', e)
}

function onAliClick() {
  // #ifdef MP-ALIPAY
  setTimeout(() => { aliZero.value = true }, 50)
  // #endif
}

function showChar(i: number) {
  const c = chars.value[i] || ''
  if (!c) return ''
  if (props.password) return props.maskChar || '●'
  return c
}
function showPlaceholder(i: number) {
  if (!props.placeholder) return ''
  return chars.value[i] ? '' : props.placeholder
}

const wrapStyle = computed(() => ({
  marginTop: toUnit(props.marginTop),
  marginBottom: toUnit(props.marginBottom)
}))

const innerStyle = computed(() => ({
  paddingLeft: toUnit(props.padding),
  paddingRight: toUnit(props.padding)
}))

const textStyle = computed(() => ({
  fontSize: toUnit(props.fontSize),
  lineHeight: toUnit(props.cellHeight),
  color: props.color,
  fontWeight: props.fontWeight as any
}))

const phStyle = computed(() => ({
  fontSize: toUnit(props.fontSize),
  lineHeight: toUnit(props.cellHeight),
  color: 'rgba(0,0,0,0.22)',
  fontWeight: props.fontWeight as any
}))

const cursorStyle = computed(() => ({
  height: toUnit(props.cursorHeight),
  background: props.cursorColor || props.activeColor,
  opacity: cursorOpacity.value
}))

function cellStyle(index: number) {
  const len = clampLen(props.length)
  const borderMode = Number(props.border)
  const bw = toUnit(props.borderWidth)
  const mr = index === len - 1 ? '0rpx' : toUnit(props.gap)

  const filled = !!chars.value[index]
  const active = activeIndex.value === index

  const bc = active || filled ? props.activeColor : props.borderColor

  const baseStyle: any = {
    width: toUnit(props.cellWidth),
    height: toUnit(props.cellHeight),
    marginRight: mr,
    background: props.background,
    borderRadius: toUnit(props.radius),
    borderStyle: borderMode === 3 ? 'none' : 'solid',
    borderColor: bc,
    borderTopWidth: borderMode === 1 ? bw : '0rpx',
    borderLeftWidth: borderMode === 1 ? bw : '0rpx',
    borderRightWidth: borderMode === 1 ? bw : '0rpx',
    borderBottomWidth: (borderMode === 1 || borderMode === 2) ? bw : '0rpx'
  }

  // 简化下划线样式 (border=2) - 移除圆角
  if (borderMode === 2) {
    baseStyle.borderRadius = '0rpx'
  }

  return baseStyle
}

defineExpose({ focus, blur, clear, setValue: (v: string) => setValue(v, false), getValue: () => val.value })
</script>

<style scoped>
.z-ci__wrap{
  position: relative;
  width: 100%;
}

.z-ci{
  width: 100%;
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.z-ci__cell{
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  /* #endif */
  flex-direction: row;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: visible;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 激活状态 - 简化 */
.z-ci__cell--active{
  /* #ifndef APP-NVUE */
  transform: scale(1.02);
  /* #endif */
}

/* 填充状态动画 - 简化 */
.z-ci__cell--filled{
  /* #ifndef APP-NVUE */
  animation: z_ci_pop 0.2s ease;
  /* #endif */
}

/* #ifndef APP-NVUE */
@keyframes z_ci_pop {
  0% { transform: scale(0.95); }
  50% { transform: scale(1.02); }
  100% { transform: scale(1); }
}
/* #endif */

.z-ci__text{
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.z-ci__ph{
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0.3;
}

/* 简化光标 - 移除花哨效果 */
.z-ci__cursor{
  border-radius: 2px;
  width: 0;
}

.z-ci__cursor--on{
  width: 2px;
  /* #ifndef APP-NVUE */
  animation: z_ci_cursor 1s infinite steps(1, start);
  /* #endif */
}

/* #ifndef APP-NVUE */
@keyframes z_ci_cursor {
  0% { opacity: 0; }
  50% { opacity: 1; }
  100% { opacity: 0; }
}
/* #endif */

.z-ci__hidden{
  position: absolute;
  /* #ifndef MP-WEIXIN || MP-QQ */
  width: 100%;
  height: 100%;
  /* #endif */
  left: 0;
  top: 0;
  /* #ifndef MP */
  right: 0;
  bottom: 0;
  flex: 1;
  /* #endif */
  z-index: 2;
  /* #ifdef MP-WEIXIN || MP-QQ*/
  height: 0rpx;
  width: 0rpx;
  /* #endif */
  margin: 0;
  padding: 0;
  opacity: 0;

  /* #ifdef MP-BAIDU || MP-TOUTIAO */
  font-size: 0.001rpx;
  /* #endif */

  /* #ifdef MP-BAIDU */
  transform: scaleX(2);
  transform-origin: 100% center;
  /* #endif */

  color: rgba(0,0,0,0);
  /* #ifdef MP || H5 || APP-VUE */
  border: none;
  /* #endif */
}

/* #ifdef MP-ALIPAY */
.z-ci__alizero{
  height: 0rpx;
  width: 0rpx;
}
/* #endif */

.z-ci--disabled{
  opacity: 0.5;
}
</style>
