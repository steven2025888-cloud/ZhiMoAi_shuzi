<template>
  <view
    class="zli"
    :class="[{ 'zli--block': block, 'zli--loaded': loaded, 'zli--clickable': clickable }]"
    :style="wrapStyle"
    @tap="onTap"
    @appear="onAppear"
  >
    <!-- placeholder / skeleton -->
    <view v-if="!revealed" class="zli-ph">
      <image
        v-if="placeholder"
        class="zli-ph__img"
        :src="placeholder"
        mode="aspectFill"
        :style="phImgStyle"
        :draggable="false"
      />
      <view v-else class="zli-ph__solid" />

      <view v-if="skeleton" class="zli-skel">
        <view class="zli-skel__shine" />
      </view>

      <slot name="placeholder" />
    </view>

    <!-- real image -->
    <image
      v-if="revealed"
      class="zli-img"
      :class="{ 'zli-img--in': loaded && fade }"
      :src="currentSrc"
      :mode="finalMode"
      :webp="webp"
      :draggable="draggable"
      :style="imgStyle"
      @load="onLoad"
      @error="onError"
      :id="elId"
    />

    <!-- overlay -->
    <view class="zli-overlay">
      <slot />
    </view>

    <!-- subtle border highlight (apple-ish) -->
    <view v-if="border" class="zli-border" />
  </view>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** image source */
  src: { type: String, default: '' },
  /** placeholder image (blur-friendly) */
  placeholder: { type: String, default: '' },
  /** fallback image when error */
  errorSrc: { type: String, default: '' },

  /** size (rpx). width=-1 means 100% */
  width: { type: [Number, String], default: -1 },
  /** height (rpx). 0/-1 means auto */
  height: { type: [Number, String], default: 0 },

  /** corner radius (rpx) */
  radius: { type: [Number, String], default: 24 },
  /** background when loading */
  background: { type: String, default: '#F3F4F6' },

  /** image mode */
  mode: { type: String, default: 'aspectFill' },

  /** margins (rpx) */
  margin: { type: [Number, String, Array], default: 0 },

  /** enable webp */
  webp: { type: Boolean, default: false },
  /** enable draggable (mainly H5) */
  draggable: { type: Boolean, default: false },

  /** fade in */
  fade: { type: Boolean, default: true },
  /** fade duration (ms) */
  fadeDuration: { type: [Number, String], default: 260 },

  /** show skeleton shimmer */
  skeleton: { type: Boolean, default: true },

  /** add subtle border */
  border: { type: Boolean, default: true },
  /** add subtle shadow */
  shadow: { type: Boolean, default: true },

  /** render as block (100% width by default) */
  block: { type: Boolean, default: true },

  /** when set, use observer with this viewport bottom (px) */
  preloadBottom: { type: [Number, String], default: 120 },

  /** passthrough tag */
  tag: { type: [String, Number, Object], default: '' }
})

const emit = defineEmits(['load', 'error', 'click', 'visible'])

const inst = getCurrentInstance()
const proxy = inst?.proxy

const elId = `zli_${Math.ceil(Math.random() * 10e5).toString(36)}`
const observer = ref(null)

const revealed = ref(false)
const loaded = ref(false)
const errored = ref(false)

const currentSrc = computed(() => {
  if (!errored.value) return props.src
  return props.errorSrc || props.src
})

const finalMode = computed(() => {
  const h = Number(props.height)
  if (h === 0 || h === -1) return 'widthFix'
  return props.mode
})

const clickable = computed(() => true)

watch(
  () => props.src,
  async () => {
    // reset state when src changes
    loaded.value = false
    errored.value = false
    revealed.value = false
    await nextTick()
    startObserve()
  }
)

const wrapStyle = computed(() => {
  const w = props.width === -1 || props.width === '-1' ? '100%' : `${Number(props.width)}rpx`
  const hNum = Number(props.height)
  const h = (hNum === 0 || hNum === -1) ? 'auto' : `${hNum}rpx`
  const r = `${Number(props.radius)}rpx`

  const m = normalizeMargin(props.margin)

  // Apple-ish: soft border + shadow
  const shadow = props.shadow
    ? '0 10rpx 28rpx rgba(17,24,39,.10), 0 2rpx 6rpx rgba(17,24,39,.06)'
    : 'none'

  return {
    width: w,
    height: h,
    borderRadius: r,
    background: props.background,
    marginTop: m[0] + 'rpx',
    marginRight: m[1] + 'rpx',
    marginBottom: m[2] + 'rpx',
    marginLeft: m[3] + 'rpx',
    boxShadow: shadow
  }
})

const imgStyle = computed(() => {
  const w = props.width === -1 || props.width === '-1' ? '100%' : `${Number(props.width)}rpx`
  const hNum = Number(props.height)
  const h = (hNum === 0 || hNum === -1) ? 'auto' : `${hNum}rpx`
  const r = `${Number(props.radius)}rpx`
  return {
    width: w,
    height: h,
    borderRadius: r,
    transitionDuration: props.fade ? `${Number(props.fadeDuration)}ms` : '0ms'
  }
})

const phImgStyle = computed(() => {
  const r = `${Number(props.radius)}rpx`
  return {
    borderRadius: r,
    filter: 'blur(10px)',
    transform: 'scale(1.05)'
  }
})

function normalizeMargin(v) {
  // number/string => all
  if (typeof v === 'number') return [v, v, v, v]
  if (typeof v === 'string') {
    const n = Number(v)
    if (!Number.isNaN(n)) return [n, n, n, n]
    // support: "10 12" or "10 12 14 16"
    const parts = v.trim().split(/[\s,]+/).map((x) => Number(x)).filter((x) => Number.isFinite(x))
    if (parts.length === 2) return [parts[0], parts[1], parts[0], parts[1]]
    if (parts.length === 3) return [parts[0], parts[1], parts[2], parts[1]]
    if (parts.length >= 4) return [parts[0], parts[1], parts[2], parts[3]]
    return [0, 0, 0, 0]
  }
  if (Array.isArray(v)) {
    const a = v.map((x) => Number(x)).filter((x) => Number.isFinite(x))
    if (a.length === 1) return [a[0], a[0], a[0], a[0]]
    if (a.length === 2) return [a[0], a[1], a[0], a[1]]
    if (a.length === 3) return [a[0], a[1], a[2], a[1]]
    if (a.length >= 4) return [a[0], a[1], a[2], a[3]]
  }
  return [0, 0, 0, 0]
}

function onTap() {
  emit('click', { tag: props.tag, src: props.src })
}

function reveal() {
  if (revealed.value) return
  revealed.value = true
  emit('visible', { tag: props.tag })
}

function onAppear() {
  // APP-NVUE fallback
  if (!revealed.value) reveal()
}

function onLoad(e) {
  loaded.value = true
  emit('load', { detail: e?.detail, tag: props.tag, src: props.src })
}

function onError(e) {
  errored.value = true
  // if no errorSrc, still allow load state to avoid stuck shimmer
  loaded.value = true
  emit('error', { detail: e?.detail, tag: props.tag, src: props.src })
}

function endObserve() {
  try {
    if (observer.value) {
      observer.value.disconnect()
      observer.value = null
    }
  } catch (e) {}
}

function startObserve() {
  if (revealed.value) return
  if (!props.src) return

  endObserve()

  // in some H5 iframe or special runtime, observer may fail => fallback reveal
  try {
    const ob = uni.createIntersectionObserver(proxy)
    const bottom = Number(props.preloadBottom) || 0
    ob.relativeToViewport({ bottom })
      .observe(`#${elId}`, (res) => {
        if (res && res.intersectionRatio > 0) {
          reveal()
          endObserve()
        }
      })
    observer.value = ob
  } catch (e) {
    reveal()
    endObserve()
  }
}

onMounted(async () => {
  // delay a tick to ensure id is ready
  await nextTick()
  setTimeout(() => {
    // if in iframe H5, intersection observer can be flaky; still try, fallback reveal on error
    startObserve()
    // If still not revealed after a while, reveal to avoid stuck placeholder
    setTimeout(() => {
      if (!revealed.value) reveal()
    }, 2600)
  }, 50)
})

onBeforeUnmount(() => {
  endObserve()
})

// expose
defineExpose({ reveal, reset: () => { revealed.value = false; loaded.value = false; errored.value = false; startObserve() } })
</script>

<style scoped>
.zli{
  position: relative;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  align-items: stretch;
  justify-content: center;
}
.zli--block{ width: 100%; }
.zli--clickable{ /* touch feedback */
  /* #ifndef APP-NVUE */
  cursor: pointer;
  /* #endif */
}
.zli:active{
  transform: scale(0.995);
}

.zli-ph{
  position:absolute;
  left:0; top:0; right:0; bottom:0;
  display:flex;
  align-items:center;
  justify-content:center;
}
.zli-ph__solid{
  position:absolute; inset:0;
  background: rgba(255,255,255,.35);
}
.zli-ph__img{
  position:absolute; inset:0;
  width:100%;
  height:100%;
  opacity: .92;
}

.zli-skel{
  position:absolute; inset:0;
  background: rgba(255,255,255,.22);
}
.zli-skel__shine{
  position:absolute;
  left:-40%;
  top:0; bottom:0;
  width:40%;
  transform: skewX(-15deg);
  background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.55), rgba(255,255,255,0));
  animation: zliShine 1.2s ease-in-out infinite;
  opacity: .9;
}
@keyframes zliShine{
  0%{ left:-45%; }
  100%{ left:110%; }
}

.zli-img{
  /* #ifndef APP-NVUE */
  display:block;
  /* #endif */
  opacity: 1;
}
.zli-img--in{
  opacity: 1;
  animation: zliFadeIn .18s ease-out;
}
@keyframes zliFadeIn{
  from{ opacity: 0; transform: scale(1.01); }
  to{ opacity: 1; transform: scale(1); }
}

.zli-overlay{
  position:absolute;
  left:0; top:0; right:0; bottom:0;
  pointer-events: none;
  display:flex;
  align-items:flex-end;
  justify-content:flex-start;
}

.zli-border{
  position:absolute;
  inset:0;
  border-radius: inherit;
  border: 1rpx solid rgba(255,255,255,.55);
  box-shadow: inset 0 0 0 1rpx rgba(17,24,39,.06);
  pointer-events:none;
}
</style>
