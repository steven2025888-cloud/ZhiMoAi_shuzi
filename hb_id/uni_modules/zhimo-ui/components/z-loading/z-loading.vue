<template>
  <view
    v-if="visible"
    class="z-loading"
    :class="{ 'z-loading--mask': showMask }"
    :style="maskStyle"
    @tap.stop="onMaskTap"
  >
    <view
      class="z-loading__container"
      :class="[
        `z-loading--${direction}`,
        fixed ? 'z-loading--fixed' : ''
      ]"
      :style="containerStyle"
    >
      <!-- 自定义图标模式 -->
      <template v-if="icon">
        <image
          ref="spinnerRef"
          class="z-loading__icon"
          :class="{ 'z-loading__spin': !isNvue }"
          :src="icon"
          :style="iconStyle"
          mode="aspectFit"
        />
      </template>

      <!-- 内置加载动画 -->
      <template v-else>
        <!-- spinner 旋转圆环 -->
        <view
          v-if="type === 'spinner'"
          class="z-loading__spinner"
          :style="spinnerStyle"
        />

        <!-- dots 三点跳动 -->
        <view v-else-if="type === 'dots'" class="z-loading__dots">
          <view
            v-for="i in 3"
            :key="i"
            class="z-loading__dot"
            :class="`z-loading__dot--${i}`"
            :style="dotStyle"
          />
        </view>

        <!-- pulse 脉冲 -->
        <view
          v-else-if="type === 'pulse'"
          class="z-loading__pulse"
          :style="pulseStyle"
        />

        <!-- wave 波浪条 -->
        <view v-else-if="type === 'wave'" class="z-loading__wave">
          <view
            v-for="i in 5"
            :key="i"
            class="z-loading__bar"
            :class="`z-loading__bar--${i}`"
            :style="barStyle"
          />
        </view>

        <!-- ring 圆环 -->
        <view
          v-else-if="type === 'ring'"
          class="z-loading__ring"
          :style="ringStyle"
        >
          <view class="z-loading__ring-inner" :style="ringInnerStyle" />
        </view>

        <!-- bounce 弹跳球 -->
        <view v-else-if="type === 'bounce'" class="z-loading__bounce">
          <view
            v-for="i in 3"
            :key="i"
            class="z-loading__ball"
            :class="`z-loading__ball--${i}`"
            :style="ballStyle"
          />
        </view>

        <!-- default: circular 默认圆形 -->
        <view
          v-else
          class="z-loading__circular"
          :style="circularStyle"
        />
      </template>

      <!-- 文本 -->
      <text
        v-if="text"
        class="z-loading__text"
        :style="textStyle"
      >{{ text }}</text>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

/**
 * z-loading 加载组件
 * 支持多种加载动画样式
 */

// #ifdef APP-NVUE
const animation = uni.requireNativePlugin('animation')
// #endif

const props = defineProps({
  /** 是否显示 */
  show: {
    type: Boolean,
    default: true
  },
  /**
   * 加载类型
   * circular: 圆形(默认)
   * spinner: 旋转圆环
   * dots: 三点跳动
   * pulse: 脉冲
   * wave: 波浪条
   * ring: 圆环
   * bounce: 弹跳球
   */
  type: {
    type: String,
    default: 'circular',
    validator: (v) => ['circular', 'spinner', 'dots', 'pulse', 'wave', 'ring', 'bounce'].includes(v)
  },
  /** 排列方向 horizontal/vertical */
  direction: {
    type: String,
    default: 'vertical',
    validator: (v) => ['horizontal', 'vertical'].includes(v)
  },
  /** 提示文字 */
  text: {
    type: String,
    default: ''
  },
  /** 文字颜色 */
  textColor: {
    type: String,
    default: ''
  },
  /** 文字大小 */
  textSize: {
    type: [Number, String],
    default: 26
  },
  /** 加载图标/动画颜色 */
  color: {
    type: String,
    default: ''
  },
  /** 加载图标/动画大小 */
  size: {
    type: [Number, String],
    default: 64
  },
  /** 自定义图标(图片地址) */
  icon: {
    type: String,
    default: ''
  },
  /** 是否固定在屏幕中心 */
  fixed: {
    type: Boolean,
    default: false
  },
  /** 容器背景色(fixed模式下生效) */
  background: {
    type: String,
    default: 'rgba(0, 0, 0, 0.7)'
  },
  /** 是否显示遮罩 */
  mask: {
    type: Boolean,
    default: false
  },
  /** 遮罩背景色 */
  maskColor: {
    type: String,
    default: 'rgba(0, 0, 0, 0.3)'
  },
  /** 点击遮罩是否关闭 */
  maskClosable: {
    type: Boolean,
    default: false
  },
  /** 层级 */
  zIndex: {
    type: Number,
    default: 1008
  },
  /** 垂直偏移 */
  offsetY: {
    type: [Number, String],
    default: 0
  }
})

const emit = defineEmits(['update:show', 'close'])

// 检测是否为nvue环境
let isNvue = false
// #ifdef APP-NVUE
isNvue = true
// #endif

const spinnerRef = ref(null)
const visible = ref(props.show)

// nvue动画相关
// #ifdef APP-NVUE
const deg = ref(0)
const stopAnimation = ref(false)
// #endif

// 计算是否显示遮罩
const showMask = computed(() => (props.mask || isNvue) && props.fixed)

// 遮罩样式
const maskStyle = computed(() => {
  if (!showMask.value) return {}
  return {
    backgroundColor: props.fixed ? props.maskColor : 'transparent',
    zIndex: props.zIndex
  }
})

// 容器样式
const containerStyle = computed(() => {
  const style = {}
  
  if (props.fixed) {
    style.backgroundColor = props.background
  }
  
  if (props.offsetY) {
    const offset = typeof props.offsetY === 'number' ? `${props.offsetY}rpx` : props.offsetY
    style.marginTop = offset
  }
  
  return style
})

// 尺寸转换
const sizeValue = computed(() => {
  const s = Number(props.size)
  return isNaN(s) ? 64 : s
})

// 默认颜色
const defaultColor = computed(() => {
  if (props.color) return props.color
  // fixed模式下默认白色，否则默认灰色
  return props.fixed ? '#ffffff' : '#666666'
})

// 图标样式
const iconStyle = computed(() => ({
  width: `${sizeValue.value}rpx`,
  height: `${sizeValue.value}rpx`
}))

// 文本样式
const textStyle = computed(() => {
  const size = Number(props.textSize) || 26
  return {
    color: props.textColor || defaultColor.value,
    fontSize: `${size}rpx`,
    lineHeight: `${size * 1.5}rpx`
  }
})

// circular 样式
const circularStyle = computed(() => ({
  width: `${sizeValue.value}rpx`,
  height: `${sizeValue.value}rpx`,
  borderWidth: `${Math.max(4, sizeValue.value / 16)}rpx`,
  borderTopColor: defaultColor.value,
  borderRightColor: defaultColor.value
}))

// spinner 样式
const spinnerStyle = computed(() => ({
  width: `${sizeValue.value}rpx`,
  height: `${sizeValue.value}rpx`,
  borderWidth: `${Math.max(4, sizeValue.value / 12)}rpx`,
  borderTopColor: defaultColor.value
}))

// dots 样式
const dotStyle = computed(() => {
  const dotSize = Math.max(12, sizeValue.value / 4)
  return {
    width: `${dotSize}rpx`,
    height: `${dotSize}rpx`,
    backgroundColor: defaultColor.value
  }
})

// pulse 样式
const pulseStyle = computed(() => ({
  width: `${sizeValue.value}rpx`,
  height: `${sizeValue.value}rpx`,
  backgroundColor: defaultColor.value
}))

// wave bar 样式
const barStyle = computed(() => ({
  width: `${Math.max(6, sizeValue.value / 10)}rpx`,
  height: `${sizeValue.value}rpx`,
  backgroundColor: defaultColor.value
}))

// ring 样式
const ringStyle = computed(() => ({
  width: `${sizeValue.value}rpx`,
  height: `${sizeValue.value}rpx`,
  borderColor: defaultColor.value
}))

const ringInnerStyle = computed(() => {
  const innerSize = sizeValue.value * 0.6
  return {
    width: `${innerSize}rpx`,
    height: `${innerSize}rpx`,
    backgroundColor: defaultColor.value
  }
})

// bounce ball 样式
const ballStyle = computed(() => {
  const ballSize = Math.max(16, sizeValue.value / 3)
  return {
    width: `${ballSize}rpx`,
    height: `${ballSize}rpx`,
    backgroundColor: defaultColor.value
  }
})

// 监听show变化
watch(
  () => props.show,
  (val) => {
    visible.value = val
    // #ifdef APP-NVUE
    if (val && props.icon) {
      nextTick(() => {
        setTimeout(() => {
          deg.value += 360
          runNvueAnimation()
        }, 50)
      })
    }
    // #endif
  },
  { immediate: true }
)

// nvue动画
// #ifdef APP-NVUE
function runNvueAnimation() {
  if (!spinnerRef.value || stopAnimation.value) return
  
  animation.transition(
    spinnerRef.value.ref,
    {
      styles: {
        transform: `rotate(${deg.value}deg)`
      },
      duration: 800,
      timingFunction: 'linear',
      iterationCount: 'infinite',
      needLayout: false,
      delay: 0
    },
    () => {
      deg.value += 360
      runNvueAnimation()
    }
  )
}

onMounted(() => {
  if (props.show && props.icon) {
    nextTick(() => {
      setTimeout(() => {
        deg.value += 360
        runNvueAnimation()
      }, 50)
    })
  }
})

onBeforeUnmount(() => {
  deg.value = 0
  stopAnimation.value = true
})
// #endif

// 点击遮罩
function onMaskTap() {
  if (!props.maskClosable) return
  emit('update:show', false)
  emit('close')
}

// 暴露方法
defineExpose({
  show: () => { visible.value = true },
  hide: () => { visible.value = false }
})
</script>

<style scoped>
.z-loading {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  align-items: center;
  justify-content: center;
}

.z-loading--mask {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
}

.z-loading__container {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  align-items: center;
  justify-content: center;
}

.z-loading--vertical {
  flex-direction: column;
}

.z-loading--horizontal {
  flex-direction: row;
}

.z-loading--fixed {
  padding: 40rpx;
  border-radius: 16rpx;
  min-width: 200rpx;
  min-height: 200rpx;
}

/* 文本样式 */
.z-loading__text {
  text-align: center;
}

.z-loading--vertical .z-loading__text {
  margin-top: 24rpx;
}

.z-loading--horizontal .z-loading__text {
  margin-left: 20rpx;
}

/* 自定义图标旋转 */
.z-loading__icon {
  /* #ifndef APP-NVUE */
  display: block;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-loading__spin {
  animation: z-rotate 0.85s linear infinite;
}
/* #endif */

/* circular 圆形加载 */
.z-loading__circular {
  border-radius: 50%;
  border-style: solid;
  border-left-color: transparent;
  border-bottom-color: transparent;
  /* #ifndef APP-NVUE */
  animation: z-rotate 0.85s linear infinite;
  /* #endif */
}

/* spinner 旋转圆环 */
.z-loading__spinner {
  border-radius: 50%;
  border-style: solid;
  border-right-color: transparent;
  border-bottom-color: transparent;
  border-left-color: transparent;
  /* #ifndef APP-NVUE */
  animation: z-rotate 0.8s linear infinite;
  /* #endif */
}

/* dots 三点跳动 */
.z-loading__dots {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.z-loading__dot {
  border-radius: 50%;
  margin: 0 6rpx;
  /* #ifndef APP-NVUE */
  animation: z-dots-bounce 1.4s ease-in-out infinite both;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-loading__dot--1 {
  animation-delay: -0.32s;
}
.z-loading__dot--2 {
  animation-delay: -0.16s;
}
.z-loading__dot--3 {
  animation-delay: 0s;
}
/* #endif */

/* pulse 脉冲 */
.z-loading__pulse {
  border-radius: 50%;
  /* #ifndef APP-NVUE */
  animation: z-pulse 1.5s ease-in-out infinite;
  /* #endif */
}

/* wave 波浪条 */
.z-loading__wave {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.z-loading__bar {
  margin: 0 4rpx;
  border-radius: 4rpx;
  /* #ifndef APP-NVUE */
  animation: z-wave 1.2s ease-in-out infinite;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-loading__bar--1 { animation-delay: -1.2s; }
.z-loading__bar--2 { animation-delay: -1.1s; }
.z-loading__bar--3 { animation-delay: -1.0s; }
.z-loading__bar--4 { animation-delay: -0.9s; }
.z-loading__bar--5 { animation-delay: -0.8s; }
/* #endif */

/* ring 圆环 */
.z-loading__ring {
  border-radius: 50%;
  border-width: 4rpx;
  border-style: solid;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  align-items: center;
  justify-content: center;
  /* #ifndef APP-NVUE */
  animation: z-ring-pulse 1.5s ease-in-out infinite;
  /* #endif */
}

.z-loading__ring-inner {
  border-radius: 50%;
  /* #ifndef APP-NVUE */
  animation: z-ring-inner 1.5s ease-in-out infinite;
  /* #endif */
}

/* bounce 弹跳球 */
.z-loading__bounce {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: flex-end;
  justify-content: center;
  height: 80rpx;
}

.z-loading__ball {
  border-radius: 50%;
  margin: 0 8rpx;
  /* #ifndef APP-NVUE */
  animation: z-bounce 0.6s ease-in-out infinite alternate;
  /* #endif */
}

/* #ifndef APP-NVUE */
.z-loading__ball--1 { animation-delay: 0s; }
.z-loading__ball--2 { animation-delay: 0.2s; }
.z-loading__ball--3 { animation-delay: 0.4s; }
/* #endif */

/* 动画定义 */
/* #ifndef APP-NVUE */
@keyframes z-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes z-dots-bounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes z-pulse {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
}

@keyframes z-wave {
  0%, 40%, 100% {
    transform: scaleY(0.4);
  }
  20% {
    transform: scaleY(1);
  }
}

@keyframes z-ring-pulse {
  0%, 100% {
    transform: scale(0.9);
    opacity: 0.7;
  }
  50% {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes z-ring-inner {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(0.6);
    opacity: 0.6;
  }
}

@keyframes z-bounce {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-40rpx);
  }
}
/* #endif */
</style>
