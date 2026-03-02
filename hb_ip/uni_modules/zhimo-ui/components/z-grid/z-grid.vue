<template>
  <view class="z-grid__wrap" :class="[isShow ? 'is-show' : 'is-hidden']">
    <view
      :id="elemId"
      ref="rootRef"
      class="z-grid"
      :class="[{ 'is-border': showBorder, 'is-between': between }]"
      :style="gridStyle"
    >
      <slot />

      <!-- #ifndef APP-VUE || H5 || MP-WEIXIN -->
      <template v-if="between && seats.length">
        <view
          v-for="n in seats"
          :key="n"
          class="z-grid__seat"
          :style="seatStyle"
        />
      </template>
      <!-- #endif -->
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onMounted, provide, ref, watch } from 'vue'

// #ifdef APP-NVUE
const dom = uni.requireNativePlugin('dom')
// #endif

type ClickDetail = { index: number }
type ClickEvent = { detail: ClickDetail }

const props = withDefaults(defineProps<{
  columns?: number
  showBorder?: boolean
  borderColor?: string
  square?: boolean
  between?: boolean
  emptyElements?: number | string
}>(), {
  columns: 3,
  showBorder: true,
  borderColor: '#EEEEEE',
  square: true,
  between: false,
  emptyElements: 0
})

const emit = defineEmits<{
  (e: 'click', evt: ClickEvent): void
}>()

const rootRef = ref<any>(null)
const elemId = `zg_${Math.ceil(Math.random() * 10e5).toString(36)}`

const width = ref<string>('0')
const height = ref<string>('')
const isShow = ref(false)
const seats = ref<number[]>([])

const gridStyle = computed(() => ({
  'border-left-color': props.borderColor,
  'border-top-color': props.borderColor
}))

const seatStyle = computed(() => {
  const w = width.value
  const h = height.value
  return `width:${w};${h ? `height:${h};` : ''}`
})

function buildSeats(val: number | string) {
  const n = Number(val)
  if (!n || n <= 0) {
    seats.value = []
    return
  }
  const arr: number[] = []
  for (let i = 0; i < n; i++) arr.push(i)
  seats.value = arr
}

function handleItemClick(evt: ClickEvent) {
  emit('click', evt)
}

async function init() {
  isShow.value = false
  await nextTick()

  // 某些端 selectorQuery 需要等一帧布局稳定
  setTimeout(() => {
    calcItemSize((w, h) => {
      width.value = w
      height.value = h
      isShow.value = true
    })
  }, 50)
}

function calcItemSize(done: (w: string, h: string) => void) {
  let isNoSupported = false
  // #ifdef MP-BAIDU || MP-TOUTIAO || MP-QQ || MP-KUAISHOU || MP-JD || MP-360 || MP-LARK
  isNoSupported = true
  // #endif

  const cols = Math.max(1, Number(props.columns) || 1)

  // #ifndef APP-NVUE
  // 默认用百分比（更快）
  let w = (100 / cols) + '%'
  let h = props.square ? height.value : ''

  // square 或某些端不支持 space-between 精细布局时，改用 px 宽度更稳定
  if (props.square || isNoSupported) {
    const inst = getCurrentInstance()
    const proxy = inst?.proxy as any

    uni.createSelectorQuery()
      // #ifndef MP-ALIPAY
      .in(proxy)
      // #endif
      .select(`#${elemId}`)
      .boundingClientRect()
      .exec((ret: any[]) => {
        const rect = ret?.[0]
        if (!rect?.width) {
          // 兜底：仍用百分比
          done(w, props.square ? '' : h)
          return
        }

        // 用 parseInt 避免部分安卓小数导致换行
        let px = (rect.width - 1) / cols
        px = parseInt(px * 10) / 10
        const pxStr = `${px}px`

        if (props.square) h = pxStr
        if (isNoSupported) w = pxStr

        done(w, h)
      })
  } else {
    done(w, h)
  }
  // #endif

  // #ifdef APP-NVUE
  dom.getComponentRect(rootRef.value, (res: any) => {
    const rectW = res?.size?.width || 0
    let px = (rectW - 1) / cols
    px = parseInt(px * 10) / 10
    const pxStr = `${px}px`
    const w = pxStr
    const h = props.square ? pxStr : ''
    done(w, h)
  })
  // #endif
}

// 提供给子项：响应式宽高 + 配置
provide('zGrid', {
  width,
  height,
  showBorder: computed(() => props.showBorder),
  borderColor: computed(() => props.borderColor),
  handleItemClick
})

watch(() => props.columns, () => init())
watch(() => props.emptyElements, (v) => buildSeats(v))
onMounted(() => {
  buildSeats(props.emptyElements)
  init()
})
</script>

<style scoped>
.z-grid__wrap {
  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  box-sizing: border-box;
  /* #endif */
  /* #ifdef APP-NVUE */
  flex: 1;
  /* #endif */
  flex-direction: column;

  /* #ifndef APP-NVUE */
  transition: opacity .2s ease-in-out;
  /* #endif */
}

.is-hidden { opacity: 0; }
.is-show { opacity: 1 !important; }

.z-grid {
  /* #ifndef APP-NVUE */
  display: flex;
  width: 100%;
  /* #endif */
  flex-direction: row;
  flex-wrap: wrap;
}

/* #ifndef APP-VUE || H5 || MP-WEIXIN */
.is-between { justify-content: space-between; }
/* #endif */

.is-border {
  position: relative;
  /* #ifdef APP-NVUE */
  border-left-style: solid;
  border-left-width: 0.5px;
  border-top-style: solid;
  border-top-width: 0.5px;
  /* #endif */
  /* #ifndef APP-NVUE */
  z-index: 1;
  border-left: 0;
  /* #endif */
}

/* #ifndef APP-NVUE */
.is-border::before {
  content: ' ';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 1px;
  border-top: 1px solid var(--z-color-border, #EEEEEE);
  transform-origin: 0 0;
  transform: scaleY(0.5);
  z-index: 1;
}

.is-border::after {
  content: ' ';
  position: absolute;
  left: 0;
  top: 0;
  width: 1px;
  height: 100%;
  border-left: 1px solid var(--z-color-border, #EEEEEE);
  transform-origin: 0 0;
  transform: scaleX(0.5);
}
/* #endif */
</style>
