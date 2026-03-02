<template>
  <view class="zsg" ref="wrapEl" :style="wrapStyle" @touchmove.stop.prevent="onWrapMove">
    <view class="zsg__inner" :style="innerStyle">
      <view
        v-for="(it, i) in state"
        :key="getKey(it, i)"
        class="zsg__item"
        :class="[
          props.ghost && dragging && dragKey === getKey(it, i) ? 'is-ghost' : '',
          dragging && dragKey === getKey(it, i) ? 'is-drag' : '',
          isDisabled(it, i) ? 'is-disabled' : ''
        ]"
        :style="itemStyle(i, it)"
        @touchstart.stop="onTouchStart($event, i, it)"
        @touchmove.stop.prevent="onTouchMove($event)"
        @touchend.stop="onTouchEnd"
        @touchcancel.stop="onTouchEnd"
        @mousedown.stop.prevent="onMouseDown($event, i, it)"
      >
        <!-- delete -->
        <view v-if="props.deletable" class="zsg__del" @tap.stop="onDelete(i, it)">
          <text class="zsg__del-txt">×</text>
        </view>

        <!-- handle -->
        <view
          v-if="useHandle"
          class="zsg__handle"
          @touchstart.stop="onHandleStart($event, i, it)"
          @mousedown.stop.prevent="onHandleMouseDown($event, i, it)"
        >
          <view class="zsg__dots">
            <view class="zsg__dot" v-for="n in 6" :key="n" />
          </view>
        </view>

        <slot :item="it" :index="i" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type AnyItem = Record<string, any>
type Size = number | string

const props = withDefaults(
  defineProps<{
    modelValue?: AnyItem[]
    /** unique key field in item (recommended: id) */
    keyField?: string

    /** columns */
    columns?: number
    /** gap between items */
    gap?: Size
    /** padding of container */
    padding?: Size
    /** container height (px/rpx). If empty, auto calculate based on items. */
    containerHeight?: Size
    /** fixed item height (px/rpx). If empty, will use itemWidth (square). */
    itemHeight?: Size
    /** fixed item width (px/rpx). If empty, auto calc by container width. */
    itemWidth?: Size

    /** drag behavior */
    draggable?: boolean
    /** start mode: longpress | immediate | handle */
    trigger?: 'longpress' | 'immediate' | 'handle'
    /** start dragging after long press (ms). Only used when trigger='longpress'. */
    longPress?: number
    /** use drag handle to start (kept for compatibility) */
    handle?: boolean
    /** scale the dragged item */
    scale?: number
    /** show ghost placeholder at original place */
    ghost?: boolean

    /** deletion */
    deletable?: boolean

    /** disable drag for some items */
    disabledIndexes?: number[]
    disabledKeyValues?: (string | number)[]

    /** z-index for dragged item */
    dragZ?: number

    /** vibration on pick */
    vibrate?: boolean
  }>(),
  {
    modelValue: () => [],
    keyField: 'id',

    columns: 4,
    gap: 12,
    padding: 12,
    containerHeight: '',
    itemHeight: '',
    itemWidth: '',

    draggable: true,
    trigger: 'longpress',
    longPress: 260,
    handle: false,
    scale: 1.05,
    ghost: true,

    deletable: false,

    disabledIndexes: () => [],
    disabledKeyValues: () => [],

    dragZ: 999,

    vibrate: false
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: AnyItem[]): void
  (e: 'change', payload: { list: AnyItem[]; from: number; to: number }): void
  (e: 'end', payload: { list: AnyItem[] }): void
  (e: 'delete', payload: { index: number; item: AnyItem; list: AnyItem[] }): void
  (e: 'tap', payload: { index: number; item: AnyItem }): void
}>()

function toPx(v: Size, unit = 'rpx'): number {
  if (v == null || v === '') return 0
  if (typeof v === 'number') return unit === 'rpx' ? uni.upx2px(v) : v
  const s = String(v).trim()
  if (s.endsWith('rpx')) return uni.upx2px(parseFloat(s))
  if (s.endsWith('px')) return parseFloat(s)
  if (/^\d+(\.\d+)?$/.test(s)) return uni.upx2px(parseFloat(s))
  return 0
}

function vib() {
  if (!props.vibrate) return
  try {
    // @ts-ignore
    uni.vibrateShort && uni.vibrateShort({ type: 'heavy' })
  } catch (e) {}
}

function getKey(it: AnyItem, i: number) {
  const k = props.keyField || 'id'
  const v = it?.[k]
  return v != null ? String(v) : String(i)
}

function isDisabled(it: AnyItem, i: number) {
  if (!props.draggable) return true
  if (props.disabledIndexes?.includes(i)) return true
  const raw = it?.[props.keyField || 'id']
  if (props.disabledKeyValues?.includes(raw)) return true
  const k = getKey(it, i)
  if (props.disabledKeyValues?.includes(k)) return true
  return false
}

const useHandle = computed(() => props.trigger === 'handle' || !!props.handle)

const wrapEl = ref<any>(null)
const wrapWidth = ref(0)

const state = ref<AnyItem[]>([])
watch(
  () => props.modelValue,
  (v) => {
    state.value = Array.isArray(v) ? v.slice() : []
  },
  { immediate: true, deep: true }
)

function setModel(list: AnyItem[]) {
  state.value = list.slice()
  emit('update:modelValue', state.value.slice())
}

function clampCols(n: any) {
  const x = Number(n)
  if (!isFinite(x)) return 4
  return Math.max(1, Math.min(8, Math.floor(x)))
}

const cols = computed(() => clampCols(props.columns))
const gapPx = computed(() => toPx(props.gap))
const padPx = computed(() => toPx(props.padding))

const itemW = ref(0)
const itemH = ref(0)
const startXPad = ref(0) // 实际起始 x（用于让左右剩余空间对等）

async function measure() {
  await nextTick()
  const ins = getCurrentInstance()
  const q = uni.createSelectorQuery().in(ins)

  const apply = (rect: any) => {
    if (!rect) return
    wrapWidth.value = rect.width || 0

    const wFixed = toPx(props.itemWidth)
    const hFixed = toPx(props.itemHeight)

    // 内部可用宽度（减去左右 padding）
    const innerW = Math.max(0, wrapWidth.value - padPx.value * 2)
    const totalGap = gapPx.value * (cols.value - 1)

    // 当前 cols 下允许的最大单元宽度（永远不允许超过，避免最后一列溢出）
    const maxAutoW = Math.max(0, Math.floor((innerW - totalGap) / cols.value))

    // 如果用户传了 itemWidth，也需要做上限裁剪，否则会稳定溢出
    const w = (wFixed > 0) ? Math.min(wFixed, maxAutoW) : maxAutoW
    const h = (hFixed > 0) ? hFixed : w

    itemW.value = Math.max(0, w)
    itemH.value = Math.max(0, h)

    // 把余数像素平均分到左右，保证左右留白对等
    const used = itemW.value * cols.value + totalGap
    const rest = Math.max(0, innerW - used)
    startXPad.value = padPx.value + rest / 2

    console.log('measure:', {
      wrapWidth: wrapWidth.value,
      innerW,
      cols: cols.value,
      pad: padPx.value,
      gap: gapPx.value,
      totalGap,
      wFixed,
      maxAutoW,
      itemW: itemW.value,
      itemH: itemH.value,
      used,
      rest,
      startXPad: startXPad.value
    })
  }

  // 优先测量 inner（更接近定位参照系），失败再测量外层
  q.select('.zsg__inner').boundingClientRect((rect: any) => {
    if (rect && rect.width) apply(rect)
    else {
      const q2 = uni.createSelectorQuery().in(ins)
      q2.select('.zsg').boundingClientRect((r: any) => apply(r)).exec()
    }
  }).exec()
}

onMounted(() => {
  measure()
  // #ifdef H5
  window.addEventListener('resize', measure)
  // #endif
})

onBeforeUnmount(() => {
  // #ifdef H5
  window.removeEventListener('resize', measure)
  // #endif
})

watch(
  () => [props.columns, props.gap, props.padding, props.itemWidth, props.itemHeight],
  () => measure(),
  { deep: true }
)

function posOf(index: number) {
  const c = cols.value
  const col = index % c
  const row = Math.floor(index / c)
  // x 起点使用 startXPad：把余数像素平均分到左右，保证留白对等
  const x = startXPad.value + col * (itemW.value + gapPx.value)
  const y = padPx.value + row * (itemH.value + gapPx.value)
  return { x, y }
}

const rows = computed(() => Math.ceil((state.value.length || 0) / cols.value))

const innerH = computed(() => {
  const r = rows.value
  if (r <= 0) return 0
  return padPx.value * 2 + r * itemH.value + (r - 1) * gapPx.value
})

const wrapStyle = computed(() => {
  return {
    position: 'relative',
    width: '100%'
  } as any
})

const innerStyle = computed(() => {
  const customHeight = toPx(props.containerHeight)
  const h = customHeight > 0 ? customHeight : innerH.value

  return {
    position: 'relative',
    width: '100%',
    height: `${h}px`,
    boxSizing: 'border-box'
  } as any
})

// ===== Drag State =====
const dragging = ref(false)
const dragIndex = ref(-1)
const dragKey = ref('')
const startX = ref(0)
const startY = ref(0)
const offsetX = ref(0)
const offsetY = ref(0)
const dragX = ref(0)
const dragY = ref(0)
let pressTimer: any = null

function clearPressTimer() {
  if (pressTimer) {
    clearTimeout(pressTimer)
    pressTimer = null
  }
}

function getPoint(e: any) {
  const t = e?.touches?.[0] || e?.changedTouches?.[0]
  if (t) return { x: t.clientX ?? t.pageX ?? 0, y: t.clientY ?? t.pageY ?? 0 }
  return { x: e?.clientX ?? 0, y: e?.clientY ?? 0 }
}

function startDrag(i: number, it: AnyItem, p: { x: number; y: number }) {
  if (!props.draggable) return
  if (isDisabled(it, i)) return
  dragging.value = true
  dragIndex.value = i
  dragKey.value = getKey(it, i)

  const { x, y } = posOf(i)
  startX.value = p.x
  startY.value = p.y

  // measure container top-left
  const ins = getCurrentInstance()
  const q = uni.createSelectorQuery().in(ins)
  q.select('.zsg').boundingClientRect((rect: any) => {
    const left = rect?.left ?? 0
    const top = rect?.top ?? 0
    offsetX.value = p.x - (left + x)
    offsetY.value = p.y - (top + y)
    dragX.value = x
    dragY.value = y
    vib()
  }).exec()
}

function maybeStartDrag(i: number, it: AnyItem, e: any) {
  clearPressTimer()
  if (!props.draggable) return
  if (props.trigger !== 'longpress') {
    startDrag(i, it, getPoint(e))
    return
  }
  const p = getPoint(e)
  if (props.longPress <= 0) {
    startDrag(i, it, p)
    return
  }
  pressTimer = setTimeout(() => {
    startDrag(i, it, p)
  }, props.longPress)
}

function onTouchStart(e: any, i: number, it: AnyItem) {
  if (useHandle.value) return
  if (props.trigger === 'immediate') {
    clearPressTimer()
    startDrag(i, it, getPoint(e))
    return
  }
  maybeStartDrag(i, it, e)
}

function onHandleStart(e: any, i: number, it: AnyItem) {
  clearPressTimer()
  if (props.trigger === 'longpress' && props.longPress > 0) {
    const p = getPoint(e)
    pressTimer = setTimeout(() => startDrag(i, it, p), props.longPress)
  } else {
    startDrag(i, it, getPoint(e))
  }
}

function calcToIndex(x: number, y: number) {
  const w = itemW.value + gapPx.value
  const h = itemH.value + gapPx.value

  // 以 startXPad / pad 为坐标原点，避免列计算偏移导致越界
  const cx = x + itemW.value / 2 - startXPad.value
  const cy = y + itemH.value / 2 - padPx.value

  let col = Math.round(cx / w)
  let row = Math.round(cy / h)

  col = Math.max(0, Math.min(cols.value - 1, col))
  row = Math.max(0, row)

  const idx = row * cols.value + col
  return Math.max(0, Math.min(state.value.length - 1, idx))
}

function move(arr: AnyItem[], from: number, to: number) {
  if (from === to) return arr
  const item = arr.splice(from, 1)[0]
  arr.splice(to, 0, item)
  return arr
}

function onTouchMove(e: any) {
  if (!dragging.value) {
    // if user moves before longpress triggers -> cancel
    const p = getPoint(e)
    const dx = Math.abs(p.x - startX.value)
    const dy = Math.abs(p.y - startY.value)
    if (dx + dy > 8) clearPressTimer()
    return
  }
  const p = getPoint(e)
  const ins = getCurrentInstance()
  const q = uni.createSelectorQuery().in(ins)
  q.select('.zsg').boundingClientRect((rect: any) => {
    const left = rect?.left ?? 0
    const top = rect?.top ?? 0
    const x = p.x - left - offsetX.value
    const y = p.y - top - offsetY.value

    dragX.value = x
    dragY.value = y

    const to = calcToIndex(x, y)
    const from = dragIndex.value
    if (to !== from && to >= 0 && to < state.value.length) {
      const next = move(state.value.slice(), from, to)
      setModel(next)
      dragIndex.value = to
      emit('change', { list: next.slice(), from, to })
    }
  }).exec()
}

function onTouchEnd() {
  clearPressTimer()
  if (!dragging.value) return
  const list = state.value.slice()
  dragging.value = false
  dragIndex.value = -1
  dragKey.value = ''
  emit('end', { list })
}

function onDelete(i: number, it: AnyItem) {
  const list = state.value.slice()
  list.splice(i, 1)
  setModel(list)
  emit('delete', { index: i, item: it, list })
  nextTick(() => measure())
}

// ===== mouse support (H5) =====
let mouseMove: any = null
let mouseUp: any = null

function onMouseDown(e: any, i: number, it: AnyItem) {
  if (useHandle.value) return
  clearPressTimer()
  if (props.trigger === 'longpress') {
    const p = getPoint(e)
    pressTimer = setTimeout(() => startDrag(i, it, p), props.longPress)
  } else {
    startDrag(i, it, getPoint(e))
  }

  mouseMove = (ev: any) => onTouchMove(ev)
  mouseUp = () => onMouseUp()

  // #ifdef H5
  window.addEventListener('mousemove', mouseMove)
  window.addEventListener('mouseup', mouseUp)
  // #endif
}

function onHandleMouseDown(e: any, i: number, it: AnyItem) {
  clearPressTimer()
  startDrag(i, it, getPoint(e))

  mouseMove = (ev: any) => onTouchMove(ev)
  mouseUp = () => onMouseUp()

  // #ifdef H5
  window.addEventListener('mousemove', mouseMove)
  window.addEventListener('mouseup', mouseUp)
  // #endif
}

function onMouseUp() {
  // #ifdef H5
  if (mouseMove) window.removeEventListener('mousemove', mouseMove)
  if (mouseUp) window.removeEventListener('mouseup', mouseUp)
  // #endif
  mouseMove = null
  mouseUp = null
  onTouchEnd()
}

function onWrapMove() {
  // prevent scroll while dragging
}
function onTouchCancel() {
  clearPressTimer()
  onTouchEnd()
}

function itemStyle(i: number, it: AnyItem) {
  const key = getKey(it, i)
  const { x, y } = posOf(i)

  const isDrag = dragging.value && dragKey.value === key
  const tx0 = isDrag ? dragX.value : x
  const ty = isDrag ? dragY.value : y

  // 真实宽度：保持与计算出来的 itemW 一致（不再用 -2 这种拍脑袋修补）
  const w = Math.max(0, Math.floor(itemW.value))

  // 兜底：永远不允许超出容器左右边界（尤其是最后一列）
  const minTx = startXPad.value
  const maxTx = Math.max(minTx, wrapWidth.value - padPx.value - w)
  const tx = Math.min(Math.max(tx0, minTx), maxTx)

  return {
    width: `${w}px`,
    height: itemH.value > 0 ? `${itemH.value}px` : 'auto',
    transform: `translate3d(${tx}px, ${ty}px, 0)`,
    zIndex: isDrag ? props.dragZ : 1,
    transitionDuration: isDrag ? '0ms' : '200ms',
    transitionTimingFunction: 'cubic-bezier(0.2, 0.9, 0.2, 1)',
    transitionProperty: 'transform',
    ...(isDrag ? { transformOrigin: 'center', scale: String(props.scale) } : {})
  } as any
}
</script>

<style scoped>
.zsg{
  width: 100%;
  overflow: hidden;
  -webkit-user-select: none;
  user-select: none;
}
.zsg__inner{
  position: relative;
  width: 100%;
  box-sizing: border-box;
}
.zsg__item{
  position: absolute;
  left: 0;
  top: 0;
  box-sizing: border-box;
  overflow: hidden;
  min-width: 0;
}
.zsg__item.is-ghost{
  opacity: 0.65;
}
.zsg__item.is-disabled{
  opacity: 0.55;
}

/* delete */
.zsg__del{
  position: absolute;
  left: 10rpx;
  top: 10rpx;
  width: 38rpx;
  height: 38rpx;
  border-radius: 999rpx;
  background: rgba(255, 59, 48, 0.92);
  display:flex;
  align-items:center;
  justify-content:center;
  z-index: 5;
}
.zsg__del-txt{
  color:#fff;
  font-size: 30rpx;
  font-weight: 900;
  line-height: 1;
  margin-top: -2rpx;
}

/* handle */
.zsg__handle{
  position:absolute;
  right: 10rpx;
  top: 10rpx;
  width: 46rpx;
  height: 46rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,0.06);
  display:flex;
  align-items:center;
  justify-content:center;
  z-index: 5;
}
.zsg__dots{
  width: 24rpx;
  height: 24rpx;
  display:flex;
  flex-wrap: wrap;
  gap: 4rpx;
}
.zsg__dot{
  width: 6rpx;
  height: 6rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,0.42);
}
</style>
