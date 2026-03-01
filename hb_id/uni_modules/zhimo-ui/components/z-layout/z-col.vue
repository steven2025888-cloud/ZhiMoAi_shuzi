<template>
  <!-- z-col: 24-grid column -->
  <view class="z-col" :style="colStyle">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'

type BP = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

const props = defineProps({
  /**
   * Base span (0~24). Used when breakpoint-specific value is not provided.
   */
  span: { type: Number, default: 0 },
  /**
   * Offset (0~24)
   */
  offset: { type: Number, default: 0 },
  /**
   * Push/Pull for re-ordering (0~24). Implemented via relative positioning.
   */
  push: { type: Number, default: 0 },
  pull: { type: Number, default: 0 },

  /**
   * Breakpoint spans (0~24). Example: :xs="8" :sm="6" ...
   */
  xs: { type: Number, default: -1 },
  sm: { type: Number, default: -1 },
  md: { type: Number, default: -1 },
  lg: { type: Number, default: -1 },
  xl: { type: Number, default: -1 },
})

/**
 * Breakpoint rules (can be adjusted to match your original reference if needed)
 */
const bp = ref<BP>('xs')
const widthPx = ref<number>(0)

const pickBP = (w: number): BP => {
  // Typical breakpoints: 0~575 xs, 576~767 sm, 768~991 md, 992~1199 lg, 1200+ xl
  if (w >= 1200) return 'xl'
  if (w >= 992) return 'lg'
  if (w >= 768) return 'md'
  if (w >= 576) return 'sm'
  return 'xs'
}

const updateBP = (w?: number) => {
  const ww = typeof w === 'number' ? w : (uni.getSystemInfoSync?.().windowWidth ?? 375)
  widthPx.value = ww
  bp.value = pickBP(ww)
}

let offResize: (() => void) | null = null
let h5Handler: any = null

onMounted(() => {
  updateBP()

  // App / 小程序：窗口变化
  if (typeof uni.onWindowResize === 'function') {
    const cb = (res: any) => updateBP(res?.size?.windowWidth)
    uni.onWindowResize(cb)
    offResize = () => {
      // uni has offWindowResize on some platforms
      if (typeof (uni as any).offWindowResize === 'function') (uni as any).offWindowResize(cb)
    }
  }

  // H5 兜底（某些环境 onWindowResize 不触发）
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g: any = (typeof window !== 'undefined') ? window : null
  if (g && typeof g.addEventListener === 'function') {
    h5Handler = () => updateBP(g.innerWidth)
    g.addEventListener('resize', h5Handler, { passive: true })
  }
})

onBeforeUnmount(() => {
  try { offResize?.() } catch (_) {}
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g: any = (typeof window !== 'undefined') ? window : null
  if (g && h5Handler) {
    g.removeEventListener('resize', h5Handler)
  }
})

const clamp24 = (n: number) => {
  if (!Number.isFinite(n)) return 0
  return Math.min(24, Math.max(0, Math.round(n)))
}

const getSpanByBP = (b: BP) => {
  const v = (props as any)[b]
  if (typeof v === 'number' && v >= 0) return v
  return props.span
}

const activeSpan = computed(() => clamp24(getSpanByBP(bp.value)))
const activeOffset = computed(() => clamp24(props.offset))
const activePush = computed(() => clamp24(props.push))
const activePull = computed(() => clamp24(props.pull))

const percent = (n: number) => `${(n / 24) * 100}%`

const colStyle = computed(() => {
  const span = activeSpan.value
  const style: Record<string, any> = {
    boxSizing: 'border-box',
    minHeight: '1px',
  }

  // span=0 => auto (like "flex:1" behavior)
  if (span === 0) {
    style.flex = '1 1 0'
    style.maxWidth = '100%'
  } else {
    const w = percent(span)
    style.flex = `0 0 ${w}`
    style.maxWidth = w
    style.width = w
  }

  const offset = activeOffset.value
  if (offset > 0) style.marginLeft = percent(offset)

  const push = activePush.value
  const pull = activePull.value
  if (push > 0 || pull > 0) {
    style.position = 'relative'
    if (push > 0) style.left = percent(push)
    if (pull > 0) style.right = percent(pull)
  }

  return style
})
</script>

<style scoped>
.z-col {
  box-sizing: border-box;
}
</style>
