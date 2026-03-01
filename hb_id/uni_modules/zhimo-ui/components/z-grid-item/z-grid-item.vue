<template>
  <view
    v-if="ready"
    class="z-grid-item"
    :style="outerStyle"
  >
    <view
      class="z-grid-item__box"
      :class="[{ 'is-border': showBorder, 'is-highlight': highlight }]"
      :style="boxStyle"
      @click="onClick"
    >
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'

// #ifdef MP-WEIXIN
defineOptions({
  options: { virtualHost: true }
})
// #endif

type GridCtx = {
  width: { value: string }
  height: { value: string }
  showBorder: { value: boolean }
  borderColor: { value: string }
  handleItemClick: (e: { detail: { index: number } }) => void
}

const props = withDefaults(defineProps<{
  highlight?: boolean
  backgroundColor?: string
  index?: number
}>(), {
  highlight: true,
  backgroundColor: 'transparent',
  index: 0
})

const emit = defineEmits<{
  (e: 'click', evt: { detail: { index: number } }): void
}>()

const grid = inject<GridCtx>('zGrid' as any)

const w = computed(() => grid?.width.value || '')
const h = computed(() => grid?.height.value || '')
const showBorder = computed(() => grid?.showBorder.value ?? true)
const borderColor = computed(() => grid?.borderColor.value ?? '#EEEEEE')

const ready = computed(() => !!w.value)

const outerStyle = computed(() => {
  const ww = w.value
  const hh = h.value
  return `width:${ww};${hh ? `height:${hh};` : ''}`
})

const boxStyle = computed(() => ({
  'border-right-color': borderColor.value,
  'border-bottom-color': borderColor.value,
  'border-top-color': borderColor.value,
  backgroundColor: props.backgroundColor
}))

function onClick() {
  const evt = { detail: { index: props.index } }
  grid?.handleItemClick?.(evt)
  emit('click', evt)
}
</script>

<style scoped>
.z-grid-item {
  /* #ifndef APP-NVUE */
  height: 100%;
  display: flex;
  box-sizing: border-box;
  flex-shrink: 0;
  /* #endif */
  flex-direction: column;
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}

.z-grid-item__box {
  /* #ifndef APP-NVUE */
  display: flex;
  width: 100%;
  /* #endif */
  position: relative;
  flex: 1;
  flex-direction: column;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
}

.is-border {
  position: relative;
  /* #ifdef APP-NVUE */
  border-bottom-style: solid;
  border-bottom-width: 0.5px;
  border-right-style: solid;
  border-right-width: 0.5px;
  /* #endif */
  /* #ifndef APP-NVUE */
  z-index: 0;
  border-bottom: 0;
  border-right: 0;
  /* #endif */
}

/* #ifndef APP-NVUE */
.is-border::before {
  content: " ";
  position: absolute;
  right: 0;
  top: 0;
  width: 1px;
  bottom: 0;
  border-right: 1px solid var(--z-color-border, #EEEEEE);
  transform-origin: 100% 0;
  transform: scaleX(0.5);
}

.is-border::after {
  content: " ";
  position: absolute;
  left: 0;
  bottom: 0;
  right: 0;
  height: 1px;
  border-bottom: 1px solid var(--z-color-border, #EEEEEE);
  transform-origin: 0 100%;
  transform: scaleY(0.5);
}
/* #endif */

.is-highlight:active {
  /* #ifdef APP-NVUE */
  background-color: rgba(0, 0, 0, 0.18) !important;
  /* #endif */
  /* #ifndef APP-NVUE */
  background-color: var(--z-color-hover, rgba(0, 0, 0, 0.18)) !important;
  /* #endif */
}
</style>
