<template>
  <view class="z-fab" @touchmove.stop.prevent="noop">
    <!-- mask -->
    <view
      v-if="mask"
      class="z-fab__mask"
      :class="{ 'z-fab__mask--show': isOpen }"
      :style="maskStyle"
      @tap.stop="onMaskTap"
    ></view>

    <!-- main wrap -->
    <!-- #ifdef APP-NVUE -->
    <view
      ref="fabRef"
      class="z-fab__wrap"
      :class="[position === 'left' ? 'z-fab__wrap--left' : 'z-fab__wrap--right']"
      :style="wrapStyle"
      @touchstart="onTouchStart"
      @touchmove.stop.prevent="onTouchMove"
      @touchend="onTouchEnd"
      @touchcancel="onTouchEnd"
    >
      <view
        ref="listRef"
        class="z-fab__list"
        :class="[
          isHidden ? 'z-fab__list--hidden' : '',
          isOpen ? 'z-fab__list--open' : '',
          position === 'left' ? 'z-fab__list--left' : 'z-fab__list--right'
        ]"
      >
        <view
          v-for="(it, idx) in items"
          :key="idx"
          class="z-fab__item"
          :class="[position === 'left' ? 'z-fab__item--left' : 'z-fab__item--right']"
          @tap.stop="onItemTap(idx)"
        >
          <text
            v-if="it.text"
            class="z-fab__text"
            :style="{ fontSize: (it.textSize || 28) + 'rpx', color: it.textColor || '#fff', textAlign: position === 'left' ? 'left' : 'right' }"
          >{{ it.text }}</text>

          <view
            class="z-fab__btn"
            :class="{ 'z-fab__btn--default': !getMainBg && !it.background }"
            :style="{ width: size + 'rpx', height: size + 'rpx', background: it.background || getMainBg }"
          >
            <z-icon v-if="it.icon" :name="it.icon" :size="it.iconSize || 64" :color="it.iconColor || '#fff'"></z-icon>
            <image
              v-else-if="it.image"
              :src="it.image"
              mode="widthFix"
              :style="{ width: (it.imageWidth || 56) + 'rpx', height: (it.imageHeight || 56) + 'rpx', borderRadius: (it.imageRadius || 0) + 'rpx' }"
            />
            <text
              v-else-if="it.abbr"
              class="z-fab__abbr"
              :style="{ fontSize: (it.abbrSize || 32) + 'rpx', lineHeight: (it.abbrSize || 32) + 'rpx', color: it.abbrColor || '#fff' }"
            >{{ it.abbr }}</text>

            <!-- #ifndef H5 -->
            <button
              v-if="it.openType"
              class="z-fab__opentype"
              :open-type="it.openType"
              :app-parameter="it.appParameter"
              :lang="it.lang"
              :sessionFrom="it.sessionFrom"
              :sendMessageTitle="it.sendMessageTitle"
              :sendMessagePath="it.sendMessagePath"
              :sendMessageImg="it.sendMessageImg"
              :showMessageCard="it.showMessageCard"
              @contact="emitContact"
              @opensetting="emitOpenSetting"
              @launchapp="emitLaunchApp"
            ></button>
            <!-- #endif -->
          </view>
        </view>
      </view>

      <view
        class="z-fab__main"
        :class="{ 'z-fab__btn--default': !getMainBg, 'z-fab__main--disabled': disabled }"
        :style="{ width: size + 'rpx', height: size + 'rpx', background: getMainBg }"
        @tap.stop="onMainTap"
      >
        <view class="z-fab__main-inner" :class="{ 'z-fab__main-inner--open': isOpen }" ref="mainInnerRef">
          <slot>
            <z-icon name="plus" :size="80" :color="color"></z-icon>
          </slot>
        </view>

        <!-- #ifndef H5 -->
        <button
          v-if="openType"
          class="z-fab__opentype"
          :open-type="openType"
          :app-parameter="appParameter"
          :lang="lang"
          :sessionFrom="sessionFrom"
          :sendMessageTitle="sendMessageTitle"
          :sendMessagePath="sendMessagePath"
          :sendMessageImg="sendMessageImg"
          :showMessageCard="showMessageCard"
          @contact="emitContact"
          @opensetting="emitOpenSetting"
          @launchapp="emitLaunchApp"
        ></button>
        <!-- #endif -->
      </view>
    </view>
    <!-- #endif -->

    <!-- #ifndef APP-NVUE -->
    <view
      ref="fabRef"
      class="z-fab__wrap"
      :class="[position === 'left' ? 'z-fab__wrap--left' : 'z-fab__wrap--right']"
      :style="wrapStyle"
      @touchstart="onTouchStart"
      @touchmove.stop.prevent="onTouchMove"
      @touchend="onTouchEnd"
      @touchcancel="onTouchEnd"
    >
      <view
        ref="listRef"
        class="z-fab__list"
        :class="[
          isHidden ? 'z-fab__list--hidden' : '',
          isOpen ? 'z-fab__list--open' : '',
          position === 'left' ? 'z-fab__list--left' : 'z-fab__list--right'
        ]"
      >
        <view
          v-for="(it, idx) in items"
          :key="idx"
          class="z-fab__item"
          :class="[position === 'left' ? 'z-fab__item--left' : 'z-fab__item--right']"
          @tap.stop="onItemTap(idx)"
        >
          <text
            v-if="it.text"
            class="z-fab__text"
            :style="{ fontSize: (it.textSize || 28) + 'rpx', color: it.textColor || '#fff', textAlign: position === 'left' ? 'left' : 'right' }"
          >{{ it.text }}</text>

          <view
            class="z-fab__btn"
            :class="{ 'z-fab__btn--default': !getMainBg && !it.background }"
            :style="{ width: size + 'rpx', height: size + 'rpx', background: it.background || getMainBg }"
          >
            <z-icon v-if="it.icon" :name="it.icon" :size="it.iconSize || 64" :color="it.iconColor || '#fff'"></z-icon>
            <image
              v-else-if="it.image"
              :src="it.image"
              mode="widthFix"
              :style="{ width: (it.imageWidth || 56) + 'rpx', height: (it.imageHeight || 56) + 'rpx', borderRadius: (it.imageRadius || 0) + 'rpx' }"
            />
            <text
              v-else-if="it.abbr"
              class="z-fab__abbr"
              :style="{ fontSize: (it.abbrSize || 32) + 'rpx', lineHeight: (it.abbrSize || 32) + 'rpx', color: it.abbrColor || '#fff' }"
            >{{ it.abbr }}</text>

            <!-- #ifndef H5 -->
            <button
              v-if="it.openType"
              class="z-fab__opentype"
              :open-type="it.openType"
              :app-parameter="it.appParameter"
              :lang="it.lang"
              :sessionFrom="it.sessionFrom"
              :sendMessageTitle="it.sendMessageTitle"
              :sendMessagePath="it.sendMessagePath"
              :sendMessageImg="it.sendMessageImg"
              :showMessageCard="it.showMessageCard"
              @contact="emitContact"
              @opensetting="emitOpenSetting"
              @launchapp="emitLaunchApp"
            ></button>
            <!-- #endif -->
          </view>
        </view>
      </view>

      <view
        class="z-fab__main"
        :class="{ 'z-fab__btn--default': !getMainBg, 'z-fab__main--disabled': disabled }"
        :style="{ width: size + 'rpx', height: size + 'rpx', background: getMainBg }"
        @tap.stop="onMainTap"
      >
        <view class="z-fab__main-inner" :class="{ 'z-fab__main-inner--open': isOpen }" ref="mainInnerRef">
          <slot>
            <z-icon name="plus" :size="80" :color="color"></z-icon>
          </slot>
        </view>

        <!-- #ifndef H5 -->
        <button
          v-if="openType"
          class="z-fab__opentype"
          :open-type="openType"
          :app-parameter="appParameter"
          :lang="lang"
          :sessionFrom="sessionFrom"
          :sendMessageTitle="sendMessageTitle"
          :sendMessagePath="sendMessagePath"
          :sendMessageImg="sendMessageImg"
          :showMessageCard="showMessageCard"
          @contact="emitContact"
          @opensetting="emitOpenSetting"
          @launchapp="emitLaunchApp"
        ></button>
        <!-- #endif -->
      </view>
    </view>
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, getCurrentInstance } from 'vue'

type FabItem = {
  text?: string
  textSize?: number
  textColor?: string
  icon?: string
  iconSize?: number
  iconColor?: string
  image?: string
  imageWidth?: number
  imageHeight?: number
  imageRadius?: number
  abbr?: string
  abbrSize?: number
  abbrColor?: string
  background?: string
  // wechat mini program open-type passthrough
  openType?: string
  appParameter?: string
  lang?: string
  sessionFrom?: string
  sendMessageTitle?: string
  sendMessagePath?: string
  sendMessageImg?: string
  showMessageCard?: boolean
  // custom payload
  value?: any
}

const props = defineProps({
  items: { type: Array as any, default: () => [] as FabItem[] },
  position: { type: String as any, default: 'right' }, // left | right
  offsetX: { type: [Number, String] as any, default: 80 }, // rpx
  offsetY: { type: [Number, String] as any, default: 120 }, // rpx
  size: { type: [Number, String] as any, default: 108 }, // rpx
  background: { type: String, default: '' },
  color: { type: String, default: '#fff' },
  mask: { type: Boolean, default: true },
  maskBackground: { type: String, default: 'rgba(0,0,0,.6)' },
  maskClosable: { type: Boolean, default: false },
  zIndex: { type: [Number, String] as any, default: 99 },
  draggable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },

  // v-model:open
  open: { type: Boolean, default: false },

  // open-type passthrough for main button
  openType: { type: String, default: '' },
  appParameter: { type: String, default: '' },
  lang: { type: String, default: 'en' },
  sessionFrom: { type: String, default: '' },
  sendMessageTitle: { type: String, default: '' },
  sendMessagePath: { type: String, default: '' },
  sendMessageImg: { type: String, default: '' },
  showMessageCard: { type: Boolean, default: false }
})

const emit = defineEmits<{
  (e: 'update:open', v: boolean): void
  (e: 'change', v: { open: boolean }): void
  (e: 'click', v: { index: number; item?: FabItem; isMain: boolean }): void
  (e: 'opensetting', detail: any): void
  (e: 'launchapp', detail: any): void
  (e: 'contact', detail: any): void
}>()

const fabRef = ref<any>(null)
const listRef = ref<any>(null)
const mainInnerRef = ref<any>(null)

const isOpen = ref(false)
const isHidden = ref(true)
let hideTimer: any = null

watch(
  () => props.open,
  (v) => {
    if (v === isOpen.value) return
    setOpen(v, true)
  },
  { immediate: true }
)

function noop() {}

const maskStyle = computed(() => `background:${props.maskBackground};z-index:${Number(props.zIndex) - 10};`)

// theme fallback
const getMainBg = computed(() => {
  let bg = props.background
  // #ifdef APP-NVUE
  if (!bg) {
    bg = '#465CFF'
  }
  // #endif
  return bg || '#465CFF'
})

/** drag state (non-nvue uses translate3d; nvue uses animation.transition) */
const dx = ref(0)
const dy = ref(0)
const startX = ref(0)
const startY = ref(0)
const lastX = ref(0)
const lastY = ref(0)
const maxX = ref(0)
const maxY = ref(0)
const edgeLeft = ref(0)
const edgeTop = ref(0)

const isDraggingMoved = ref(false)
let moveEndTimer: any = null

const wrapStyle = computed(() => {
  const base = [`bottom:${props.offsetY}rpx`, `z-index:${props.zIndex}`]
  if (props.position === 'left') base.push(`left:${props.offsetX}rpx`)
  else base.push(`right:${props.offsetX}rpx`)

  // #ifndef APP-NVUE
  if (props.draggable) {
    base.push(`transform:translate3d(${dx.value}px,${dy.value}px,0)`)
  }
  // #endif
  return base.join(';') + ';'
})

function clearHideTimer() {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
}
function scheduleHideIfNeeded() {
  // #ifndef APP-NVUE
  clearHideTimer()
  if (!isOpen.value) {
    hideTimer = setTimeout(() => {
      isHidden.value = true
    }, 250)
  }
  // #endif
}
function setOpen(v: boolean, fromWatch = false) {
  isHidden.value = false
  clearHideTimer()

  isOpen.value = v
  emit('update:open', v)
  emit('change', { open: v })

  // #ifdef APP-NVUE
  nextTick(() => runNvueAnimation(v))
  // #endif

  if (!v) scheduleHideIfNeeded()
  if (!fromWatch) {
    // keep prop sync for uncontrolled usage
  }
}

function toggle() {
  if (!props.items || props.items.length === 0) return
  setOpen(!isOpen.value)
}

function onMainTap() {
  if (props.disabled) return

  // Ignore click after drag (for all platforms)
  if (isDraggingMoved.value) {
    isDraggingMoved.value = false
    return
  }

  if (props.items && props.items.length > 0) {
    toggle()
    emit('click', { index: -1, isMain: true })
  } else {
    emit('click', { index: -1, isMain: true })
  }
}

function onItemTap(idx: number) {
  // Ignore click after drag (for all platforms)
  if (isDraggingMoved.value) {
    isDraggingMoved.value = false
    return
  }
  const item = (props.items || [])[idx]
  emit('click', { index: idx, item, isMain: false })
  setOpen(false)
}

function onMaskTap() {
  if (!props.maskClosable) return
  setOpen(false)
}

function emitOpenSetting(e: any) {
  emit('opensetting', (e && e.detail) || {})
}
function emitLaunchApp(e: any) {
  emit('launchapp', (e && e.detail) || {})
}
function emitContact(e: any) {
  emit('contact', (e && e.detail) || {})
}

/** measure bounds for dragging */
async function measureBounds() {
  if (!props.draggable) return
  const sys = uni.getSystemInfoSync()

  // #ifndef APP-NVUE
  await new Promise<void>((resolve) => {
    const query = uni.createSelectorQuery()
    // #ifndef MP-ALIPAY
    const instance = getCurrentInstanceProxy()
    if (instance) {
      query.in(instance)
    }
    // #endif
    query
      .select('.z-fab__wrap')
      .boundingClientRect()
      .exec((ret) => {
        const r = ret && ret[0]
        if (r) {
          maxX.value = sys.windowWidth - r.width - (r.left || 0)
          maxY.value = sys.windowHeight - r.height - (r.top || 0)
          edgeLeft.value = r.left || 0
          edgeTop.value = r.top || 0
        } else {
          // Fallback: set reasonable defaults if query fails
          maxX.value = sys.windowWidth - 100
          maxY.value = sys.windowHeight - 100
          edgeLeft.value = 0
          edgeTop.value = 0
        }
        resolve()
      })
  })
  // #endif

  // #ifdef APP-NVUE
  const dom = (uni as any).requireNativePlugin('dom')
  await new Promise<void>((resolve) => {
    dom.getComponentRect(fabRef.value, (ret: any) => {
      const size = ret && ret.size
      if (size) {
        maxX.value = sys.windowWidth - size.width - (size.left || 0)
        maxY.value = sys.windowHeight - size.height - (size.top || 0)
        edgeLeft.value = size.left || 0
        edgeTop.value = size.top || 0
      } else {
        // Fallback: set reasonable defaults if query fails
        maxX.value = sys.windowWidth - 100
        maxY.value = sys.windowHeight - 100
        edgeLeft.value = 0
        edgeTop.value = 0
      }
      resolve()
    })
  })
  // #endif
}

function clamp(v: number, min: number, max: number) {
  return v < min ? min : v > max ? max : v
}

function getTouches(e: any) {
  return e.touches || e.changedTouches || []
}

function onTouchStart(e: any) {
  if (!props.draggable) return
  const t = getTouches(e)[0]
  if (!t) return
  startX.value = t.clientX ?? t.screenX
  startY.value = t.clientY ?? t.screenY
  isDraggingMoved.value = false
}

function onTouchMove(e: any) {
  if (!props.draggable) return
  const t = getTouches(e)[0]
  if (!t) return
  const x = t.clientX ?? t.screenX
  const y = t.clientY ?? t.screenY

  const left = clamp(x - startX.value + lastX.value, -edgeLeft.value, maxX.value)
  const top = clamp(y - startY.value + lastY.value, -edgeTop.value, maxY.value)

  // Mark as moved if there's significant movement
  if (Math.abs(x - startX.value) > 5 || Math.abs(y - startY.value) > 5) {
    isDraggingMoved.value = true
  }

  startX.value = x
  startY.value = y

  lastX.value = left
  lastY.value = top

  // #ifndef APP-NVUE
  dx.value = left
  dy.value = top
  // #endif

  // #ifdef APP-NVUE
  runNvueMove(left, top)
  // #endif
}

function onTouchEnd() {
  if (!props.draggable) return
  if (moveEndTimer) clearTimeout(moveEndTimer)
  moveEndTimer = setTimeout(() => {
    isDraggingMoved.value = false
  }, 50)
}

function getCurrentInstanceProxy() {
  const inst = getCurrentInstance()
  return inst && (inst as any).proxy
}

function refresh() {
  dx.value = lastX.value
  dy.value = lastY.value
  nextTick(() => {
    setTimeout(() => {
      measureBounds()
    }, 80)
  })
}
defineExpose({ refresh })

onMounted(() => {
  nextTick(() => {
    setTimeout(() => {
      measureBounds()
    }, 60)
  })
})

onBeforeUnmount(() => {
  clearHideTimer()
  if (moveEndTimer) clearTimeout(moveEndTimer)
})

/** NVUE animation (open/close + move) */
function runNvueMove(x: number, y: number) {
  // #ifdef APP-NVUE
  const animation = (uni as any).requireNativePlugin('animation')
  if (!fabRef.value || !props.draggable) return
  animation.transition(
    fabRef.value,
    {
      styles: { transform: `translate(${x}px,${y}px)` },
      duration: 0,
      timingFunction: 'linear',
      needLayout: false,
      delay: 0
    },
    () => {
      if (Math.abs(x) > 0.1 || Math.abs(y) > 0.1) isDraggingMoved.value = true
    }
  )
  // #endif
}

function runNvueAnimation(open: boolean) {
  // #ifdef APP-NVUE
  const animation = (uni as any).requireNativePlugin('animation')
  if (!listRef.value || !mainInnerRef.value) return

  if (props.mask) {
    // mask is a normal view, CSS already handles
  }

  animation.transition(
    mainInnerRef.value,
    {
      styles: { transform: `rotate(${open ? '135deg' : '0deg'})` },
      duration: 250,
      timingFunction: 'ease-in-out',
      needLayout: false,
      delay: 0
    },
    () => {
      if (!open) isHidden.value = true
    }
  )

  animation.transition(
    listRef.value,
    {
      styles: { transform: `scale(${open ? 1 : 0})`, opacity: open ? 1 : 0 },
      duration: 250,
      timingFunction: 'ease-in-out',
      needLayout: false,
      delay: 0
    },
    () => {}
  )
  // #endif
}
</script>

<style scoped>
.z-fab__mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  opacity: 0;
  /* #ifndef APP-NVUE */
  visibility: hidden;
  transition-property: visibility, opacity;
  /* #endif */
  transition-duration: 0.25s;
  /* #ifdef APP-NVUE */
  transition-property: opacity;
  transition-timing-function: ease-in-out;
  transform: translateX(-100%);
  /* #endif */
}
.z-fab__mask--show {
  opacity: 1;
  /* #ifdef APP-NVUE */
  transform: translateX(0);
  /* #endif */
  /* #ifndef APP-NVUE */
  visibility: visible;
  /* #endif */
}

.z-fab__wrap {
  position: fixed;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: column;
  justify-content: center;
}
.z-fab__wrap--left {
  align-items: flex-start;
}
.z-fab__wrap--right {
  align-items: flex-end;
}

.z-fab__list {
  /* #ifndef APP-NVUE */
  display: flex;
  visibility: hidden;
  transition: all 0.25s ease-in-out;
  transform: scale3d(0, 0, 1);
  opacity: 0;
  /* #endif */
  flex-direction: column;
}
.z-fab__list--left {
  transform-origin: 0 100%;
  align-items: flex-start;
}
.z-fab__list--right {
  transform-origin: 100% 100%;
  align-items: flex-end;
}
.z-fab__list--hidden {
  width: 0;
  height: 0;
}
.z-fab__list--open {
  /* #ifndef APP-NVUE */
  opacity: 1;
  transform: scale3d(1, 1, 1);
  visibility: visible;
  /* #endif */
}

.z-fab__item {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
  margin-bottom: 26rpx;
  position: relative;
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}
.z-fab__item--left {
  flex-direction: row-reverse;
  justify-content: flex-start;
}
.z-fab__item--right {
  flex-direction: row;
  justify-content: flex-end;
}

.z-fab__text {
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
  padding-left: 22rpx;
  padding-right: 22rpx;
  font-weight: normal;
}

.z-fab__btn,
.z-fab__main {
  /* #ifndef APP-NVUE */
  display: flex;
  border-radius: 50%;
  /* #endif */
  /* #ifdef APP-NVUE */
  border-radius: 100px;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  position: relative;
}

.z-fab__btn--default {
  background: #465CFF;
}

.z-fab__abbr {
  text-align: center;
  font-weight: normal;
}

.z-fab__main {
  /* #ifndef APP-NVUE */
  box-shadow: 0 10rpx 14rpx 0 rgba(0, 0, 0, 0.12);
  /* #endif */
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}

.z-fab__main--disabled {
  opacity: 0.6;
}

.z-fab__main-inner {
  /* #ifndef APP-NVUE */
  display: flex;
  transform: rotate(0deg);
  transition: transform 0.25s;
  /* #endif */
  align-items: center;
  justify-content: center;
}
.z-fab__main-inner--open {
  /* #ifndef APP-NVUE */
  transform: rotate(135deg);
  /* #endif */
}

.z-fab__opentype {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  border: 0;
  padding: 0;
  margin: 0;
  background: transparent;
}
</style>
