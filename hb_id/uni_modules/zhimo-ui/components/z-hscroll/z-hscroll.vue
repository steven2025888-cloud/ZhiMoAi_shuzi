<template>
  <view
    class="z-hscroll"
    :style="{ marginTop: marginTop + 'rpx', marginBottom: marginBottom + 'rpx' }"
    ref="rootRef"
  >
    <!-- #ifndef APP-NVUE -->
    <scroll-view
      class="z-hscroll__view"
      :scroll-x="true"
      :show-scrollbar="false"
      :upper-threshold="0"
      :lower-threshold="0"
      @scroll="onScroll"
      @scrolltoupper="onScrollToUpper"
      @scrolltolower="onScrollToLower"
    >
      <view class="z-hscroll__wrap">
        <slot />
      </view>
    </scroll-view>
    <!-- #endif -->

    <!-- #ifdef APP-NVUE -->
    <scroller
      class="z-hscroll__view"
      ref="scrollerRef"
      scroll-direction="horizontal"
      :show-scrollbar="false"
      :offset-accuracy="2"
      @scroll="onNvueScroll"
    >
      <view class="z-hscroll__wrap">
        <slot />
      </view>
    </scroller>
    <!-- #endif -->

    <view class="z-hscroll__bar-wrap" :style="{ marginTop: scrollGap + 'rpx' }" v-if="scroll">
      <view
        class="z-hscroll__bar"
        :class="{ 'z-hscroll__radius': scrollCap === 'round' }"
        :style="{ height: blockHeightPx + 'px', width: bgWidthPx + 'px', background: background }"
      >
        <view
          class="z-hscroll__indicator"
          :class="{ 'z-hscroll__radius': scrollCap === 'round', 'z-hscroll__indicator-default': !scrollBarColor }"
          :style="indicatorStyle"
          ref="indicatorRef"
        />
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount, getCurrentInstance } from 'vue'

defineOptions({ name: 'z-hscroll' })

const emit = defineEmits(['scrolltoupper', 'scrolltolower'])

const props = defineProps({
  marginTop: { type: [String, Number], default: 0 },
  marginBottom: { type: [String, Number], default: 0 },

  /** 是否显示底部滚动条 */
  scroll: { type: Boolean, default: true },

  /** 滚动条背景长度（rpx） */
  scrollWidth: { type: [String, Number], default: 96 },

  /** 滚动条滑块长度（rpx） */
  scrollBarWidth: { type: [String, Number], default: 32 },

  /** 滚动条高度（rpx） */
  scrollHeight: { type: [String, Number], default: 8 },

  /** square | round */
  scrollCap: { type: String, default: 'round' },

  /** 滑块颜色；不传则用 CSS 变量默认色 */
  scrollBarColor: { type: String, default: '' },

  /** 背景颜色 */
  background: { type: String, default: '#EEEEEE' },

  /** 滚动条距离内容间距（rpx） */
  scrollGap: { type: [String, Number], default: 24 },
})

const rootRef = ref(null)
const indicatorRef = ref(null)
// #ifdef APP-NVUE
const scrollerRef = ref(null)
// #endif

const widthPx = ref(0)
const bgWidthPx = ref(0)
const blockWidthPx = ref(0)
const blockHeightPx = ref(0)

// #ifndef APP-NVUE
const transform = ref('translate3d(0,0,0)')
// #endif

function toEvenPxFromRpx(v) {
  let px = Math.floor(uni.upx2px(Number(v || 0)))
  return px % 2 === 0 ? px : px + 1
}

function recalcBar() {
  bgWidthPx.value = toEvenPxFromRpx(props.scrollWidth || 96)
  blockWidthPx.value = toEvenPxFromRpx(props.scrollBarWidth || 32)
  blockHeightPx.value = toEvenPxFromRpx(props.scrollHeight || 8)
}

recalcBar()

watch(
  () => [props.scrollWidth, props.scrollBarWidth, props.scrollHeight],
  () => {
    recalcBar()
    // 内容尺寸改变时，重新测一次容器宽度，避免计算偏差
    init()
  }
)

const indicatorStyle = computed(() => {
  let style = `height:${blockHeightPx.value}px;width:${blockWidthPx.value}px;`
  const color = props.scrollBarColor
  if (color) style += `background:${color};`

  // #ifndef APP-NVUE
  style += `transform:${transform.value};`
  // #endif

  return style
})

function emitEdge(edge) {
  emit(edge === 'left' ? 'scrolltoupper' : 'scrolltolower')
}

/** 重新初始化（外部也可调用） */
function init() {
  setTimeout(() => getSize(), 80)
}

defineExpose({ init })

// #ifndef APP-NVUE
function onScroll(e) {
  if (!props.scroll) return
  const d = e.detail || {}
  const scrollWidth = d.scrollWidth || 0
  const scrollLeft = d.scrollLeft || 0
  const w = widthPx.value || 0
  const barW = bgWidthPx.value
  const blkW = blockWidthPx.value

  const denom = scrollWidth - w
  const x = denom > 0 ? (scrollLeft / denom) * (barW - blkW) : 0
  transform.value = `translate3d(${x}px,0,0)`
}

function onScrollToUpper() {
  emitEdge('left')
  transform.value = 'translate3d(0,0,0)'
}

function onScrollToLower() {
  emitEdge('right')
  const x = bgWidthPx.value - blockWidthPx.value
  transform.value = `translate3d(${x}px,0,0)`
}
// #endif

// #ifdef APP-NVUE
const BindingX = uni.requireNativePlugin('bindingx')
const dom = uni.requireNativePlugin('dom')
let bindToken = null
let bound = false

function getNvueEl(r) {
  return r?.value ? r.value.ref : null
}

function bindIfNeeded(contentWidth) {
  if (!props.scroll || bound) return
  const anchor = getNvueEl(scrollerRef)
  const element = getNvueEl(indicatorRef)
  if (!anchor || !element) return
  const w = widthPx.value
  if (!w || contentWidth <= w) return

  const barAllMove = bgWidthPx.value - blockWidthPx.value
  if (barAllMove <= 0) return

  const platform = (uni.getSystemInfoSync().platform || '').toLowerCase()
  // 原实现：iOS 需要除以 2 才匹配位移
  const actionNum = platform === 'ios' ? 2 : 1
  const expression = `(x / ${actionNum}) / ${contentWidth - w} * ${barAllMove}`

  try {
    const res = BindingX.bind({
      anchor,
      eventType: 'scroll',
      props: [{ element, property: 'transform.translateX', expression }],
    })
    bindToken = res && res.token
    bound = true
  } catch (err) {
    // 兜底：不阻断滚动
    bound = false
  }
}

function onNvueScroll(e) {
  const scrollLeft = e?.contentOffset?.x ?? 0
  const contentWidth = e?.contentSize?.width ?? 0

  bindIfNeeded(contentWidth)

  if (scrollLeft + widthPx.value >= contentWidth) {
    emitEdge('right')
  } else if (scrollLeft <= 0) {
    emitEdge('left')
  }
}

onBeforeUnmount(() => {
  try {
    if (bindToken) BindingX.unbind({ token: bindToken })
  } catch (e) {}
  bindToken = null
  bound = false
})
// #endif

function getSize() {
  // #ifndef APP-NVUE
  uni.createSelectorQuery()
    // #ifndef MP-ALIPAY
    .in(getCurrentInstanceProxy())
    // #endif
    .select('.z-hscroll')
    .boundingClientRect()
    .exec((ret) => {
      const w = ret?.[0]?.width || 0
      if (w) widthPx.value = w
    })
  // #endif

  // #ifdef APP-NVUE
  dom.getComponentRect(rootRef.value, (ret) => {
    const size = ret?.size
    if (size?.width) widthPx.value = size.width
  })
  // #endif
}

// 为了兼容 uni-app createSelectorQuery().in(this) 的 this，拿到当前组件代理
function getCurrentInstanceProxy() {
  const inst = getCurrentInstance()
  return inst && inst.proxy ? inst.proxy : undefined
}

onMounted(async () => {
  await nextTick()
  init()
})
</script>

<style scoped>
/* #ifndef APP-NVUE */
::-webkit-scrollbar {
  width: 0 !important;
  height: 0 !important;
  color: transparent !important;
  display: none;
}
/* #endif */

.z-hscroll,
.z-hscroll__view {
  /* #ifndef APP-NVUE */
  display: flex;
  flex-shrink: 0;
  /* #endif */
  flex-direction: row;
}

.z-hscroll__wrap {
  /* #ifndef APP-NVUE */
  display: inline-flex;
  flex-shrink: 0;
  align-items: flex-start;
  /* #endif */
  /* #ifdef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: column;
}
.z-hscroll {
  flex-direction: column;
  align-items: stretch;
  /* #ifndef APP-NVUE */
  align-content: flex-start;
  width: 100%;
  /* #endif */
}

.z-hscroll__bar-wrap {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  justify-content: center;
}

.z-hscroll__bar {
  position: relative;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  transform: translateZ(0);
  /* #endif */
}

.z-hscroll__radius {
  border-radius: 100px;
}

.z-hscroll__indicator {
  position: absolute;
  left: 0;
  top: 0;
  /* #ifndef APP-NVUE */
  transition: all 0.1s linear;
  /* #endif */
}

/* 不传 scrollBarColor 时用主题色（你们自己项目可定义这个变量） */
.z-hscroll__indicator-default {
  background-color: var(--zui-color-primary, #465cff) !important;
}
</style>
