<template>
  <!-- z-dragdeck：纯拖拽版（已移除缩放相关逻辑）
       ✅ 仍保留：多实例叠加可同时拖拽（不互相遮挡）
  -->
  <movable-area class="z-dragdeck-area" :style="areaStyleNorm">
    <movable-view
      class="z-dragdeck-view"
      :style="viewStyleMerged"
      :direction="direction"
      :disabled="disabled"
      :x="innerX"
      :y="innerY"
      :out-of-bounds="outOfBounds"
      :inertia="inertia"
      :damping="damping"
      :friction="friction"
      @change="onMoveChange"
      @touchstart="emit('touchstart', $event)"
      @touchend="emit('touchend', $event)"
      @touchcancel="emit('touchcancel', $event)"
    >
      <slot />
    </movable-view>
  </movable-area>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type Dir = 'all' | 'vertical' | 'horizontal' | 'none'

const props = withDefaults(defineProps<{
  /** 拖拽方向 */
  direction?: Dir
  /** 禁用拖拽 */
  disabled?: boolean
  /** 是否允许越界拖拽 */
  outOfBounds?: boolean
  /** 惯性 */
  inertia?: boolean
  /** 阻尼系数 0~100，越大越难动 */
  damping?: number
  /** 摩擦系数 0~100，越大越快停 */
  friction?: number

  /** 位置（推荐 v-model:x / v-model:y） */
  x?: number
  y?: number

  /** movable-area 的样式（建议显式给宽高，否则默认 100%） */
  areaStyle?: string | Record<string, any>
  /** movable-view 的样式（不传则不强制宽高，跟随 slot 内容） */
  viewStyle?: string | Record<string, any>

  /** 可选：给 movable-view 设置层级（同一舞台多个时） */
  zIndex?: number
}>(), {
  direction: 'all',
  disabled: false,
  outOfBounds: false,
  inertia: true,
  damping: 20,
  friction: 2,

  x: 0,
  y: 0,

  zIndex: 1
})

const emit = defineEmits<{
  (e: 'update:x', v: number): void
  (e: 'update:y', v: number): void
  (e: 'change', payload: { x: number; y: number; source?: string }): void
  (e: 'touchstart', ev: any): void
  (e: 'touchend', ev: any): void
  (e: 'touchcancel', ev: any): void
}>()

const innerX = ref<number>(props.x)
const innerY = ref<number>(props.y)

watch(() => props.x, v => { if (typeof v === 'number') innerX.value = v })
watch(() => props.y, v => { if (typeof v === 'number') innerY.value = v })

const areaStyleNorm = computed(() => {
  if (!props.areaStyle) return { width: '100%', height: '100%' }
  return props.areaStyle
})

const viewStyleMerged = computed(() => {
  const base = (props.viewStyle || {}) as any
  return { ...base, zIndex: String(props.zIndex) }
})

function onMoveChange(e: any) {
  const d = e?.detail || {}
  if (typeof d.x === 'number') {
    innerX.value = d.x
    emit('update:x', d.x)
  }
  if (typeof d.y === 'number') {
    innerY.value = d.y
    emit('update:y', d.y)
  }
  emit('change', { x: innerX.value, y: innerY.value, source: d.source })
}
</script>

<style scoped>
/* ✅ 关键：不让整层 movable-area 当透明遮罩吃事件（多个实例叠加也能拖） */
.z-dragdeck-area{
  position: relative;
  pointer-events: none;
}

/* ✅ 只有真正可拖的 movable-view 接收触摸 */
.z-dragdeck-view{
  pointer-events: auto;
  touch-action: none;
}
</style>
