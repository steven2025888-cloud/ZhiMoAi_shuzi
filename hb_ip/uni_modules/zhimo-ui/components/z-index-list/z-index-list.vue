<template>
  <view class="z-index-list" :style="containerStyle">
    <!-- 已选择提示栏 -->
    <view v-if="selectable && showSelectBar && selectedCount > 0" class="z-index-list__select-bar" :style="selectBarStyle">
      <text class="z-index-list__select-text">已选择 {{ selectedCount }} 项</text>
      <view class="z-index-list__select-clear" @tap="onClearAll">清空</view>
    </view>

    <!-- 内置搜索栏 -->
    <view v-if="showSearch" class="z-index-list__search" :style="searchStyle">
      <view class="z-index-list__search-box">
        <z-icon :name="searchIcon" :size="searchIconSize" :color="searchIconColor" class="z-index-list__search-icon-wrap" />
        <input
          class="z-index-list__search-input"
          :value="searchKeyword"
          :placeholder="searchPlaceholder"
          placeholder-class="z-index-list__search-placeholder"
          @input="onSearchInput"
        />
        <view v-if="searchKeyword" class="z-index-list__search-clear" @tap="onClearSearch">✕</view>
      </view>
    </view>

    <!-- 顶部插槽 -->
    <view v-if="$slots.header" class="z-index-list__header">
      <slot name="header" />
    </view>

    <!-- 主滚动区域 -->
    <scroll-view
      class="z-index-list__scroll"
      :style="scrollStyle"
      scroll-y
      :scroll-into-view="scrollIntoViewId"
      :scroll-with-animation="scrollAnimation"
      @scroll="onScroll"
    >
      <view class="z-index-list__content" :style="contentStyle">
        <!-- 数据列表 -->
        <view
          v-for="(group, gIndex) in displayList"
          :key="group[letterKey]"
          :id="'z-anchor-' + group[letterKey]"
          class="z-index-list__group"
        >
          <!-- 分组标题 -->
          <view class="z-index-list__title" :style="titleStyle">
            <text class="z-index-list__title-text" :style="titleTextStyle">
              {{ group[descrKey] || group[letterKey] }}
            </text>
          </view>

          <!-- 分组内容 -->
          <view
            v-for="(item, iIndex) in group[dataKey]"
            :key="item._uid || iIndex"
            class="z-index-list__item"
            :class="{
              'z-index-list__item--active': activeItem === `${gIndex}-${iIndex}`,
              'z-index-list__item--last': iIndex === group[dataKey].length - 1
            }"
            @tap="onItemTap(item, group, iIndex)"
            @touchstart="onItemTouchStart(gIndex, iIndex)"
            @touchend="onItemTouchEnd"
          >
            <!-- 自定义内容插槽 -->
            <slot name="item" :item="item" :group="group" :itemIndex="iIndex">
              <!-- 默认内容 -->
              <view class="z-index-list__item-content">
                <!-- 头像/图片 -->
                <view v-if="showAvatar && item[srcKey]" class="z-index-list__avatar">
                  <image
                    class="z-index-list__avatar-img"
                    :src="item[srcKey]"
                    :style="avatarStyle"
                    mode="aspectFill"
                  />
                </view>

                <!-- 文字内容 -->
                <view class="z-index-list__text-wrap">
                  <text class="z-index-list__text" :style="textStyle">{{ item[textKey] }}</text>
                  <text v-if="item[subTextKey]" class="z-index-list__subtext" :style="subTextStyle">
                    {{ item[subTextKey] }}
                  </text>
                </view>

                <!-- 选择状态 -->
                <view v-if="selectable" class="z-index-list__check" @tap.stop="onCheckTap(item, group, iIndex)">
                  <view
                    class="z-index-list__checkbox"
                    :class="{ 'z-index-list__checkbox--checked': item[checkedKey] }"
                    :style="item[checkedKey] ? checkedStyle : {}"
                  >
                    <view v-if="item[checkedKey]" class="z-index-list__checkmark" />
                  </view>
                </view>

                <!-- 右侧箭头 -->
                <view v-if="showArrow && !selectable" class="z-index-list__arrow">
                  <text class="z-index-list__arrow-icon">›</text>
                </view>
              </view>
            </slot>
          </view>
        </view>

        <!-- 无数据提示 -->
        <view v-if="displayList.length === 0" class="z-index-list__empty">
          <slot name="empty">
            <text class="z-index-list__empty-text">{{ searchKeyword ? '未找到匹配项' : emptyText }}</text>
          </slot>
        </view>

        <!-- 底部插槽 -->
        <view v-if="$slots.footer" class="z-index-list__footer">
          <slot name="footer" />
        </view>

        <!-- 底部安全区 -->
        <view v-if="safeAreaBottom" class="z-index-list__safe-bottom" />
      </view>
    </scroll-view>

    <!-- 右侧索引栏 -->
    <view
      v-if="showSidebar && sidebarList.length > 0"
      class="z-index-list__sidebar"
      :style="sidebarStyle"
      @touchstart.stop.prevent="onSidebarTouchStart"
      @touchmove.stop.prevent="onSidebarTouchMove"
      @touchend.stop.prevent="onSidebarTouchEnd"
    >
      <view
        v-for="(letter, index) in sidebarList"
        :key="letter"
        class="z-index-list__sidebar-item"
        :class="{ 'z-index-list__sidebar-item--active': currentLetter === letter }"
        :style="currentLetter === letter ? sidebarActiveStyle : {}"
        :data-letter="letter"
        :data-index="index"
        @tap.stop="onSidebarItemTap(letter)"
      >
        <text class="z-index-list__sidebar-text">{{ letter }}</text>
      </view>
    </view>

    <!-- 索引提示气泡 -->
    <view v-if="showIndicator && indicatorVisible" class="z-index-list__indicator" :style="indicatorStyle">
      <text class="z-index-list__indicator-text">{{ currentLetter }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick, getCurrentInstance } from 'vue'

interface Props {
  // 数据相关
  list: any[]
  letterKey?: string
  descrKey?: string
  dataKey?: string
  textKey?: string
  subTextKey?: string
  srcKey?: string
  checkedKey?: string

  // 搜索相关
  showSearch?: boolean
  searchPlaceholder?: string
  searchKey?: string
  searchIcon?: string
  searchIconSize?: number
  searchIconColor?: string

  // 选择相关
  selectable?: boolean
  showSelectBar?: boolean

  // 显示控制
  showAvatar?: boolean
  showArrow?: boolean
  showSidebar?: boolean
  showIndicator?: boolean

  // 样式相关
  height?: string
  bgColor?: string
  titleBgColor?: string
  titleColor?: string
  titleSize?: number
  textColor?: string
  textSize?: number
  subTextColor?: string
  subTextSize?: number
  avatarSize?: number
  avatarRadius?: number
  activeColor?: string
  searchBg?: string
  
  
  sidebarColor?: string
  sidebarActiveColor?: string
  indicatorColor?: string
  indicatorSize?: number

  // 其他
  scrollAnimation?: boolean
  emptyText?: string
  safeAreaBottom?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  list: () => [],
  letterKey: 'letter',
  descrKey: 'descr',
  dataKey: 'data',
  textKey: 'text',
  subTextKey: 'subText',
  srcKey: 'src',
  checkedKey: 'checked',

  showSearch: false,
  searchPlaceholder: '搜索',
  searchKey: 'text',
  searchIcon: 'mdi:magnify',
  searchIconSize: 40,
  searchIconColor: '#86909c',

  selectable: false,
  showSelectBar: true,

  showAvatar: true,
  showArrow: false,
  showSidebar: true,
  showIndicator: true,

  height: '100vh',
  bgColor: '#f5f6fa',
  titleBgColor: '#f0f1f5',
  titleColor: '#86909c',
  titleSize: 26,
  textColor: '#1d2129',
  textSize: 30,
  subTextColor: '#86909c',
  subTextSize: 24,
  avatarSize: 80,
  avatarRadius: 12,
  activeColor: '#3b82f6',
  
  searchBg: '#FFFFFF',
  
  sidebarColor: '#86909c',
  sidebarActiveColor: '#3b82f6',
  indicatorColor: '#3b82f6',
  indicatorSize: 120,

  scrollAnimation: true,
  emptyText: '暂无数据',
  safeAreaBottom: true
})

const emit = defineEmits<{
  (e: 'init'): void
  (e: 'click', data: { item: any; letter: string; itemIndex: number }): void
  (e: 'select', data: { item: any; letter: string; itemIndex: number; checked: boolean }): void
  (e: 'scroll', data: { scrollTop: number; currentLetter: string }): void
  (e: 'letterChange', letter: string): void
  (e: 'search', keyword: string): void
  (e: 'clearAll'): void
}>()

const instance = getCurrentInstance()

// 响应式数据
const scrollIntoViewId = ref('')
const currentLetter = ref('')
const indicatorVisible = ref(false)
const activeItem = ref('')
const sidebarTouching = ref(false)
const searchKeyword = ref('')
const isScrolling = ref(false)
const scrollTopValue = ref(0)

// 计算已选数量
const selectedCount = computed(() => {
  let count = 0
  props.list.forEach((group: any) => {
    if (group[props.dataKey]) {
      group[props.dataKey].forEach((item: any) => {
        if (item[props.checkedKey]) count++
      })
    }
  })
  return count
})

// 过滤后的列表（搜索）
const filteredList = computed(() => {
  if (!searchKeyword.value) {
    return props.list.filter(group =>
      group[props.dataKey] && group[props.dataKey].length > 0
    )
  }

  const keyword = searchKeyword.value.toLowerCase()
  return props.list
    .map((group: any) => ({
      ...group,
      [props.dataKey]: group[props.dataKey]?.filter((item: any) => {
        const searchField = item[props.searchKey] || item[props.textKey] || ''
        return searchField.toLowerCase().includes(keyword)
      }) || []
    }))
    .filter((group: any) => group[props.dataKey].length > 0)
})

// 显示的列表
const displayList = computed(() => filteredList.value)

// 索引列表（基于显示数据）
const sidebarList = computed(() => {
  return displayList.value.map(group => group[props.letterKey])
})

// 样式计算
const containerStyle = computed(() => ({
  height: props.height,
  backgroundColor: props.bgColor
}))

const scrollStyle = computed(() => {
  let height = '100%'
  return { height }
})


const contentStyle = computed(() => ({
  paddingRight: props.showSidebar ? '60rpx' : '0'
}))


const searchStyle = computed(() => ({
  backgroundColor: props.searchBg
}))

const selectBarStyle = computed(() => ({
  backgroundColor: props.activeColor
}))

const titleStyle = computed(() => ({
  backgroundColor: props.titleBgColor
}))

const titleTextStyle = computed(() => ({
  color: props.titleColor,
  fontSize: `${props.titleSize}rpx`
}))

const textStyle = computed(() => ({
  color: props.textColor,
  fontSize: `${props.textSize}rpx`
}))

const subTextStyle = computed(() => ({
  color: props.subTextColor,
  fontSize: `${props.subTextSize}rpx`
}))

const avatarStyle = computed(() => ({
  width: `${props.avatarSize}rpx`,
  height: `${props.avatarSize}rpx`,
  borderRadius: `${props.avatarRadius}rpx`
}))

const sidebarStyle = computed(() => ({
  '--sidebar-color': props.sidebarColor,
  '--sidebar-active-color': props.sidebarActiveColor
}))

const sidebarActiveStyle = computed(() => ({
  color: props.sidebarActiveColor,
  fontWeight: '700'
}))

const indicatorStyle = computed(() => ({
  width: `${props.indicatorSize}rpx`,
  height: `${props.indicatorSize}rpx`,
  backgroundColor: props.indicatorColor
}))

const checkedStyle = computed(() => ({
  backgroundColor: props.activeColor,
  borderColor: props.activeColor
}))

// 搜索输入
function onSearchInput(e: any) {
  searchKeyword.value = e.detail.value
  emit('search', searchKeyword.value)
}

// 清空搜索
function onClearSearch() {
  searchKeyword.value = ''
  emit('search', '')
}

// 清空所有选择
function onClearAll() {
  emit('clearAll')
}

// 滚动到指定字母
function scrollToLetter(letter: string) {
  if (!letter || isScrolling.value) return

  // 检查字母是否在当前显示列表中
  const targetGroup = displayList.value.find(g => g[props.letterKey] === letter)
  if (!targetGroup) return

  isScrolling.value = true
  currentLetter.value = letter

  // 使用 scroll-into-view，先清空再设置，确保触发滚动
  scrollIntoViewId.value = ''
  nextTick(() => {
    scrollIntoViewId.value = `z-anchor-${letter}`
  })

  emit('letterChange', letter)

  setTimeout(() => {
    isScrolling.value = false
  }, 350)
}

// 滚动事件
function onScroll(e: any) {
  if (sidebarTouching.value || isScrolling.value) return

  scrollTopValue.value = e.detail.scrollTop

  // 获取当前可见的分组
  updateCurrentLetterByScroll()

  emit('scroll', { scrollTop: scrollTopValue.value, currentLetter: currentLetter.value })
}

// 根据滚动位置更新当前字母
function updateCurrentLetterByScroll() {
  const query = uni.createSelectorQuery().in(instance?.proxy)
  query.select('.z-index-list__scroll').boundingClientRect()
  query.selectAll('.z-index-list__group').boundingClientRect()

  query.exec((res) => {
    if (!res || !res[0] || !res[1]) return

    const scrollRect = res[0]
    const groupRects = res[1] as any[]

    // 找到第一个顶部在可视区域内的分组
    for (let i = 0; i < groupRects.length; i++) {
      const rect = groupRects[i]
      // 分组标题在滚动区域顶部附近
      if (rect.top <= scrollRect.top + 60 && rect.bottom > scrollRect.top) {
        const letter = displayList.value[i]?.[props.letterKey]
        if (letter && letter !== currentLetter.value) {
          currentLetter.value = letter
        }
        break
      }
    }
  })
}

// 点击项目
function onItemTap(item: any, group: any, itemIndex: number) {
  const letter = group[props.letterKey]
  emit('click', { item, letter, itemIndex })
}

function onItemTouchStart(groupIndex: number, itemIndex: number) {
  activeItem.value = `${groupIndex}-${itemIndex}`
}

function onItemTouchEnd() {
  setTimeout(() => {
    activeItem.value = ''
  }, 100)
}

// 选择项目
function onCheckTap(item: any, group: any, itemIndex: number) {
  const letter = group[props.letterKey]
  const newChecked = !item[props.checkedKey]
  emit('select', { item, letter, itemIndex, checked: newChecked })
}

// 侧边栏触摸处理
let sidebarItemRects: any[] = []
let sidebarRectsReady = false

function onSidebarTouchStart(e: any) {
  sidebarTouching.value = true
  indicatorVisible.value = true
  sidebarRectsReady = false
  // 获取所有索引项的位置
  getSidebarRects(() => {
    sidebarRectsReady = true
    handleSidebarTouch(e)
  })
}

function onSidebarTouchMove(e: any) {
  if (sidebarRectsReady) {
    handleSidebarTouch(e)
  }
}

function onSidebarTouchEnd() {
  sidebarTouching.value = false
  sidebarRectsReady = false
  setTimeout(() => {
    indicatorVisible.value = false
  }, 300)
}

function onSidebarItemTap(letter: string) {
  // 直接点击索引项
  indicatorVisible.value = true
  scrollToLetter(letter)
  setTimeout(() => {
    indicatorVisible.value = false
  }, 300)
}

function getSidebarRects(callback: () => void) {
  const query = uni.createSelectorQuery().in(instance?.proxy)
  query.selectAll('.z-index-list__sidebar-item').boundingClientRect((rects: any) => {
    if (rects && rects.length) {
      sidebarItemRects = rects
    }
    callback()
  }).exec()
}

function handleSidebarTouch(e: any) {
  if (!sidebarItemRects.length || sidebarItemRects.length !== sidebarList.value.length) {
    return
  }

  const touch = e.touches?.[0] || e.changedTouches?.[0]
  if (!touch) return

  const clientY = touch.clientY

  for (let i = 0; i < sidebarItemRects.length; i++) {
    const rect = sidebarItemRects[i]
    if (clientY >= rect.top && clientY <= rect.bottom) {
      const letter = sidebarList.value[i]
      if (letter && letter !== currentLetter.value) {
        scrollToLetter(letter)
        // 振动反馈
        try {
          uni.vibrateShort({ type: 'light' })
        } catch {}
      }
      break
    }
  }
}

// 初始化
function init() {
  nextTick(() => {
    // 设置初始字母
    if (sidebarList.value.length > 0 && !currentLetter.value) {
      currentLetter.value = sidebarList.value[0]
    }
    emit('init')
  })
}

// 监听数据变化
watch(() => props.list, () => {
  nextTick(init)
}, { deep: true })

watch(searchKeyword, () => {
  nextTick(() => {
    // 搜索后重置当前字母
    if (sidebarList.value.length > 0) {
      currentLetter.value = sidebarList.value[0]
    }
  })
})

// 挂载
onMounted(() => {
  setTimeout(init, 100)
})

// 暴露方法
defineExpose({
  scrollToLetter,
  clearSearch: onClearSearch,
  getSelectedCount: () => selectedCount.value
})
</script>

<style scoped>
.z-index-list {
  position: relative;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 已选择提示栏 */
.z-index-list__select-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 32rpx;
  flex-shrink: 0;
}

.z-index-list__select-text {
  font-size: 28rpx;
  color: #ffffff;
  font-weight: 500;
}

.z-index-list__select-clear {
  padding: 10rpx 24rpx;
  font-size: 26rpx;
  color: #3b82f6;
  background: #ffffff;
  border-radius: 24rpx;
  font-weight: 500;
}

/* 搜索栏 */
.z-index-list__search {
  padding: 16rpx 24rpx;
  flex-shrink: 0;
}

.z-index-list__search-box {
  display: flex;
  align-items: center;
  height: 72rpx;
  padding: 0 20rpx;
  background: #f5f6fa;
  border-radius: 36rpx;
}

.z-index-list__search-icon-wrap {
  margin-right: 12rpx;
  flex-shrink: 0;
}

.z-index-list__search-input {
  flex: 1;
  font-size: 28rpx;
  color: #1d2129;
  background: transparent;
}

.z-index-list__search-placeholder {
  color: #c9cdd4;
}

.z-index-list__search-clear {
  width: 40rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  color: #86909c;
  background: #e5e6eb;
  border-radius: 50%;
}

.z-index-list__header {
  position: relative;
  z-index: 10;
  background: #ffffff;
  flex-shrink: 0;
}

.z-index-list__scroll {
  flex: 1;
  width: 100%;
  min-height: 0;
}

.z-index-list__content {
  min-height: 100%;
}

.z-index-list__group {
  position: relative;
}

.z-index-list__title {
  position: sticky;
  top: 0;
  z-index: 5;
  padding: 16rpx 32rpx;
}

.z-index-list__title-text {
  font-weight: 500;
}

.z-index-list__item {
  background: #ffffff;
  transition: background-color 0.15s ease;
}

.z-index-list__item--active {
  background: #f5f6fa;
}

.z-index-list__item-content {
  display: flex;
  align-items: center;
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid #f0f1f5;
}

.z-index-list__item--last .z-index-list__item-content {
  border-bottom: none;
}

.z-index-list__avatar {
  margin-right: 24rpx;
  flex-shrink: 0;
}

.z-index-list__avatar-img {
  display: block;
}

.z-index-list__text-wrap {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.z-index-list__text {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.z-index-list__subtext {
  display: block;
  margin-top: 8rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.z-index-list__check {
  padding: 16rpx;
  margin-left: 16rpx;
  flex-shrink: 0;
}

.z-index-list__checkbox {
  width: 44rpx;
  height: 44rpx;
  border: 3rpx solid #d9d9d9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.z-index-list__checkbox--checked {
  border-color: #3b82f6;
  background: #3b82f6;
}

.z-index-list__checkmark {
  width: 20rpx;
  height: 10rpx;
  border-left: 3rpx solid #ffffff;
  border-bottom: 3rpx solid #ffffff;
  transform: rotate(-45deg);
  margin-top: -4rpx;
}

.z-index-list__arrow {
  margin-left: 16rpx;
  flex-shrink: 0;
}

.z-index-list__arrow-icon {
  font-size: 36rpx;
  color: #c9cdd4;
}

/* 侧边栏 */
.z-index-list__sidebar {
  position: absolute;
  right: 8rpx;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12rpx 4rpx;
  border-radius: 24rpx;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 4rpx 24rpx rgba(0, 0, 0, 0.08);
}

.z-index-list__sidebar-item {
  width: 44rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.z-index-list__sidebar-item--active {
  transform: scale(1.3);
}

.z-index-list__sidebar-text {
  font-size: 22rpx;
  color: var(--sidebar-color, #86909c);
  font-weight: 500;
}

.z-index-list__sidebar-item--active .z-index-list__sidebar-text {
  color: var(--sidebar-active-color, #3b82f6);
}

/* 索引指示器 */
.z-index-list__indicator {
  position: fixed;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 32rpx rgba(59, 130, 246, 0.4);
  animation: indicator-pop 0.2s ease;
}

@keyframes indicator-pop {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 0;
  }
  100% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
}

.z-index-list__indicator-text {
  font-size: 64rpx;
  color: #ffffff;
  font-weight: 700;
}

/* 空状态 */
.z-index-list__empty {
  padding: 120rpx 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-index-list__empty-text {
  font-size: 28rpx;
  color: #86909c;
}

/* 底部 */
.z-index-list__footer {
  flex-shrink: 0;
}

.z-index-list__safe-bottom {
  height: constant(safe-area-inset-bottom);
  height: env(safe-area-inset-bottom);
}
</style>
