<template>
  <view @touchend.stop="">
    <!-- 遮罩层 -->
    <view 
      class="share-mask" 
      :style="maskStyle" 
      :class="{ 'share-mask-show': visible }"
      @tap.stop="handleMaskClick"
    ></view>
    
    <!-- 分享面板 -->
    <view 
      class="share-panel"
      :class="{
        'share-panel-radius': rounded,
        'share-panel-show': visible
      }"
      :style="panelStyle"
    >
      <!-- 标题插槽 -->
      <slot name="title">
        <text 
          v-if="title" 
          class="share-title"
          :style="titleStyle"
        >{{ title }}</text>
      </slot>
      
      <!-- 分享选项列表 -->
      <view 
        class="share-group" 
        v-for="(group, groupIndex) in groupedItems" 
        :key="groupIndex"
      >
        <scroll-view 
          :show-scrollbar="false" 
          :scroll-x="true" 
          class="share-scroll"
        >
          <view 
            class="share-list" 
            :class="{ 'share-list-full': fullWidth }"
            :style="{ 
              paddingLeft: padding + 'rpx', 
              paddingRight: padding + 'rpx' 
            }"
          >
            <view 
              class="share-item" 
              v-for="(item, index) in group" 
              :key="index"
              @tap.stop="handleItemClick(groupIndex, index, item)"
            >
              <view 
                class="share-icon"
                :style="{
                  background: item.background || itemBg,
                  width: iconSize + 'rpx',
                  height: iconSize + 'rpx'
                }"
              >
                <!-- 图标 -->
                <z-icon
                  v-if="item.icon"
                  :name="item.icon"
                  :size="item.iconSize || 48"
                  :color="item.iconColor || '#333'"
                ></z-icon>

                <!-- 图片 -->
                <image 
                  v-if="item.image"
                  class="share-image"
                  :style="{
                    width: (item.imageSize || 72) + 'rpx',
                    height: (item.imageSize || 72) + 'rpx'
                  }"
                  :src="item.image"
                  mode="aspectFill"
                ></image>
              </view>
              
              <text 
                class="share-text"
                :style="{
                  fontSize: (item.textSize || 24) + 'rpx',
                  color: item.textColor || '#666'
                }"
              >{{ item.text }}</text>
            </view>
          </view>
        </scroll-view>
      </view>
      
      <!-- 取消按钮 -->
      <view 
        class="share-footer" 
        :class="{ 'share-footer-safe': safeArea }"
        :style="{ background: footerBg }"
      >
        <view class="footer-line" :style="{ background: lineColor }"></view>
        <text 
          class="cancel-btn"
          :class="{ 'cancel-btn-safe': safeArea }"
          :style="{
            fontSize: cancelSize + 'rpx',
            color: cancelColor
          }"
          @tap.stop="handleCancel"
        >{{ cancelText }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

// Props定义
const props = defineProps({
  // 是否显示
  visible: {
    type: Boolean,
    default: false
  },
  // 分享项列表（支持单数组或二维数组）
  items: {
    type: Array,
    default: () => []
  },
  // 标题
  title: {
    type: String,
    default: ''
  },
  // 标题大小
  titleSize: {
    type: [Number, String],
    default: 28
  },
  // 标题颜色
  titleColor: {
    type: String,
    default: '#999'
  },
  // 图标大小
  iconSize: {
    type: [Number, String],
    default: 100
  },
  // 选项背景色
  itemBg: {
    type: String,
    default: '#f5f5f5'
  },
  // 面板背景色
  background: {
    type: String,
    default: '#fff'
  },
  // 底部背景色
  footerBg: {
    type: String,
    default: '#fff'
  },
  // 分割线颜色
  lineColor: {
    type: String,
    default: '#eee'
  },
  // 遮罩背景色
  maskBg: {
    type: String,
    default: 'rgba(0,0,0,0.5)'
  },
  // 是否圆角
  rounded: {
    type: Boolean,
    default: true
  },
  // 点击遮罩是否关闭
  maskClose: {
    type: Boolean,
    default: true
  },
  // 层级
  zIndex: {
    type: [Number, String],
    default: 999
  },
  // 是否全宽布局
  fullWidth: {
    type: Boolean,
    default: false
  },
  // 左右内边距
  padding: {
    type: [Number, String],
    default: 32
  },
  // 取消按钮文本
  cancelText: {
    type: String,
    default: '取消'
  },
  // 取消按钮大小
  cancelSize: {
    type: [Number, String],
    default: 32
  },
  // 取消按钮颜色
  cancelColor: {
    type: String,
    default: '#333'
  },
  // 是否适配底部安全区
  safeArea: {
    type: Boolean,
    default: true
  }
})

// Emits定义
const emit = defineEmits(['update:visible', 'click', 'cancel'])

// 计算分组数据
const groupedItems = computed(() => {
  if (!props.items || props.items.length === 0) return []
  
  // 如果是二维数组，直接返回
  if (Array.isArray(props.items[0])) {
    return props.items
  }
  
  // 如果是一维数组，包装成二维数组
  return [props.items]
})

// 遮罩样式
const maskStyle = computed(() => {
  return `background: ${props.maskBg}; z-index: ${Number(props.zIndex) - 1};`
})

// 面板样式
const panelStyle = computed(() => {
  return `z-index: ${props.zIndex}; background: ${props.background};`
})

// 标题样式
const titleStyle = computed(() => {
  return `font-size: ${props.titleSize}rpx; color: ${props.titleColor};`
})

// 处理遮罩点击
const handleMaskClick = () => {
  if (!props.maskClose) return
  handleCancel()
}

// 处理选项点击
const handleItemClick = (groupIndex, index, item) => {
  const result = {
    groupIndex,
    index,
    item
  }
  
  emit('click', result)
}

// 处理取消
const handleCancel = () => {
  emit('update:visible', false)
  emit('cancel')
}
</script>

<style scoped>
/* 遮罩层 */
.share-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  transition: opacity 0.3s ease;
  opacity: 0;
  visibility: hidden;
}

.share-mask-show {
  opacity: 1;
  visibility: visible;
}

/* 分享面板 */
.share-panel {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translateY(100%);
  transition: transform 0.3s ease;
  display: flex;
  flex-direction: column;
  background: #f7f7f7;
}

.share-panel-radius {
  border-top-left-radius: 32rpx;
  border-top-right-radius: 32rpx;
  overflow: hidden;
}

.share-panel-show {
  transform: translateY(0);
}

/* 标题 */
.share-title {
  width: 100%;
  text-align: center;
  padding: 24rpx 0 16rpx;
  font-weight: 400;
  font-size: 26rpx;
  line-height: 1.4;
  color: #999;
}

/* 分组容器 */
.share-group {
  padding: 20rpx 0;
  background: #fff;
  position: relative;
}

.share-group + .share-group {
  margin-top: 16rpx;
}

/* 滚动容器 */
.share-scroll {
  flex-direction: row;
}

/* 选项列表 */
.share-list {
  white-space: nowrap;
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  box-sizing: border-box;
}

.share-list-full {
  min-width: 100%;
  justify-content: space-between;
}

/* 选项 */
.share-item {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 16rpx;
  flex-shrink: 0;
  transition: opacity 0.2s;
}

.share-item:active {
  opacity: 0.6;
}

/* 图标容器 */
.share-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  overflow: hidden;
}

/* 图片 */
.share-image {
  display: block;
}

/* 选项文本 */
.share-text {
  font-size: 22rpx;
  margin-top: 12rpx;
  text-align: center;
  line-height: 1.4;
  color: #666;
}

/* 底部 */
.share-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  margin-top: 16rpx;
  height: 100rpx;
  background: #fff;
}

.share-footer-safe {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

/* 分割线 */
.footer-line {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  transform: scaleY(0.5);
  transform-origin: 0 0;
}

/* 取消按钮 */
.cancel-btn {
  width: 100%;
  text-align: center;
  font-weight: 500;
  line-height: 100rpx;
  transition: background 0.2s;
}

.cancel-btn-safe {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

.cancel-btn:active {
  background: rgba(0, 0, 0, 0.05);
}
</style>
