<template>
  <view class="z-rate" :class="{ 'is-disabled': disabled || readonly }">
    <view
      v-for="i in maxCount"
      :key="i"
      class="z-rate__item"
      :style="itemStyle(i)"
      @tap.stop="handleItemTap($event, i)"
    >
      <!-- Inactive star -->
      <z-icon
        :name="inactiveIcon"
        :size="toNum(size, 34)"
        :color="inactiveColor"
        class="z-rate__star z-rate__star--inactive"
      />

      <!-- Active overlay -->
      <view class="z-rate__overlay" :style="overlayStyle(i)">
        <z-icon
          :name="activeIcon"
          :size="toNum(size, 34)"
          :color="activeColor"
          class="z-rate__star z-rate__star--active"
        />
      </view>
    </view>

    <text v-if="showText" class="z-rate__text" :style="textStyle">
      {{ text }}
    </text>
  </view>
</template>

<script setup>
import { computed } from 'vue'
import ZIcon from '../z-icon/z-icon.vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  max: { type: Number, default: 5 },
  count: { type: Number, default: 0 }, // alias for max
  allowHalf: { type: Boolean, default: false },
  allowClear: { type: Boolean, default: true },
  disabled: { type: Boolean, default: false },
  readonly: { type: Boolean, default: false },

  size: { type: [Number, String], default: 40 }, // rpx
  gap: { type: [Number, String], default: 8 },  // rpx

  activeColor: { type: String, default: '#FFB400' },
  inactiveColor: { type: String, default: '#D4D4D4' },
  activeIcon: { type: String, default: 'mdi:star' },
  inactiveIcon: { type: String, default: 'mdi:star' },

  showText: { type: Boolean, default: false },
  texts: { type: Array, default: () => [] },
  textColor: { type: String, default: '#666' },
  textGap: { type: [Number, String], default: 12 },
})

const emit = defineEmits(['update:modelValue', 'change'])

function toNum(v, fallback) {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}
function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

const maxCount = computed(() => {
  // count prop takes precedence if set
  const c = props.count > 0 ? props.count : props.max
  return Math.max(1, Math.floor(toNum(c, 5)))
})
const current = computed(() => {
  const v = toNum(props.modelValue, 0)
  const c = clamp(v, 0, maxCount.value)
  return props.allowHalf ? Math.round(c * 2) / 2 : Math.round(c)
})

const text = computed(() => {
  if (!props.showText) return ''
  const list = props.texts || []
  const v = current.value
  const idx = Math.max(0, Math.min(list.length - 1, Math.ceil(v) - 1))
  if (list.length > 0) return list[idx] || ''
  return `${v}/${maxCount.value}`
})

const textStyle = computed(() => ({
  marginLeft: `${toNum(props.textGap, 12)}rpx`,
  color: props.textColor,
  fontSize: '26rpx',
}))

function fillFor(i) {
  const v = current.value
  if (v >= i) return 1
  if (props.allowHalf && v + 0.5 >= i) return 0.5
  return 0
}

function itemStyle(i) {
  const g = toNum(props.gap, 8)
  const s = toNum(props.size, 40)
  return {
    marginRight: i === maxCount.value ? '0' : `${g}rpx`,
    width: `${s}rpx`,
    height: `${s}rpx`,
  }
}

function overlayStyle(i) {
  const f = fillFor(i)
  return { width: `${f * 100}%` }
}

function emitValue(next) {
  const v = props.allowHalf ? Math.round(next * 2) / 2 : Math.round(next)
  const clamped = clamp(v, 0, maxCount.value)
  emit('update:modelValue', clamped)
  emit('change', clamped)
}

function handleItemTap(e, index) {
  if (props.disabled || props.readonly) return

  // 获取点击位置
  let isLeftHalf = false
  if (props.allowHalf) {
    // 尝试获取点击的相对位置
    try {
      const touch = e.touches?.[0] || e.changedTouches?.[0] || e.detail || e
      const x = touch.offsetX ?? touch.x ?? 0
      const itemWidth = toNum(props.size, 40)
      // 将 rpx 转换为大致的 px（假设 375 设计稿）
      const halfWidth = itemWidth / 2
      isLeftHalf = x < halfWidth
    } catch {
      isLeftHalf = false
    }
  }

  let next = index
  if (props.allowHalf && isLeftHalf) {
    next = index - 0.5
  }

  // allowClear: tap same value to clear to 0
  if (props.allowClear && next === current.value) {
    emitValue(0)
    return
  }
  emitValue(next)
}
</script>

<style scoped>
.z-rate {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
}

.z-rate.is-disabled {
  opacity: 0.5;
}

.z-rate__item {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.z-rate__star {
  position: absolute;
  left: 0;
  top: 0;
}

.z-rate__star--inactive {
  z-index: 1;
}

.z-rate__star--active {
  z-index: 2;
}

.z-rate__overlay {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  overflow: hidden;
  pointer-events: none;
  z-index: 2;
}

.z-rate__text {
  line-height: 1;
  white-space: nowrap;
}
</style>
