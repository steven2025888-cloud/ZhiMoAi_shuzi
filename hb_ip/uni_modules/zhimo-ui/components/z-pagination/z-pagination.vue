<template>
  <view class="z-pagination" :style="wrapStyle">
    <!-- 上一页按钮 -->
    <view
      class="z-pagination__btn z-pagination__prev"
      :class="{ 'is-disabled': isFirstPage }"
      :style="btnStyle"
      @click="onPrev"
    >
      <slot name="prev">
        <text class="z-pagination__text" :style="textStyle">{{ prevText }}</text>
      </slot>
    </view>

    <!-- 中间内容区 -->
    <view class="z-pagination__content">
      <!-- 数字模式 -->
      <view v-if="mode === 'number'" class="z-pagination__num-list">
        <view
          v-for="(item, index) in pageList"
          :key="index"
          class="z-pagination__num-item"
          :class="{
            'is-active': item === modelValue,
            'is-ellipsis': item === '...'
          }"
          :style="getNumStyle(item)"
          @click="onPageClick(item)"
        >
          <text class="z-pagination__num-text">{{ item }}</text>
        </view>
      </view>

      <!-- 简约模式 -->
      <view v-else class="z-pagination__simple">
        <text class="z-pagination__current" :style="{ color: activeColor }">{{ modelValue }}</text>
        <text class="z-pagination__divider" :style="{ color: color }">/</text>
        <text class="z-pagination__total" :style="{ color: color }">{{ maxPage }}</text>
      </view>
    </view>

    <!-- 下一页按钮 -->
    <view
      class="z-pagination__btn z-pagination__next"
      :class="{ 'is-disabled': isLastPage }"
      :style="btnStyle"
      @click="onNext"
    >
      <slot name="next">
        <text class="z-pagination__text" :style="textStyle">{{ nextText }}</text>
      </slot>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineOptions({
  name: 'z-pagination'
})

// Props 定义
const props = withDefaults(
  defineProps<{
    /** 当前页码 (v-model) */
    modelValue?: number
    /** 数据总量 */
    total?: number
    /** 每页数据量 */
    pageSize?: number
    /** 显示模式: 'simple' | 'number' */
    mode?: 'simple' | 'number'
    /** 上一页文字 */
    prevText?: string
    /** 下一页文字 */
    nextText?: string
    /** 按钮宽度 (rpx) */
    btnWidth?: number | string
    /** 按钮高度 (rpx) */
    height?: number | string
	
	minWidth?: number | string
    /** 圆角 (rpx) */
    radius?: number | string
    /** 文字颜色 */
    color?: string
    /** 激活状态颜色 */
    activeColor?: string
    /** 按钮背景色 */
    bgColor?: string
    /** 数字页码显示数量 */
    pagerCount?: number
  }>(),
  {
    modelValue: 1,
    total: 0,
    pageSize: 10,
    mode: 'number',
    prevText: '上一页',
    nextText: '下一页',
    btnWidth: 80,
    height: 50,
    radius: 12,
	minWidth:50,
    color: '#333333',
    activeColor: '#3b82f6',
    bgColor: '#ffffff',
    pagerCount: 5
  }
)

// 事件定义
const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
  (e: 'change', payload: { type: string; current: number }): void
}>()

// 计算最大页数
const maxPage = computed(() => {
  const total = Number(props.total) || 0
  const pageSize = Number(props.pageSize) || 10
  return total > 0 ? Math.ceil(total / pageSize) : 1
})

// 是否为第一页/最后一页
const isFirstPage = computed(() => props.modelValue <= 1)
const isLastPage = computed(() => props.modelValue >= maxPage.value)

// 容器样式
const wrapStyle = computed(() => ({
  '--z-pg-color': props.color,
  '--z-pg-active': props.activeColor,
  '--z-pg-bg': props.bgColor,
}))

// 按钮样式
const btnStyle = computed(() => ({
  width: `${props.btnWidth}rpx`,
  height: `${props.height}rpx`,
  borderRadius: `${props.radius}rpx`,
  backgroundColor: props.bgColor,
}))

// 文字样式
const textStyle = computed(() => ({
  color: props.color,
}))

// 获取页码样式
function getNumStyle(item: number | string) {
  const base = {
    height: `${props.height}rpx`,
    minWidth: `${props.minWidth}rpx`,
    borderRadius: `${props.radius}rpx`,
  }

  if (item === '...') {
    return {
      ...base,
      color: '#9ca3af',
      backgroundColor: 'transparent',
    }
  }

  if (item === props.modelValue) {
    return {
      ...base,
      color: '#ffffff',
      backgroundColor: props.activeColor,
      boxShadow: `0 4rpx 16rpx ${props.activeColor}40`,
    }
  }

  return {
    ...base,
    color: props.color,
    backgroundColor: 'transparent',
  }
}

// 计算页码列表
const pageList = computed(() => {
  const count = props.pagerCount
  const current = props.modelValue
  const pageCount = maxPage.value

  // 总页数少于显示数量，全部显示
  if (pageCount <= count) {
    return Array.from({ length: pageCount }, (_, i) => i + 1)
  }

  const halfCount = Math.floor((count - 2) / 2)
  const showPrevMore = current > count - halfCount - 1
  const showNextMore = current < pageCount - halfCount

  const list: (number | string)[] = []

  if (!showPrevMore && showNextMore) {
    // 左侧无省略，右侧有省略
    for (let i = 1; i < count; i++) {
      list.push(i)
    }
    list.push('...')
    list.push(pageCount)
  } else if (showPrevMore && !showNextMore) {
    // 左侧有省略，右侧无省略
    list.push(1)
    list.push('...')
    for (let i = pageCount - count + 2; i <= pageCount; i++) {
      list.push(i)
    }
  } else if (showPrevMore && showNextMore) {
    // 双侧都有省略
    list.push(1)
    list.push('...')
    for (let i = current - halfCount; i <= current + halfCount; i++) {
      list.push(i)
    }
    list.push('...')
    list.push(pageCount)
  } else {
    // 兜底：全部显示
    for (let i = 1; i <= pageCount; i++) {
      list.push(i)
    }
  }

  return list
})

// 上一页
function onPrev() {
  if (isFirstPage.value) return
  updatePage(props.modelValue - 1, 'prev')
}

// 下一页
function onNext() {
  if (isLastPage.value) return
  updatePage(props.modelValue + 1, 'next')
}

// 点击页码
function onPageClick(item: number | string) {
  if (item === '...' || item === props.modelValue) return
  updatePage(Number(item), 'page')
}

// 更新页码
function updatePage(newPage: number, type: string) {
  emit('update:modelValue', newPage)
  emit('change', { type, current: newPage })
}
</script>

<style scoped>
.z-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  box-sizing: border-box;
}

/* 按钮 */
.z-pagination__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.z-pagination__btn:active {
  opacity: 0.7;
  transform: scale(0.96);
}

.z-pagination__btn.is-disabled {
  opacity: 0.35;
  pointer-events: none;
}

.z-pagination__text {
  font-size: 26rpx;
  font-weight: 500;
}

/* 内容区 */
.z-pagination__content {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0 16rpx;
  min-width: 0;
}

/* 简约模式 */
.z-pagination__simple {
  display: flex;
  align-items: baseline;
  gap: 4rpx;
}

.z-pagination__current {
  font-size: 40rpx;
  font-weight: 700;
  line-height: 1;
}

.z-pagination__divider {
  font-size: 28rpx;
  font-weight: 500;
  margin: 0 4rpx;
}

.z-pagination__total {
  font-size: 28rpx;
  font-weight: 500;
}

/* 数字列表模式 */
.z-pagination__num-list {
  display: flex;
  align-items: center;
  gap: 6rpx;
  flex-wrap: nowrap;
}

.z-pagination__num-item {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26rpx;
  font-weight: 500;
  transition: all 0.25s ease;
  box-sizing: border-box;
  flex-shrink: 0;
}

.z-pagination__num-item:not(.is-ellipsis):active {
  transform: scale(0.92);
}

.z-pagination__num-item.is-active {
  transform: scale(1.08);
  font-weight: 700;
}

.z-pagination__num-item.is-ellipsis {
  letter-spacing: 2rpx;
  pointer-events: none;
}

.z-pagination__num-text {
  font-size: inherit;
  font-weight: inherit;
  color: inherit;
}
</style>
