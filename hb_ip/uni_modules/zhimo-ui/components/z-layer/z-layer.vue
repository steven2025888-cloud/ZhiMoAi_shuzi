<template>
  <view
    v-if="visible || !isNvue"
    ref="layerRef"
    class="z-layer"
    :class="[
      absolute ? 'z-layer--absolute' : 'z-layer--fixed',
      visible ? 'z-layer--visible' : ''
    ]"
    :style="layerStyle"
    @tap.stop="onMaskTap"
  >
    <view class="z-layer__content" :style="contentStyle">
      <!-- 默认插槽 - 弹窗内容 -->
      <slot />

      <!-- 关闭按钮 -->
      <view
        v-if="closable"
        class="z-layer__close"
        :class="closePositionClass"
        :style="closeStyle"
        @tap.stop="onClose"
      >
        <z-icon
          :name="closeIcon"
          :size="closeSize"
          :color="closeColor"
        />
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

/**
 * z-layer 压屏窗/弹出层组件
 * 用于在浮层中显示广告、公告、引导等内容
 */

// #ifdef APP-NVUE
const animation = uni.requireNativePlugin('animation')
// #endif

const props = defineProps({
  /** 是否显示 */
  show: {
    type: Boolean,
    default: false
  },
  /** 是否显示关闭按钮 */
  closable: {
    type: Boolean,
    default: true
  },
  /** 关闭按钮图标 */
  closeIcon: {
    type: String,
    default: 'mdi:close-circle-outline'
  },
  /** 关闭按钮颜色 */
  closeColor: {
    type: String,
    default: '#ffffff'
  },
  /** 关闭按钮大小 */
  closeSize: {
    type: [Number, String],
    default: 56
  },
  /**
   * 关闭按钮位置
   * left-top: 左上角
   * right-top: 右上角
   * center-bottom: 中下方
   */
  closePosition: {
    type: String,
    default: 'center-bottom',
    validator: (v) => ['left-top', 'right-top', 'center-bottom'].includes(v)
  },
  /** 关闭按钮距离内容的距离 */
  closeOffset: {
    type: [Number, String],
    default: 100
  },
  /** 是否使用绝对定位 */
  absolute: {
    type: Boolean,
    default: false
  },
  /** 内容区域顶部偏移 */
  offsetTop: {
    type: [Number, String],
    default: 0
  },
  /** 点击遮罩是否关闭 */
  maskClosable: {
    type: Boolean,
    default: false
  },
  /** 遮罩背景色 */
  maskColor: {
    type: String,
    default: 'rgba(0, 0, 0, 0.6)'
  },
  /** 层级 */
  zIndex: {
    type: Number,
    default: 996
  },
  /** 动画时长(ms) */
  duration: {
    type: Number,
    default: 250
  },
  /** 自定义参数，关闭时回传 */
  param: {
    type: [Number, String, Object],
    default: null
  }
})

const emit = defineEmits(['update:show', 'close', 'open'])

// 检测是否为nvue环境
let isNvue = false
// #ifdef APP-NVUE
isNvue = true
// #endif

const layerRef = ref(null)
const visible = ref(false)

// 计算属性
const layerStyle = computed(() => ({
  background: props.maskColor,
  zIndex: props.zIndex
}))

const contentStyle = computed(() => ({
  marginTop: props.offsetTop ? `${props.offsetTop}rpx` : '0'
}))

const closePositionClass = computed(() => {
  const map = {
    'left-top': 'z-layer__close--lt',
    'right-top': 'z-layer__close--rt',
    'center-bottom': 'z-layer__close--cb'
  }
  return map[props.closePosition] || 'z-layer__close--cb'
})

const closeStyle = computed(() => {
  const offset = Math.abs(Number(props.closeOffset))
  const pos = props.closePosition

  // #ifdef APP-NVUE
  // nvue下不需要负值偏移
  if (pos === 'center-bottom') {
    return { bottom: '0rpx' }
  }
  return { top: '0rpx' }
  // #endif

  // #ifndef APP-NVUE
  if (pos === 'center-bottom') {
    return { bottom: `-${offset}rpx` }
  }
  return { top: `-${offset}rpx` }
  // #endif
})

// 监听show属性
watch(
  () => props.show,
  (val) => {
    if (val) {
      open()
    } else {
      close()
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.show) {
    open()
  }
})

// nvue动画
// #ifdef APP-NVUE
function runAnimation(show) {
  if (!layerRef.value) return

  animation.transition(
    layerRef.value.ref,
    {
      styles: { opacity: show ? 1 : 0 },
      duration: props.duration,
      timingFunction: 'ease-in-out',
      needLayout: false,
      delay: 0
    },
    () => {
      if (!show) {
        visible.value = false
      }
    }
  )
}
// #endif

function open() {
  visible.value = true
  emit('open')

  // #ifdef APP-NVUE
  nextTick(() => {
    setTimeout(() => {
      runAnimation(true)
    }, 50)
  })
  // #endif
}

function close() {
  // #ifndef APP-NVUE
  visible.value = false
  // #endif

  // #ifdef APP-NVUE
  runAnimation(false)
  // #endif
}

function onMaskTap() {
  if (!props.maskClosable) return
  onClose()
}

function onClose() {
  emit('update:show', false)
  emit('close', { param: props.param })
}

// 暴露方法供外部调用
defineExpose({
  open,
  close: onClose
})
</script>

<style scoped>
.z-layer {
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  /* #ifndef APP-NVUE */
  display: flex;
  transition: all ease-in-out 0.25s;
  transform: scale3d(1, 1, 0);
  visibility: hidden;
  /* #endif */
  opacity: 0;
  align-items: center;
  justify-content: center;
}

.z-layer--fixed {
  position: fixed;
}

.z-layer--absolute {
  position: absolute;
}

/* #ifndef APP-NVUE */
.z-layer--visible {
  opacity: 1;
  transform: scale3d(1, 1, 1);
  visibility: visible;
}
/* #endif */

.z-layer__content {
  position: relative;
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  /* #endif */
  align-items: center;
  justify-content: center;
  flex-direction: column;
  /* #ifdef APP-NVUE */
  padding: 40px 0;
  /* #endif */
}

/* 关闭按钮基础样式 */
.z-layer__close {
  position: absolute;
  left: 0;
  right: 0;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}

/* 左上角 */
.z-layer__close--lt {
  justify-content: flex-start;
}

/* 右上角 */
.z-layer__close--rt {
  justify-content: flex-end;
}

/* 中下方 */
.z-layer__close--cb {
  justify-content: center;
}
</style>
