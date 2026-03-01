<template>
  <!-- #ifndef APP-NVUE -->
  <view class="zbtp-host">
    <view
      v-if="shown"
      class="zbtp"
      :class="[
        shapeClass,
        { 'zbtp--shadow': shadow, 'zbtp--glass': glass, 'zbtp--pressed': pressed }
      ]"
      :style="wrapStyle"
      @touchstart="onPressStart"
      @touchend="onPressEnd"
      @touchcancel="onPressEnd"
      @tap.stop="toTop"
    >
      <slot>
        <view class="zbtp__arrow-wrap">
          <text class="zbtp__arrow" :style="{ color: iconColor, fontSize: arrowSize }">↑</text>
        </view>
      </slot>
    </view>
  </view>
  <!-- #endif -->

  <!-- #ifdef APP-NVUE -->
  <view
    v-if="shown"
    class="zbtp"
    :class="[shapeClass, { 'zbtp--shadow': shadow, 'zbtp--pressed': pressed }]"
    :style="wrapStyleNvue"
    @touchstart="onPressStart"
    @touchend="onPressEnd"
    @touchcancel="onPressEnd"
    @tap.stop="toTop"
  >
    <slot>
      <view class="zbtp__arrow-wrap">
        <text class="zbtp__arrow" :style="{ color: iconColor, fontSize: arrowSize }">↑</text>
      </view>
    </slot>
  </view>
  <!-- #endif -->
</template>

<script setup>
import { computed, ref, watch } from 'vue'

// #ifdef APP-NVUE
const dom = weex.requireModule('dom')
// #endif

const props = defineProps({
  /** current page scrollTop */
  scrollTop: { type: [Number, String], default: 0 },

  /** show when scrollTop > threshold */
  threshold: { type: [Number, String], default: 320 },

  /** size in rpx */
  size: { type: [Number, String], default: 88 },

  /** offsets in rpx */
  offsetRight: { type: [Number, String], default: 36 },
  offsetBottom: { type: [Number, String], default: 170 },

  /** icon size in rpx (for default arrow) */
  iconSize: { type: [Number, String], default: 48 },

  /** colors */
  background: { type: String, default: '#FFFFFF' },
  iconColor: { type: String, default: '#111827' },

  /** style */
  shape: { type: String, default: 'circle' }, // circle | rounded
  radius: { type: [Number, String], default: 26 }, // only for rounded
  shadow: { type: Boolean, default: true },
  glass: { type: Boolean, default: true }, // H5: blur background
  border: { type: Boolean, default: true },

  /** behavior */
  duration: { type: [Number, String], default: 160 },
  disabled: { type: Boolean, default: false },

  /** NVUE: scroll to element */
  targetRef: { type: [String, Object], default: '' },

  /** z-index */
  zIndex: { type: [Number, String], default: 999999 }
})

const emit = defineEmits(['click', 'show', 'hide'])

const shown = ref(false)
const pressed = ref(false)

const thr = computed(() => Number(props.threshold) || 0)
const st = computed(() => Number(props.scrollTop) || 0)

watch(
  st,
  () => {
    const next = st.value > thr.value
    if (next === shown.value) return
    shown.value = next
    emit(next ? 'show' : 'hide', { scrollTop: st.value })
  },
  { immediate: true }
)

const shapeClass = computed(() => (props.shape === 'rounded' ? 'zbtp--rounded' : 'zbtp--circle'))

const arrowSize = computed(() => `${Number(props.iconSize) || 48}rpx`)

const wrapStyle = computed(() => {
  const s = Number(props.size) || 88
  const br = props.shape === 'rounded' ? `${Number(props.radius) || 26}rpx` : '9999rpx'
  const bd = props.border ? '1rpx solid rgba(17,24,39,.10)' : 'none'
  const bg = props.glass ? 'rgba(255,255,255,.72)' : props.background
  return {
    width: `${s}rpx`,
    height: `${s}rpx`,
    right: `${Number(props.offsetRight) || 0}rpx`,
    bottom: `${Number(props.offsetBottom) || 0}rpx`,
    borderRadius: br,
    background: bg,
    border: bd,
    zIndex: String(props.zIndex)
  }
})

const wrapStyleNvue = computed(() => {
  const s = Number(props.size) || 88
  const br = props.shape === 'rounded' ? `${Number(props.radius) || 26}rpx` : `${s}rpx`
  return {
    width: `${s}rpx`,
    height: `${s}rpx`,
    right: `${Number(props.offsetRight) || 0}rpx`,
    bottom: `${Number(props.offsetBottom) || 0}rpx`,
    borderRadius: br,
    background: props.background,
    zIndex: Number(props.zIndex) || 999999
  }
})

function onPressStart() { pressed.value = true }
function onPressEnd() { pressed.value = false }

function toTop() {
  if (props.disabled) return

  // #ifndef APP-NVUE
  pressed.value = true
  setTimeout(() => { pressed.value = false }, 220)
  uni.pageScrollTo({ scrollTop: 0, duration: Number(props.duration) || 160 })
  // #endif

  // #ifdef APP-NVUE
  if (props.targetRef) {
    try { dom.scrollToElement(props.targetRef, {}) } catch (e) {}
  } else {
    uni.pageScrollTo({ scrollTop: 0, duration: Number(props.duration) || 160 })
  }
  // #endif

  emit('click', { scrollTop: st.value })
}
</script>

<style scoped>
/* host fixes stacking context: always on top */
.zbtp-host{
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 999999;
  pointer-events: none;
}

.zbtp{
  position: fixed;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;

  animation: zbtpIn .16s ease-out;
  transform: translateZ(0);

  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}

.zbtp--circle{ border-radius: 9999rpx; }
.zbtp--shadow{
  box-shadow: 0 12rpx 26rpx rgba(17,24,39,.12), 0 2rpx 8rpx rgba(17,24,39,.08);
}

.zbtp--glass{
  /* #ifdef H5 */
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  /* #endif */
}

.zbtp--pressed{
  transform: scale(0.96);
  opacity: .92;
}

.zbtp__arrow-wrap{
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.zbtp__arrow{
  font-weight: 900;
  line-height: 1;
  transform: translateY(-2rpx);
}

@keyframes zbtpIn{
  from{ opacity: 0; transform: scale(.92); }
  to{ opacity: 1; transform: scale(1); }
}
</style>
