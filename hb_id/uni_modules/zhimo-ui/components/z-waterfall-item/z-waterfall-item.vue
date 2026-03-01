<template>
  <view class="z-wfi" :class="['z-wfi--' + id, wrapClass]" :style="[baseStyle, styleFromParent]" @tap.stop>
    <view class="z-wfi__inner" :style="innerStyle">
      <slot />
    </view>
  </view>
</template>

<script setup>
import { computed, getCurrentInstance, inject, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  /** 自定义 class */
  wrapClass: { type: [String, Array], default: '' },
  /** 圆角（rpx） */
  radius: { type: [Number, String], default: 24 },
  /** 是否显示阴影（苹果风格柔和阴影） */
  shadow: { type: Boolean, default: true },
  /** 背景色 */
  background: { type: String, default: '#FFFFFF' },
  /** 触发重新测量 */
  measureKey: { type: [String, Number], default: '' }
})

const waterfall = inject('zWaterfall', null)

const id = ref('')
const inst = getCurrentInstance()

function toPxByRpx(v) {
  const n = Number(v || 0)
  return Math.round(uni.upx2px(n))
}

function measure() {
  if (!id.value) return
  const cls = `.z-wfi--${id.value}`
  const tryQuery = (q) => new Promise((resolve) => {
    q.select(cls).boundingClientRect((rect) => resolve(rect)).exec()
  })

  // 先用组件内 query，更快
  const q1 = uni.createSelectorQuery().in(inst?.proxy)
  tryQuery(q1).then((rect) => {
    if (rect && rect.height) {
      waterfall?.updateItemHeight(id.value, Math.ceil(rect.height))
      return
    }
    // fallback：有些端 in(proxy) 会失败，用全局再测一次
    const q2 = uni.createSelectorQuery()
    tryQuery(q2).then((rect2) => {
      if (rect2 && rect2.height) waterfall?.updateItemHeight(id.value, Math.ceil(rect2.height))
    })
  })
}

onMounted(() => {
  if (!waterfall) return
  id.value = waterfall.registerItem()
  nextTick(() => {
    // 首次渲染后再测一次更稳
    setTimeout(() => measure(), 0)
  })
})

watch(() => props.measureKey, () => {
  nextTick(() => setTimeout(() => measure(), 0))
})

onBeforeUnmount(() => {
  // no-op
})

const styleFromParent = computed(() => {
  return waterfall?.getItemStyle(id.value) || {}
})

const baseStyle = computed(() => ({
  position: 'absolute',
  left: 0,
  top: 0,
  willChange: 'transform',
  transitionProperty: 'transform, opacity',
  transitionDuration: '220ms',
  transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)'
}))

const innerStyle = computed(() => {
  const r = `${toPxByRpx(props.radius)}px`
  return {
    borderRadius: r,
    background: props.background,
    overflow: 'hidden',
    boxShadow: props.shadow ? '0 8px 24px rgba(0,0,0,0.05)' : 'none'
  }
})
</script>

<style scoped>
.z-wfi{
  box-sizing: border-box;
}
.z-wfi__inner{
  width: 100%;
}
</style>