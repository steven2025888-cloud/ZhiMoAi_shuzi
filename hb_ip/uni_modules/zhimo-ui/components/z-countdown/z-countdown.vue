<template>
  <view class="z-countdown" :style="wrapStyle">
    <!-- Years -->
    <template v-if="showYears && computedParts.y > 0">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="yearLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ yearLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.y }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.y }}</text>
          </view>
        </view>
        <text v-if="yearLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ yearLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="yearLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ yearLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.y" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.y }}</text>
        </view>
        <text v-if="yearLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ yearLabel }}</text>
      </view>
    </template>

    <!-- Months -->
    <template v-if="showMonths && computedParts.mo > 0">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="monthLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ monthLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.mo }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.mo }}</text>
          </view>
        </view>
        <text v-if="monthLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ monthLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="monthLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ monthLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.mo" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.mo }}</text>
        </view>
        <text v-if="monthLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ monthLabel }}</text>
      </view>
    </template>

    <!-- Days -->
    <template v-if="showDays && computedParts.d > 0">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="dayLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ dayLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.d }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.d }}</text>
          </view>
        </view>
        <text v-if="dayLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ dayLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="dayLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ dayLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.d" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.d }}</text>
        </view>
        <text v-if="dayLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ dayLabel }}</text>
      </view>
    </template>

    <!-- Hours -->
    <template v-if="showHours">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="hourLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ hourLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.h }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.h }}</text>
          </view>
        </view>
        <text v-if="hourLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ hourLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="hourLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ hourLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.h" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.h }}</text>
        </view>
        <text v-if="hourLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ hourLabel }}</text>
      </view>
    </template>

    <!-- Minutes -->
    <template v-if="showMinutes">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="minuteLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ minuteLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.m }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.m }}</text>
          </view>
        </view>
        <text v-if="minuteLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ minuteLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="minuteLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ minuteLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.m" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.m }}</text>
        </view>
        <text v-if="minuteLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ minuteLabel }}</text>
      </view>
    </template>

    <!-- Seconds -->
    <template v-if="showSeconds">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="secondLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ secondLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="flipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.s }" :style="flipCardStyle">
            <text class="z-countdown__text" :style="textStyle">{{ computedParts.s }}</text>
          </view>
        </view>
        <text v-if="secondLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ secondLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="secondLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ secondLabel }}</text>
        <view class="z-countdown__box" :style="boxStyle">
          <z-number v-if="useZNumber" :text="computedParts.s" :preset="numberPreset" :size="fontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="textStyle">{{ computedParts.s }}</text>
        </view>
        <text v-if="secondLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ secondLabel }}</text>
      </view>
    </template>

    <!-- Milliseconds -->
    <template v-if="showMs">
      <view v-if="flip" class="z-countdown__flip-container" :style="flipContainerStyle">
        <text v-if="msLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ msLabel }}</text>
        <view class="z-countdown__flip-wrapper" :style="msFlipWrapperStyle">
          <view class="z-countdown__flip-card" :class="{ 'z-countdown__flip-card--flipping': flipStates.ms }" :style="msFlipCardStyle">
            <text class="z-countdown__text" :style="msTextStyle">{{ computedParts.ms }}</text>
          </view>
        </view>
        <text v-if="msLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__flip-label" :style="flipLabelStyle">{{ msLabel }}</text>
      </view>
      <view v-else class="z-countdown__item" :style="itemStyle">
        <text v-if="msLabel && (computedLabelPosition === 'top' || computedLabelPosition === 'left')" class="z-countdown__label" :style="labelStyle">{{ msLabel }}</text>
        <view class="z-countdown__box" :style="msBoxStyle">
          <z-number v-if="useZNumber" :text="computedParts.ms" :preset="numberPreset" :size="msFontSize" :color="computedColor" :bold="bold" />
          <text v-else class="z-countdown__text" :style="msTextStyle">{{ computedParts.ms }}</text>
        </view>
        <text v-if="msLabel && (computedLabelPosition === 'bottom' || computedLabelPosition === 'right')" class="z-countdown__label" :style="labelStyle">{{ msLabel }}</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, defineExpose } from 'vue'

type TimeInput = number | {
  years?: number
  months?: number
  days?: number
  hours?: number
  minutes?: number
  seconds?: number
  milliseconds?: number
}

const props = defineProps({
  /** Time input: seconds (number) or object {years, months, days, hours, minutes, seconds, milliseconds} */
  time: { type: [Number, Object] as any, default: 0 },

  /** Legacy: seconds (for backward compatibility) */
  seconds: { type: [Number, String], default: 0 },

  /** Auto start */
  autoStart: { type: Boolean, default: true },

  /** Show parts */
  showYears: { type: Boolean, default: false },
  showMonths: { type: Boolean, default: false },
  showDays: { type: Boolean, default: false },
  showHours: { type: Boolean, default: true },
  showMinutes: { type: Boolean, default: true },
  showSeconds: { type: Boolean, default: true },
  showMs: { type: Boolean, default: false },

  /** Unit labels (Chinese by default) */
  yearLabel: { type: String, default: '年' },
  monthLabel: { type: String, default: '月' },
  dayLabel: { type: String, default: '日' },
  hourLabel: { type: String, default: '时' },
  minuteLabel: { type: String, default: '分' },
  secondLabel: { type: String, default: '秒' },
  msLabel: { type: String, default: '毫秒' },

  /** Flip effect */
  flip: { type: Boolean, default: false },
  flipDuration: { type: Number, default: 600 },
  flipCardWidth: { type: [Number, String], default: 60 },
  flipCardHeight: { type: [Number, String], default: 80 },

  /** Use z-number component */
  useZNumber: { type: Boolean, default: false },
  numberPreset: { type: String, default: 'digital' },

  /** Typography */
  fontSize: { type: [Number, String], default: 28 },
  msFontSize: { type: [Number, String], default: 24 },
  color: { type: String, default: '#333333' },
  bold: { type: Boolean, default: false },

  /** Label styling */
  labelSize: { type: [Number, String], default: 24 },
  labelColor: { type: String, default: '#666666' },
  labelWeight: { type: [Number, String], default: 400 },
  labelMargin: { type: String, default: '0 8rpx' },
  labelPosition: { type: String, default: '' }, // 'top' | 'bottom' | 'left' | 'right' | '' (auto)

  /** Box styling */
  width: { type: [Number, String], default: 0 },
  height: { type: [Number, String], default: 0 },
  minWidth: { type: [Number, String], default: 0 },
  minHeight: { type: [Number, String], default: 0 },
  padding: { type: String, default: '' },
  background: { type: String, default: '' },
  borderRadius: { type: [Number, String], default: 0 },
  borderColor: { type: String, default: '' },
  borderWidth: { type: [Number, String], default: 0 },
  boxShadow: { type: String, default: '' },

  /** Wrapper styling */
  gap: { type: [Number, String], default: 4 },

  /** Behavior */
  interval: { type: Number, default: 1000 },
  padZero: { type: Boolean, default: true }
})

const emit = defineEmits<{
  (e: 'change', payload: any): void
  (e: 'finish'): void
}>()

const timer = ref<number | null>(null)
const endAt = ref(0)
const remainMs = ref(0)
const running = ref(false)

// Flip animation states
const flipStates = ref({
  y: false,
  mo: false,
  d: false,
  h: false,
  m: false,
  s: false,
  ms: false
})

const prevParts = ref({
  y: '00',
  mo: '00',
  d: '00',
  h: '00',
  m: '00',
  s: '00',
  ms: '000'
})

const computedColor = computed(() => props.color)

// Computed label position: auto-select based on flip mode
const computedLabelPosition = computed(() => {
  if (props.labelPosition) return props.labelPosition
  return props.flip ? 'bottom' : 'right'
})

function toRpx(val: number | string): string {
  if (!val) return ''
  const str = String(val)
  if (str.includes('rpx') || str.includes('px') || str.includes('%')) return str
  return `${val}rpx`
}

function parseTimeInput(input: TimeInput): number {
  if (typeof input === 'number') {
    return input * 1000 // convert seconds to ms
  }

  const { years = 0, months = 0, days = 0, hours = 0, minutes = 0, seconds = 0, milliseconds = 0 } = input

  // Approximate: 1 year = 365 days, 1 month = 30 days
  const totalDays = years * 365 + months * 30 + days
  const totalSeconds = totalDays * 86400 + hours * 3600 + minutes * 60 + seconds
  const totalMs = totalSeconds * 1000 + milliseconds

  return totalMs
}

function pad2(n: number) {
  return props.padZero ? String(n).padStart(2, '0') : String(n)
}

function calcParts(msLeft: number) {
  const totalMs = Math.max(0, Math.floor(msLeft))
  const totalSec = Math.floor(totalMs / 1000)

  // Calculate years, months, days, hours, minutes, seconds, milliseconds
  const y = Math.floor(totalSec / (365 * 86400))
  const remainAfterYears = totalSec % (365 * 86400)

  const mo = Math.floor(remainAfterYears / (30 * 86400))
  const remainAfterMonths = remainAfterYears % (30 * 86400)

  const d = Math.floor(remainAfterMonths / 86400)
  const remainAfterDays = remainAfterMonths % 86400

  const h = Math.floor(remainAfterDays / 3600)
  const m = Math.floor((remainAfterDays % 3600) / 60)
  const s = Math.floor(remainAfterDays % 60)
  const ms = Math.floor((totalMs % 1000))

  return {
    y: pad2(y),
    mo: pad2(mo),
    d: pad2(d),
    h: pad2(h),
    m: pad2(m),
    s: pad2(s),
    ms: String(ms).padStart(3, '0')
  }
}

const computedParts = computed(() => calcParts(remainMs.value))

const wrapStyle = computed(() => ({
  display: 'flex',
  alignItems: 'center',
  gap: toRpx(props.gap)
}))

const boxStyle = computed(() => {
  const style: any = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  }

  if (props.width) style.width = toRpx(props.width)
  if (props.height) style.height = toRpx(props.height)
  if (props.minWidth) style.minWidth = toRpx(props.minWidth)
  if (props.minHeight) style.minHeight = toRpx(props.minHeight)
  if (props.padding) style.padding = props.padding
  if (props.background) style.background = props.background
  if (props.borderRadius) style.borderRadius = toRpx(props.borderRadius)
  if (props.boxShadow) style.boxShadow = props.boxShadow

  if (props.borderColor && props.borderWidth) {
    style.border = `${toRpx(props.borderWidth)} solid ${props.borderColor}`
  }

  return style
})

const msBoxStyle = computed(() => ({
  ...boxStyle.value,
  fontSize: toRpx(props.msFontSize)
}))

const textStyle = computed(() => ({
  fontSize: toRpx(props.fontSize),
  color: computedColor.value,
  fontWeight: props.bold ? '700' : '400',
  fontVariantNumeric: 'tabular-nums'
}))

const msTextStyle = computed(() => ({
  fontSize: toRpx(props.msFontSize),
  color: computedColor.value,
  fontWeight: props.bold ? '700' : '400',
  fontVariantNumeric: 'tabular-nums'
}))

const labelStyle = computed(() => ({
  fontSize: toRpx(props.labelSize),
  color: props.labelColor,
  fontWeight: String(props.labelWeight),
  margin: props.labelMargin
}))

const msLabelStyle = computed(() => ({
  fontSize: toRpx(props.labelSize),
  color: props.labelColor,
  fontWeight: String(props.labelWeight),
  margin: props.labelMargin
}))

// Item container style (for non-flip mode)
const itemStyle = computed(() => {
  const isVertical = computedLabelPosition.value === 'top' || computedLabelPosition.value === 'bottom'
  return {
    display: 'inline-flex',
    flexDirection: isVertical ? 'column' : 'row',
    alignItems: 'center'
  }
})

// Flip container style
const flipContainerStyle = computed(() => {
  const isVertical = computedLabelPosition.value === 'top' || computedLabelPosition.value === 'bottom'
  return {
    display: 'inline-flex',
    flexDirection: isVertical ? 'column' : 'row',
    alignItems: 'center'
  }
})

// Flip styles
const flipLabelStyle = computed(() => ({
  fontSize: toRpx(props.labelSize),
  color: props.labelColor,
  fontWeight: String(props.labelWeight),
  textAlign: 'center',
  marginBottom: '8rpx',
  display: 'block'
}))

const flipWrapperStyle = computed(() => ({
  position: 'relative',
  display: 'inline-block',
  width: toRpx(props.flipCardWidth),
  height: toRpx(props.flipCardHeight)
}))

const msFlipWrapperStyle = computed(() => ({
  position: 'relative',
  display: 'inline-block',
  width: toRpx(props.flipCardWidth),
  height: toRpx(props.flipCardHeight)
}))

const flipCardStyle = computed(() => {
  const style: any = {
    position: 'relative',
    width: '100%',
    height: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: toRpx(props.borderRadius || 8)
  }

  if (props.background) style.background = props.background
  if (props.boxShadow) style.boxShadow = props.boxShadow
  if (props.borderColor && props.borderWidth) {
    style.border = `${toRpx(props.borderWidth)} solid ${props.borderColor}`
  }

  return style
})

const msFlipCardStyle = computed(() => ({
  ...flipCardStyle.value
}))

function clearTimer() {
  if (timer.value != null) {
    clearTimeout(timer.value as any)
    timer.value = null
  }
  running.value = false
}

const clampInterval = computed(() => {
  if (props.showMs) return Math.max(30, Math.min(100, props.interval || 80))
  return Math.max(200, props.interval || 1000)
})

function scheduleTick() {
  if (!running.value) return
  const now = Date.now()
  const left = Math.max(0, endAt.value - now)
  remainMs.value = left

  emit('change', {
    ms: left,
    seconds: Math.floor(left / 1000),
    parts: computedParts.value
  })

  if (left <= 0) {
    clearTimer()
    emit('finish')
    return
  }

  timer.value = setTimeout(scheduleTick, clampInterval.value) as any
}

function start() {
  if (running.value) return
  const now = Date.now()
  if (!endAt.value || endAt.value < now) {
    endAt.value = now + Math.max(0, remainMs.value)
  }
  running.value = true
  scheduleTick()
}

function pause() {
  if (!running.value) return
  const now = Date.now()
  remainMs.value = Math.max(0, endAt.value - now)
  clearTimer()
}

function reset(nextTime?: TimeInput) {
  clearTimer()
  const timeInput = nextTime !== undefined ? nextTime : (props.time || props.seconds)
  remainMs.value = parseTimeInput(timeInput)
  endAt.value = Date.now() + remainMs.value
  if (props.autoStart) start()
}

defineExpose({ start, pause, reset })

// Watch for value changes to trigger flip animation
watch(
  () => computedParts.value,
  (newParts, oldParts) => {
    if (!props.flip || !oldParts) return

    const keys: Array<keyof typeof newParts> = ['y', 'mo', 'd', 'h', 'm', 's', 'ms']
    keys.forEach(key => {
      if (newParts[key] !== prevParts.value[key]) {
        flipStates.value[key] = true
        prevParts.value[key] = newParts[key]

        setTimeout(() => {
          flipStates.value[key] = false
        }, props.flipDuration)
      }
    })
  },
  { deep: true }
)

watch(
  () => [props.time, props.seconds],
  () => {
    const timeInput = props.time || props.seconds
    remainMs.value = parseTimeInput(timeInput)
    endAt.value = Date.now() + remainMs.value
    clearTimer()
    if (props.autoStart) start()
  },
  { immediate: true, deep: true }
)

onMounted(() => {
  if (props.autoStart) start()
})

onBeforeUnmount(() => {
  clearTimer()
})
</script>

<style scoped>
.z-countdown{
  display: inline-flex;
  align-items: flex-end;
}

.z-countdown__item{
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.z-countdown__box{
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.z-countdown__text{
  line-height: 1;
}

.z-countdown__label{
  transition: opacity 0.3s ease;
}

/* Flip animation styles */
.z-countdown__flip-container{
  display: inline-flex;
  flex-direction: column;
  align-items: center;
}

.z-countdown__flip-label{
  display: block;
  text-align: center;
}

.z-countdown__flip-wrapper{
  position: relative;
  perspective: 1000rpx;
}

.z-countdown__flip-card{
  position: relative;
  transform-style: preserve-3d;
  transition: transform 0.6s ease-in-out;
}

.z-countdown__flip-card--flipping{
  animation: flipPage 0.6s ease-in-out;
}

@keyframes flipPage {
  0% {
    transform: rotateY(0deg);
  }
  50% {
    transform: rotateY(90deg);
  }
  100% {
    transform: rotateY(0deg);
  }
}
</style>
