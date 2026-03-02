<template>
  <view class="zcp-wrap" :style="{ width: px(sizePx), height: px(sizePx) }" @tap="onTap">
    <canvas
      class="zcp-canvas"
      :canvas-id="canvasId"
      :id="canvasId"
      :style="{ width: px(sizePx), height: px(sizePx) }"
    />
    <view v-if="showText" class="zcp-center">
      <slot>
        <text class="zcp-text" :style="{ fontSize: px(textSizePx), color: textColorComputed }">{{ displayText }}</text>
      </slot>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type LineCap = 'round' | 'butt' | 'square'

const props = defineProps({
  /** 0-100 */
  percent: { type: Number, default: 0 },
  /** 直径（rpx 或 px 数值）。默认 rpx */
  size: { type: [Number, String], default: 200 },
  /** 线条宽度（rpx 或 px 数值）。默认 rpx */
  strokeWidth: { type: [Number, String], default: 12 },
  /** 进度颜色 */
  color: { type: String, default: '#465CFF' },
  /** 背景轨道颜色 */
  background: { type: String, default: '#EEEEEE' },
  /**
   * 渐变：
   * - 传 string：与 color 组成线性渐变（color -> gradient）
   * - 传 array：多段渐变色（从左到右）
   */
  gradient: { type: [String, Array], default: '' },
  /** 起始角度（度），-90 表示从正上方开始 */
  startAngle: { type: Number, default: -90 },
  /** 扫过角度（度），360 为完整圆；270/180 可做仪表盘 */
  sweepAngle: { type: Number, default: 360 },
  /** 是否顺时针 */
  clockwise: { type: Boolean, default: true },
  /** 线帽 */
  lineCap: { type: String as unknown as () => LineCap, default: 'round' },

  /** 动画 */
  animated: { type: Boolean, default: true },
  /** 动画时长（ms） */
  duration: { type: Number, default: 600 },

  /** 中心文字 */
  showText: { type: Boolean, default: true },
  /** 自定义文字（为空则显示 xx%） */
  text: { type: String, default: '' },
  /** 文字颜色（为空自动跟随 color） */
  textColor: { type: String, default: '' },
  /** 文字大小（rpx 或 px 数值） */
  textSize: { type: [Number, String], default: 28 },

  /** 防止 0 不显示：showText 时如果 percent=0 仍显示 0% */
  showZero: { type: Boolean, default: true }
})

const emit = defineEmits<{
  (e: 'change', payload: { percent: number }): void
  (e: 'tap'): void
}>()

const ins = getCurrentInstance()

const canvasId = `zcp_${Math.random().toString(36).slice(2, 10)}`
const sizePx = computed(() => toPx(props.size))
const strokePx = computed(() => clamp(toPx(props.strokeWidth), 1, sizePx.value))
const radiusPx = computed(() => Math.max(0, (sizePx.value - strokePx.value) / 2))

const textSizePx = computed(() => toPx(props.textSize))
const textColorComputed = computed(() => props.textColor || props.color)

const targetPercent = computed(() => clamp(props.percent, 0, 100))

const displayPercent = ref(targetPercent.value)
let timer: any = null

const displayText = computed(() => {
  const p = Math.round(displayPercent.value)
  if (!props.showZero && p === 0) return ''
  return props.text ? props.text : `${p}%`
})

function px(n: number) {
  return `${Math.round(n)}px`
}
function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n))
}
function isNumberLike(v: any) {
  return typeof v === 'number' || (typeof v === 'string' && v.trim() !== '' && !isNaN(Number(v)))
}
/** 数字默认按 rpx 处理；如果传 "20px" 则按 px；传 "20rpx" 按 rpx */
function toPx(v: any): number {
  if (typeof v === 'string') {
    const s = v.trim()
    if (s.endsWith('px')) return Number(s.replace('px', '')) || 0
    if (s.endsWith('rpx') || s.endsWith('upx')) return uni.upx2px(Number(s.replace(/(rpx|upx)$/, '')) || 0)
    if (isNumberLike(s)) return uni.upx2px(Number(s))
    return 0
  }
  if (typeof v === 'number') return uni.upx2px(v)
  return 0
}

function stopAnim() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function draw(percentValue: number) {
  const w = sizePx.value
  const sw = strokePx.value
  const r = radiusPx.value
  if (!w || !r) return

  // @ts-ignore
  const ctx = uni.createCanvasContext(canvasId, ins)
  // 清空
  ctx.clearRect(0, 0, w, w)

  const cx = w / 2
  const cy = w / 2

  const start = deg2rad(props.startAngle)
  const sweep = deg2rad(clamp(props.sweepAngle, 0, 360))
  const progSweep = sweep * clamp(percentValue, 0, 100) / 100

  const endTrack = props.clockwise ? (start + sweep) : (start - sweep)
  const endProg = props.clockwise ? (start + progSweep) : (start - progSweep)

  const anti = !props.clockwise

  // 轨道
  ctx.beginPath()
  ctx.setLineWidth(sw)
  ctx.setLineCap(props.lineCap)
  ctx.setStrokeStyle(props.background)
  ctx.arc(cx, cy, r, start, endTrack, anti)
  ctx.stroke()

  // 进度
  if (percentValue > 0) {
    ctx.beginPath()
    ctx.setLineWidth(sw)
    ctx.setLineCap(props.lineCap)

    const strokeStyle = buildStrokeStyle(ctx, w)
    // @ts-ignore
    ctx.setStrokeStyle(strokeStyle)

    ctx.arc(cx, cy, r, start, endProg, anti)
    ctx.stroke()
  }

  ctx.draw()
}

function buildStrokeStyle(ctx: any, w: number) {
  // 渐变优先
  const g = props.gradient as any
  if (Array.isArray(g) && g.length >= 2) {
    const grd = ctx.createLinearGradient(0, 0, w, 0)
    const stops = g.filter(Boolean)
    const n = stops.length
    stops.forEach((c: string, i: number) => {
      const t = n === 1 ? 1 : i / (n - 1)
      grd.addColorStop(t, c)
    })
    return grd
  }
  if (typeof g === 'string' && g.trim()) {
    const grd = ctx.createLinearGradient(0, 0, w, 0)
    grd.addColorStop(0, props.color)
    grd.addColorStop(1, g.trim())
    return grd
  }
  return props.color
}

function deg2rad(d: number) {
  return (d * Math.PI) / 180
}

function animateTo(nextP: number) {
  stopAnim()
  const from = displayPercent.value
  const to = nextP
  if (!props.animated || props.duration <= 0) {
    displayPercent.value = to
    draw(to)
    emit('change', { percent: to })
    return
  }
  const duration = props.duration
  const startTs = Date.now()
  timer = setInterval(() => {
    const t = Date.now() - startTs
    const p = clamp(t / duration, 0, 1)
    // easeOutCubic
    const e = 1 - Math.pow(1 - p, 3)
    const cur = from + (to - from) * e
    displayPercent.value = cur
    draw(cur)
    if (p >= 1) {
      stopAnim()
      displayPercent.value = to
      draw(to)
      emit('change', { percent: to })
    }
  }, 16)
}

function refresh() {
  nextTick(() => draw(displayPercent.value))
}
defineExpose({ refresh, draw: () => draw(displayPercent.value) })

function onTap() {
  emit('tap')
}

onMounted(async () => {
  await nextTick()
  draw(displayPercent.value)
})

watch(targetPercent, (v) => {
  animateTo(v)
})

watch(
  () => [props.size, props.strokeWidth, props.startAngle, props.sweepAngle, props.clockwise, props.lineCap, props.color, props.background, props.gradient],
  () => {
    refresh()
  }
)

onBeforeUnmount(() => stopAnim())
</script>

<style scoped>
.zcp-wrap{
  position: relative;
  display:flex;
  align-items:center;
  justify-content:center;
}
.zcp-canvas{
  width: 100%;
  height: 100%;
}
.zcp-center{
  position:absolute;
  left:0; right:0; top:0; bottom:0;
  display:flex;
  align-items:center;
  justify-content:center;
  pointer-events:none;
}
.zcp-text{
  font-weight:600;
  line-height:1;
}
</style>
