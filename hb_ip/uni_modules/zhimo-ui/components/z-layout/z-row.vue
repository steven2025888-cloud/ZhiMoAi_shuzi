<template>
  <!-- z-row: 24-grid row (no gutter) -->
  <view class="z-row" :style="rowStyle">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Justify = 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly'
type Align = 'start' | 'center' | 'end' | 'stretch' | 'baseline'

const props = defineProps({
  /**
   * Flex layout switch. Default true because grid is based on flex.
   */
  flex: { type: Boolean, default: true },
  /**
   * Whether to wrap columns. Default true.
   */
  wrap: { type: Boolean, default: true },
  /**
   * Horizontal alignment.
   */
  justify: { type: String as unknown as () => Justify, default: 'start' },
  /**
   * Vertical alignment.
   */
  align: { type: String as unknown as () => Align, default: 'stretch' },
})

const mapJustify = (j: Justify) => {
  switch (j) {
    case 'center': return 'center'
    case 'end': return 'flex-end'
    case 'between': return 'space-between'
    case 'around': return 'space-around'
    case 'evenly': return 'space-evenly'
    default: return 'flex-start'
  }
}
const mapAlign = (a: Align) => {
  switch (a) {
    case 'center': return 'center'
    case 'end': return 'flex-end'
    case 'start': return 'flex-start'
    case 'baseline': return 'baseline'
    default: return 'stretch'
  }
}

const rowStyle = computed(() => {
  if (!props.flex) return ''
  return {
    display: 'flex',
    flexWrap: props.wrap ? 'wrap' : 'nowrap',
    justifyContent: mapJustify(props.justify),
    alignItems: mapAlign(props.align),
  } as any
})
</script>

<style scoped>
.z-row {
  width: 100%;
  box-sizing: border-box;
}
</style>
