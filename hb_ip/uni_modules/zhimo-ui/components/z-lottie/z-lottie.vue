<template>
  <view class="z-lottie" :style="wrapStyle">
    <!-- #ifdef APP-VUE || H5 -->
    <view
      ref="lottieRef"
      :id="containerId"
      class="z-lottie__canvas"
      :prop="animationOptions"
      :change:prop="bindProp"
      :action="currentAction"
      :change:action="bindAction"
      :style="canvasStyle"
    />
    <!-- #endif -->
    
    <!-- #ifdef MP -->
    <canvas
      :id="containerId"
      :class="containerId"
      class="z-lottie__canvas"
      type="2d"
      :style="canvasStyleMp"
    />
    <!-- #endif -->
  </view>
</template>

<!-- #ifdef APP-VUE || H5 -->
<script module="bindProp" lang="renderjs">
import lottieWeb from './lottie-web.min.js'

export default {
  data() {
    return {
      animation: null,
      prevAction: '',
      initialized: false
    }
  },
  methods: {
    bindProp(newVal, oldVal) {
      let isAppVue3 = false
      // #ifdef APP-VUE
      // #ifdef VUE3
      isAppVue3 = true
      // #endif
      // #endif
      if (!this.initialized && !isAppVue3) return
      this.initAnimation(newVal || oldVal)
    },
    bindAction(newVal, oldVal) {
      const action = newVal || oldVal
      if (action === this.prevAction) return
      this.prevAction = action
      try {
        if (this.animation && typeof this.animation[action] === 'function') {
          this.animation[action]()
        }
      } catch (e) {
        console.warn('Lottie action error:', e)
      }
    },
    initAnimation(options) {
      if (!options || (!options.path && !options.animationData)) return
      
      // 销毁旧动画
      if (this.animation) {
        this.animation.destroy()
        this.animation = null
      }
      
      this.$nextTick(() => {
        const containerId = options._containerId || 'z_lottie_container'
        // #ifndef H5
        const container = document.getElementById(containerId)
        // #endif
        // #ifdef H5
        const container = this.$refs.lottieRef?.$el
        // #endif
        
        if (!container) return
        
        this.animation = lottieWeb.loadAnimation({
          container,
          renderer: options.renderer || 'svg',
          loop: options.loop !== false,
          autoplay: options.autoplay !== false,
          path: options.path,
          animationData: options.animationData
        })
      })
    }
  },
  mounted() {
    this.initialized = true
    setTimeout(() => {
      this.initAnimation(this.animationOptions)
    }, 200)
  }
}
</script>
<!-- #endif -->

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

// #ifdef MP
import lottieMiniprogram from './lottie-miniprogram.js'
// #endif

/**
 * z-lottie Lottie动画组件
 * 通过读取JSON文件实现丰富的动画效果
 */

const props = defineProps({
  /** 动画宽度(rpx) */
  width: {
    type: [Number, String],
    default: 600
  },
  /** 动画高度(rpx) */
  height: {
    type: [Number, String],
    default: 400
  },
  /** 动画JSON数据(本地导入) */
  animationData: {
    type: Object,
    default: null
  },
  /** 动画JSON路径(网络地址) */
  path: {
    type: String,
    default: ''
  },
  /** 是否自动播放 */
  autoplay: {
    type: Boolean,
    default: true
  },
  /** 是否循环播放 */
  loop: {
    type: Boolean,
    default: true
  },
  /** 渲染器类型 svg/canvas */
  renderer: {
    type: String,
    default: 'svg'
  },
  /** 动画操作 play/pause/stop/destroy */
  action: {
    type: String,
    default: 'play',
    validator: (v) => ['play', 'pause', 'stop', 'destroy'].includes(v)
  }
})

const emit = defineEmits(['complete', 'loopComplete', 'enterFrame', 'error'])

// 生成唯一ID
const containerId = ref(`z_lottie_${Math.random().toString(36).slice(2, 10)}`)

// 当前动作
const currentAction = ref('play')

// #ifdef MP
const mpAnimation = ref(null)
const mpInitialized = ref(false)
const mpWidth = ref(300)
const mpHeight = ref(200)
// #endif

// 计算尺寸
const widthValue = computed(() => Number(props.width) || 600)
const heightValue = computed(() => Number(props.height) || 400)

// 容器样式
const wrapStyle = computed(() => ({
  width: `${widthValue.value}rpx`,
  height: `${heightValue.value}rpx`
}))

const canvasStyle = computed(() => ({
  width: `${widthValue.value}rpx`,
  height: `${heightValue.value}rpx`
}))

// #ifdef MP
const canvasStyleMp = computed(() => ({
  width: `${mpWidth.value}px`,
  height: `${mpHeight.value}px`
}))
// #endif

// 动画配置(用于renderjs通信)
const animationOptions = computed(() => ({
  _containerId: containerId.value,
  path: props.path,
  animationData: props.animationData,
  autoplay: props.autoplay,
  loop: props.loop,
  renderer: props.renderer
}))

// 验证并返回有效的action
function getValidAction(action) {
  const validActions = ['play', 'pause', 'stop', 'destroy']
  return validActions.includes(action) ? action : 'play'
}

// 监听action变化
watch(
  () => props.action,
  (val) => {
    currentAction.value = getValidAction(val)
    // #ifdef MP
    handleMpAction()
    // #endif
  }
)

// 监听动画配置变化
watch(
  [() => props.path, () => props.animationData],
  () => {
    // #ifdef MP
    if (mpInitialized.value) {
      initMpAnimation()
    }
    // #endif
  }
)

// #ifdef MP
// 小程序端动作处理
function handleMpAction() {
  try {
    if (mpAnimation.value && typeof mpAnimation.value[currentAction.value] === 'function') {
      mpAnimation.value[currentAction.value]()
    }
  } catch (e) {
    console.warn('Lottie MP action error:', e)
  }
}

// 小程序端初始化
function initMpAnimation() {
  if (!props.path && !props.animationData) return
  
  // 销毁旧动画
  if (mpAnimation.value) {
    mpAnimation.value.destroy()
    mpAnimation.value = null
  }
  
  nextTick(() => {
    const query = uni.createSelectorQuery()
    // #ifndef MP-ALIPAY
    query.in(getCurrentInstance().proxy)
    // #endif
    
    // #ifndef MP-QQ
    query.selectAll(`.${containerId.value}`).node(res => {
      if (!res || !res[0] || !res[0].node) {
        emit('error', { message: 'Canvas node not found' })
        return
      }
      
      const canvas = res[0].node
      const context = canvas.getContext('2d')
      const dpr = uni.getSystemInfoSync().pixelRatio
      
      canvas.width = mpWidth.value * dpr
      canvas.height = mpHeight.value * dpr
      context.scale(dpr, dpr)
      
      lottieMiniprogram.setup(canvas)
      
      mpAnimation.value = lottieMiniprogram.loadAnimation({
        loop: props.loop,
        autoplay: props.autoplay,
        path: props.path,
        animationData: props.animationData,
        rendererSettings: {
          context
        }
      })
      
      // 绑定事件
      if (mpAnimation.value) {
        mpAnimation.value.addEventListener('complete', () => emit('complete'))
        mpAnimation.value.addEventListener('loopComplete', () => emit('loopComplete'))
        mpAnimation.value.addEventListener('enterFrame', (e) => emit('enterFrame', e))
      }
      
      mpInitialized.value = true
    }).exec()
    // #endif
  })
}
// #endif

onMounted(() => {
  currentAction.value = getValidAction(props.action)
  
  // #ifdef MP
  // 转换rpx到px
  mpWidth.value = uni.upx2px(widthValue.value)
  mpHeight.value = uni.upx2px(heightValue.value)
  
  nextTick(() => {
    setTimeout(() => {
      initMpAnimation()
    }, 50)
  })
  // #endif
})

onBeforeUnmount(() => {
  currentAction.value = 'destroy'
  // #ifdef MP
  if (mpAnimation.value) {
    mpAnimation.value.destroy()
    mpAnimation.value = null
  }
  // #endif
})

// 暴露方法供外部调用
defineExpose({
  play: () => { currentAction.value = 'play' },
  pause: () => { currentAction.value = 'pause' },
  stop: () => { currentAction.value = 'stop' },
  destroy: () => { currentAction.value = 'destroy' }
})
</script>

<script>
// 用于小程序获取组件实例
import { getCurrentInstance } from 'vue'
export default {
  name: 'z-lottie'
}
</script>

<style scoped>
.z-lottie {
  /* #ifndef APP-NVUE */
  display: inline-flex;
  /* #endif */
  overflow: hidden;
}

.z-lottie__canvas {
  /* #ifndef APP-NVUE */
  display: block;
  /* #endif */
}
</style>
