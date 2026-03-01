<template>
  <view
    class="z-tab"
    :class="{ 'z-tab--fixed': fixed, 'z-tab--sticky': sticky }"
    :style="{ zIndex, background: bgColor, top: topStr }"
  >
    <scroll-view
      class="z-tab__scroll"
      :scroll-x="scrollable"
      :scroll-left="scrollLeft"
      :scroll-with-animation="true"
      :show-scrollbar="false"
      @scroll="onScroll"
    >
      <view class="z-tab__wrapper" ref="wrapperRef">
        <view
          v-for="(item, index) in list"
          :key="index"
          :id="'z-tab-' + index"
          class="z-tab__item"
          :class="{
            'z-tab__item--disabled': item[disabledKey],
            'z-tab__item--active': modelValue === index,
            'z-tab__item--full': !scrollable
          }"
          :style="itemStyle"
          @tap="onTabClick(index, item)"
        >
          <view class="z-tab__content">
            <!-- 徽标 -->
            <view
              v-if="item[badgeKey]"
              class="z-tab__badge"
              :class="{ 'z-tab__badge--dot': isDot }"
              :style="{ backgroundColor: badgeBgColor, color: badgeColor }"
            >
              {{ isDot ? '' : item[badgeKey] }}
            </view>

            <!-- 图标 -->
            <image
              v-if="item.icon"
              class="z-tab__icon"
              :src="(modelValue === index && item.activeIcon) ? item.activeIcon : item.icon"
              mode="aspectFit"
            />

            <!-- 文字 -->
            <text
              class="z-tab__text"
              :style="{
                color: modelValue === index ? activeColor : inactiveColor,
                fontSize: (modelValue === index ? activeSize : fontSize) + 'rpx',
                fontWeight: modelValue === index ? activeFontWeight : fontWeight
              }"
            >
              {{ item[keyName] }}
            </text>
          </view>
        </view>

        <!-- Line 下划线指示器 -->
        <view
          v-if="type === 'line' && showBar && indicatorReady"
          class="z-tab__bar"
          :style="barStyle"
        />

        <!-- Capsule 胶囊指示器 -->
        <view
          v-if="type === 'capsule' && indicatorReady"
          class="z-tab__capsule"
          :style="capsuleStyle"
        />
      </view>
    </scroll-view>
  </view>
  <!-- 占位元素 -->
  <view v-if="fixed && placeholder" :style="{ height: height + 'rpx' }" />
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, getCurrentInstance, nextTick } from 'vue'

interface TabItem {
  [key: string]: any
}

const props = withDefaults(
  defineProps<{
    /** 数据源 */
    list?: TabItem[]
    /** 当前选中索引 (v-model) */
    modelValue?: number
    /** 显示文字的键名 */
    keyName?: string
    /** 徽标的键名 */
    badgeKey?: string
    /** 禁用的键名 */
    disabledKey?: string
    /** 模式: line(下划线), capsule(胶囊), text(纯文本) */
    type?: 'line' | 'capsule' | 'text'

    /** 高度 (rpx) */
    height?: number | string
    /** 是否可滚动 */
    scrollable?: boolean
    /** 是否固定定位 */
    fixed?: boolean
    /** 是否吸顶 */
    sticky?: boolean
    /** 顶部距离 */
    top?: number | string
    /** z-index */
    zIndex?: number | string
    /** 是否显示占位元素 */
    placeholder?: boolean
    /** item 左右内边距 (rpx) */
    itemPadding?: number | string

    /** 背景色 */
    bgColor?: string
    /** 激活颜色 */
    activeColor?: string
    /** 未激活颜色 */
    inactiveColor?: string
    /** 字体大小 (rpx) */
    fontSize?: number | string
    /** 激活字体大小 (rpx) */
    activeSize?: number | string
    /** 字体粗细 */
    fontWeight?: number | string
    /** 激活字体粗细 */
    activeFontWeight?: number | string

    /** 徽标是否为圆点 */
    isDot?: boolean
    /** 徽标文字颜色 */
    badgeColor?: string
    /** 徽标背景色 */
    badgeBgColor?: string

    /** 是否显示下划线 */
    showBar?: boolean
    /** 下划线宽度 (rpx)，0 表示自动 */
    barWidth?: number | string
    /** 下划线高度 (rpx) */
    barHeight?: number | string
    /** 下划线圆角 (rpx) */
    barRadius?: number | string
    /** 下划线底部距离 (rpx) */
    barBottom?: number | string
    /** 下划线颜色 */
    barColor?: string

    /** 胶囊高度 (rpx) */
    capsuleHeight?: number | string
    /** 胶囊圆角 (rpx) */
    capsuleRadius?: number | string
    /** 胶囊激活背景色 */
    capsuleActiveColor?: string
  }>(),
  {
    list: () => [],
    modelValue: 0,
    keyName: 'name',
    badgeKey: 'badge',
    disabledKey: 'disabled',
    type: 'line',

    height: 88,
    scrollable: false,
    fixed: false,
    sticky: false,
    top: 0,
    zIndex: 99,
    placeholder: false,
    itemPadding: 30,

    bgColor: '#ffffff',
    activeColor: '#3b82f6',
    inactiveColor: '#64748b',
    fontSize: 28,
    activeSize: 30,
    fontWeight: 'normal',
    activeFontWeight: '600',

    isDot: false,
    badgeColor: '#ffffff',
    badgeBgColor: '#ef4444',

    showBar: true,
    barWidth: 40,
    barHeight: 6,
    barRadius: 3,
    barBottom: 4,
    barColor: '',

    capsuleHeight: 60,
    capsuleRadius: 100,
    capsuleActiveColor: '',
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
  (e: 'change', payload: { index: number; [key: string]: any }): void
  (e: 'click', payload: { index: number; [key: string]: any }): void
}>()

const instance = getCurrentInstance()

// 状态
const scrollLeft = ref(0)
const currentScrollLeft = ref(0)
const tabPositions = ref<{ left: number; width: number }[]>([])
const indicatorReady = ref(false)
const wrapperLeft = ref(0)

// 计算属性
const topStr = computed(() => {
  if (props.fixed || props.sticky) {
    return typeof props.top === 'number' ? `${props.top}px` : props.top
  }
  return 'auto'
})

const itemStyle = computed(() => ({
  height: `${props.height}rpx`,
  padding: `0 ${props.itemPadding}rpx`,
}))

// 下划线样式 - 使用存储的位置信息，不依赖实时 boundingClientRect
const barStyle = computed(() => {
  const pos = tabPositions.value[props.modelValue]
  if (!pos) return {}

  const bg = props.barColor || props.activeColor
  let width = uni.upx2px(Number(props.barWidth))
  if (width === 0) {
    width = pos.width * 0.6
  }

  const left = pos.left + (pos.width - width) / 2

  return {
    width: `${width}px`,
    height: `${props.barHeight}rpx`,
    borderRadius: `${props.barRadius}rpx`,
    backgroundColor: bg,
    bottom: `${props.barBottom}rpx`,
    left: `${left}px`,
    transition: 'left 0.3s ease, width 0.3s ease',
  }
})

// 胶囊样式
const capsuleStyle = computed(() => {
  const pos = tabPositions.value[props.modelValue]
  if (!pos) return {}

  const bg = props.capsuleActiveColor || props.activeColor

  return {
    width: `${pos.width}px`,
    height: `${props.capsuleHeight}rpx`,
    borderRadius: `${props.capsuleRadius}rpx`,
    backgroundColor: bg,
    left: `${pos.left}px`,
    opacity: 0.15,
    transition: 'left 0.3s ease, width 0.3s ease',
  }
})

// 监听
watch(() => props.modelValue, (val) => {
  nextTick(() => {
    scrollToCenter(val)
  })
})

watch(() => props.list, () => {
  nextTick(() => {
    init()
  })
}, { deep: true })

onMounted(() => {
  init()
})

// 初始化
function init() {
  setTimeout(() => {
    getTabPositions()
  }, 50)
}

// 获取所有 Tab 的位置信息（相对于 wrapper 的固定位置）
function getTabPositions() {
  const query = uni.createSelectorQuery().in(instance)

  // 先获取 wrapper 的位置
  query.select('.z-tab__wrapper').boundingClientRect()
  query.selectAll('.z-tab__item').boundingClientRect()

  query.exec((res) => {
    if (!res || !res[0] || !res[1]) return

    const wrapperRect = res[0]
    const itemRects = res[1] as any[]

    wrapperLeft.value = wrapperRect.left

    // 计算每个 tab 相对于 wrapper 的位置（固定值，不受滚动影响）
    tabPositions.value = itemRects.map((rect) => ({
      left: rect.left - wrapperRect.left,
      width: rect.width,
    }))

    indicatorReady.value = true
    scrollToCenter(props.modelValue)
  })
}

// 滚动到中心位置
function scrollToCenter(index: number) {
  if (!props.scrollable) return
  if (!tabPositions.value[index]) return

  const pos = tabPositions.value[index]

  // 获取 scroll-view 的宽度
  const query = uni.createSelectorQuery().in(instance)
  query.select('.z-tab__scroll').boundingClientRect((rect: any) => {
    if (!rect) return

    const scrollViewWidth = rect.width
    const tabCenter = pos.left + pos.width / 2
    const targetScrollLeft = tabCenter - scrollViewWidth / 2

    // 确保不超出边界
    scrollLeft.value = Math.max(0, targetScrollLeft)
  }).exec()
}

// 滚动事件
function onScroll(e: any) {
  currentScrollLeft.value = e.detail.scrollLeft
}

// 点击事件
function onTabClick(index: number, item: TabItem) {
  if (item[props.disabledKey]) return
  emit('update:modelValue', index)
  emit('change', { index, ...item })
  emit('click', { index, ...item })
}
</script>

<style scoped>
.z-tab {
  width: 100%;
  box-sizing: border-box;
}

.z-tab--fixed {
  position: fixed;
  left: 0;
  right: 0;
}

.z-tab--sticky {
  position: sticky;
  left: 0;
  right: 0;
}

.z-tab__scroll {
  width: 100%;
  white-space: nowrap;
}

.z-tab__wrapper {
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
}

.z-tab__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  position: relative;
  transition: all 0.3s ease;
  z-index: 2;
  flex-shrink: 0;
}

.z-tab__item--full {
  flex: 1;
}

.z-tab__item--disabled {
  opacity: 0.4;
  pointer-events: none;
}

.z-tab__item--active {
  /* 激活状态可添加额外样式 */
}

.z-tab__content {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding-right: 8rpx; /* 给徽标留出空间 */
}

.z-tab__icon {
  width: 40rpx;
  height: 40rpx;
  margin-right: 10rpx;
  flex-shrink: 0;
}

.z-tab__text {
  transition: color 0.3s ease, font-size 0.2s ease;
  white-space: nowrap;
}

/* 徽标 - 修复重叠问题 */
.z-tab__badge {
  position: absolute;
  top: -8rpx;
  right: -16rpx;
  min-width: 32rpx;
  height: 32rpx;
  line-height: 32rpx;
  padding: 0 8rpx;
  border-radius: 32rpx;
  font-size: 20rpx;
  font-weight: 600;
  text-align: center;
  z-index: 10;
  box-sizing: border-box;
  transform: translateX(50%);
}

.z-tab__badge--dot {
  width: 16rpx;
  height: 16rpx;
  min-width: 16rpx;
  padding: 0;
  right: -4rpx;
  top: -4rpx;
  transform: none;
}

/* 下划线指示器 - 使用 left 定位而非 transform */
.z-tab__bar {
  position: absolute;
  bottom: 0;
  left: 0;
  z-index: 1;
}

/* 胶囊指示器 */
.z-tab__capsule {
  position: absolute;
  top: 50%;
  left: 0;
  z-index: 1;
  transform: translateY(-50%);
}
</style>
