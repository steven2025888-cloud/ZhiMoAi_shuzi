<template>
  <view class="z-loadmore" :class="[`z-loadmore--${direction}`]" :style="wrapStyle">
    <!-- 加载中状态 -->
    <view v-if="status === 'loading'" class="z-loadmore__loading">
      <view v-if="!icon" class="z-loadmore__spinner" :style="spinnerStyle"></view>
      <image v-else class="z-loadmore__icon" :src="icon" :style="iconStyle" />
    </view>

    <!-- 文字提示 -->
    <text class="z-loadmore__text" :style="textStyle">{{ statusText }}</text>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Status = 'loading' | 'more' | 'nomore'
type Direction = 'row' | 'column'

interface Props {
  status?: Status
  loadingText?: string
  moreText?: string
  nomoreText?: string
  height?: number
  color?: string
  size?: number
  spinnerColor?: string
  activeColor?: string
  spinnerSize?: number
  icon?: string
  direction?: Direction
}

const props = withDefaults(defineProps<Props>(), {
  status: 'loading',
  loadingText: '加载中...',
  moreText: '上拉加载更多',
  nomoreText: '没有更多了',
  height: 100,
  color: '#86909c',
  size: 26,
  spinnerColor: '#c9cdd4',
  activeColor: '#6366f1',
  spinnerSize: 32,
  icon: '',
  direction: 'row'
})

const statusText = computed(() => {
  const textMap = {
    loading: props.loadingText,
    more: props.moreText,
    nomore: props.nomoreText
  }
  return textMap[props.status] || ''
})

const wrapStyle = computed(() => ({
  height: `${props.height}rpx`
}))

const textStyle = computed(() => ({
  color: props.color,
  fontSize: `${props.size}rpx`,
  lineHeight: `${props.size}rpx`
}))

const spinnerStyle = computed(() => ({
  width: `${props.spinnerSize}rpx`,
  height: `${props.spinnerSize}rpx`,
  borderColor: props.spinnerColor,
  borderLeftColor: props.activeColor
}))

const iconStyle = computed(() => ({
  width: `${props.spinnerSize}rpx`,
  height: `${props.spinnerSize}rpx`
}))
</script>

<style scoped>
.z-loadmore {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
}

.z-loadmore--row {
  flex-direction: row;
  gap: 16rpx;
}

.z-loadmore--column {
  flex-direction: column;
  gap: 12rpx;
}

.z-loadmore__loading {
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-loadmore__spinner {
  border: 3rpx solid;
  border-radius: 50%;
  animation: z-spin 0.8s linear infinite;
}

@keyframes z-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.z-loadmore__icon {
  animation: z-spin 0.8s linear infinite;
}

.z-loadmore__text {
  white-space: nowrap;
}
</style>
