<template>
  <view class="z-field-label" :class="{ 'is-inline': inline, 'is-full': full }" :style="wrapStyle" @tap.stop="onTap">
    <view v-if="icon || $slots.icon" class="z-field-label__icon">
      <slot name="icon">
        <image v-if="icon" :src="icon" mode="aspectFit" class="z-field-label__img" />
      </slot>
    </view>
    <view class="z-field-label__text">
      <slot>{{ text }}</slot>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
  icon: { type: String, default: '' },
  full: { type: Boolean, default: false },
  inline: { type: Boolean, default: false },
  padding: { type: Array, default: () => [12, 16] }, // [v,h] rpx
  margin: { type: Array, default: () => [0, 0] },   // [v,h] rpx
  radius: { type: Number, default: 14 },
  background: { type: String, default: 'transparent' }
})

const emit = defineEmits(['click'])

const wrapStyle = computed(() => ({
  padding: `${props.padding[0]}rpx ${props.padding[1]}rpx`,
  margin: `${props.margin[0]}rpx ${props.margin[1]}rpx`,
  borderRadius: `${props.radius}rpx`,
  background: props.background
}))

function onTap() {
  emit('click')
}
</script>

<style scoped>
.z-field-label{
  display:flex; align-items:center;
}
.z-field-label.is-full{ width:100%; }
.z-field-label.is-inline{ display:inline-flex; }
.z-field-label__icon{ width: 36rpx; height:36rpx; margin-right: 10rpx; display:flex; align-items:center; justify-content:center; }
.z-field-label__img{ width: 36rpx; height:36rpx; }
.z-field-label__text{ font-size: 26rpx; }
</style>
