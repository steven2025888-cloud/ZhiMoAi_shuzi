<template>
  <view class="z-wf" :style="wrapStyle">
    <slot />
  </view>
</template>

<script setup>
import { computed, reactive, provide, getCurrentInstance, nextTick, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  /** 列数（默认2列） */
  columns: { type: [Number, String], default: 2 },
  /** 列间距/行间距（rpx） */
  gap: { type: [Number, String], default: 24 },
  /** 外边距（左右内边距 rpx） */
  paddingX: { type: [Number, String], default: 0 },
  /** 上下间距（rpx） */
  paddingTop: { type: [Number, String], default: 0 },
  paddingBottom: { type: [Number, String], default: 0 },
  /** 是否从前面插入（用于上拉加载历史） */
  prepend: { type: Boolean, default: false },
  /** 触发重新布局的 key（列表变化时可变更此值） */
  layoutKey: { type: [String, Number], default: '' },
  /** z-index（用于和页面其它层级冲突时调高） */
  zIndex: { type: [Number, String], default: 1 }
})

const emit = defineEmits(['init', 'end'])

const inst = getCurrentInstance()
const uid = Math.random().toString(36).slice(2, 8)

const state = reactive({
  heightPx: 0,
  itemWidthPx: 0,
  cols: 2,
  gapPx: 0,
  padXPx: 0,
  padTopPx: 0,
  padBottomPx: 0,
  colHeights: [],
  // itemId => { left, top, transform, width, opacity }
  itemStyleMap: new Map(),
  // order
  items: [],
  // for prepend
  prependItems: []
})

function toPxByRpx(v) {
  const n = Number(v || 0)
  return Math.round(uni.upx2px(n))
}

function clamp(n, min, max) { return Math.max(min, Math.min(max, n)) }

function calcParams() {
  const sys = uni.getSystemInfoSync()
  const cols = clamp(parseInt(String(props.columns), 10) || 2, 1, 6)
  const gapPx = toPxByRpx(props.gap)
  const padXPx = toPxByRpx(props.paddingX)
  const padTopPx = toPxByRpx(props.paddingTop)
  const padBottomPx = toPxByRpx(props.paddingBottom)

  const totalGap = gapPx * (cols - 1)
  const totalPad = padXPx * 2
  const usable = Math.max(0, sys.windowWidth - totalPad - totalGap)
  const itemWidthPx = usable / cols

  state.cols = cols
  state.gapPx = gapPx
  state.padXPx = padXPx
  state.padTopPx = padTopPx
  state.padBottomPx = padBottomPx
  state.itemWidthPx = itemWidthPx
  state.colHeights = Array.from({ length: cols }).map(() => padTopPx)

  emit('init', { itemWidth: itemWidthPx })
}

calcParams()

function resetLayout() {
  state.heightPx = 0
  state.itemStyleMap.clear()
  state.items = []
  state.prependItems = []
  state.colHeights = Array.from({ length: state.cols }).map(() => state.padTopPx)
}

function findShortestCol() {
  let minIdx = 0
  let min = state.colHeights[0] || 0
  for (let i = 1; i < state.colHeights.length; i++) {
    const h = state.colHeights[i]
    if (h < min) { min = h; minIdx = i }
  }
  return minIdx
}

function layoutOne(item) {
  const col = findShortestCol()
  const left = state.padXPx + col * (state.itemWidthPx + state.gapPx)

  // colHeights 记录的是「上一张卡片的底部位置」
  const baseTop = state.colHeights[col] ?? state.padTopPx
  const top = baseTop + (baseTop === state.padTopPx ? 0 : state.gapPx)

  const t = `translate3d(${left}px, ${top}px, 0)`
  const style = {
    width: `${state.itemWidthPx}px`,
    transform: t,
    opacity: item._show ? 1 : 0
  }
  state.itemStyleMap.set(item.id, style)

  // 更新本列底部高度
  const h = Number(item.height || 0)
  state.colHeights[col] = top + h

  const maxH = Math.max(...state.colHeights, state.padTopPx)
  state.heightPx = Math.ceil(maxH + state.padBottomPx)
}

function relayoutAll() {
  // reset heights
  state.colHeights = Array.from({ length: state.cols }).map(() => state.padTopPx)

  const use = props.prepend ? state.prependItems.concat(state.items) : state.items
  use.forEach((it) => layoutOne(it))
  emit('end', {})
}

function registerItem() {
  const id = `zwf_${uid}_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
  // init style (hidden until measured)
  state.itemStyleMap.set(id, {
    width: `${state.itemWidthPx}px`,
    transform: `translate3d(${state.padXPx}px, ${state.padTopPx}px, 0)`,
    opacity: 0
  })
  return id
}

function updateItemHeight(id, height) {
  if (!height) return
  // find in arrays, else create
  const list = props.prepend ? state.prependItems : state.items
  let item = list.find(x => x.id === id)
  if (!item) {
    item = { id, height: 0, _show: false }
    list.push(item)
  }
  item.height = height
  item._show = true
  // layout only this item if append and not prepend; otherwise full relayout
  if (!props.prepend) {
    // layout incrementally
    layoutOne(item)
    emit('end', {})
  } else {
    // prepend requires relayout
    relayoutAll()
  }
}

function getItemStyle(id) {
  return state.itemStyleMap.get(id) || {}
}

function getItemWidth() {
  return state.itemWidthPx
}

function requestRelayout() {
  nextTick(() => relayoutAll())
}

provide('zWaterfall', {
  registerItem,
  updateItemHeight,
  getItemStyle,
  getItemWidth,
  requestRelayout
})

watch(() => [props.columns, props.gap, props.paddingX, props.paddingTop, props.paddingBottom], () => {
  calcParams()
  nextTick(() => {
    // keep existing items but relayout
    // itemStyleMap will be overwritten during relayout
    state.itemStyleMap.clear()
    state.items.forEach(it => it._show = true)
    state.prependItems.forEach(it => it._show = true)
    relayoutAll()
  })
})

watch(() => props.layoutKey, () => {
  // 列表/布局参数变化：用已有的高度直接重排，避免样式被清空后全部堆叠
  nextTick(() => {
    state.itemStyleMap.clear()
    state.items.forEach(it => it._show = true)
    state.prependItems.forEach(it => it._show = true)
    relayoutAll()
  })
})

onBeforeUnmount(() => {
  resetLayout()
})

const wrapStyle = computed(() => {
  return {
    position: 'relative',
    width: '100%',
    height: state.heightPx ? `${state.heightPx}px` : 'auto',
    zIndex: Number(props.zIndex) || 1
  }
})
</script>

<style scoped>
.z-wf{
  width: 100%;
  position: relative;
  box-sizing: border-box;
}
</style>