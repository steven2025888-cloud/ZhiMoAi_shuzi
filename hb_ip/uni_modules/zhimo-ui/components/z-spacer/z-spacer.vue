<template>
  <!--
    z-spacer: 用于“上下间距”的纯占位组件
    - 只做高度（垂直间距）
    - 可选背景色（方便演示/调试）
  -->
  <view class="z-spacer" :style="spacerStyle"></view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type SpacerProps = {
  /** 间距大小：只传数字，单位自动补 rpx。默认 16（即 16rpx） */
  size?: number | string
  /** 可选：背景色（演示/调试用） */
  background?: string
}

const props = withDefaults(defineProps<SpacerProps>(), {
  size: 16,
  background: 'transparent'
})

/** 只允许 size 是数字；如果传了字符串，也会尽量转数字 */
function normalizeSizeToRpx(val: number | string): string {
  // 允许传 "16" 这种，统一转成 number
  const n = typeof val === 'number' ? val : Number(val)
  // 非法值兜底为默认 16
  const safe = Number.isFinite(n) ? n : 16
  return `${safe}rpx`
}

const spacerStyle = computed(() => {
  return {
    height: normalizeSizeToRpx(props.size),
    width: '100%',
    backgroundColor: props.background || 'transparent'
  } as Record<string, string>
})
</script>

<style scoped>
.z-spacer {
  /* 防止被压缩（部分布局里可能出现） */
  flex-shrink: 0;
}
</style>
