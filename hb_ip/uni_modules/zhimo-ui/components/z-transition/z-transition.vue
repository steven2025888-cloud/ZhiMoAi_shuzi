\
<template>
  <view
    v-if="rendered"
    ref="aniRef"
    class="z-transition"
    :class="fadeClass"
    :style="wrapStyle"
    @tap="handleTap"
  >
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

/**
 * z-transition
 * 用途：给弹层/内容区加过渡动画（H5/小程序走 CSS，APP-NVUE 走原生 animation.transition）
 *
 * effects 支持：
 * ['fade','slide-top','slide-right','slide-bottom','slide-left','zoom-in','zoom-out']
 */

type Effect =
  | 'fade'
  | 'slide-top'
  | 'slide-right'
  | 'slide-bottom'
  | 'slide-left'
  | 'zoom-in'
  | 'zoom-out'

type Props = {
  /** v-model：是否显示（推荐） */
  modelValue?: boolean
  /** 兼容旧写法 */
  show?: boolean

  /** 过渡效果（推荐） */
  effects?: Effect[]
  /** 兼容旧写法 */
  animationType?: Effect[]

  /** 动画时长（ms） */
  duration?: number

  /** 自定义样式（推荐） */
  customStyle?: Record<string, any>
  /** 兼容旧写法 */
  styles?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: undefined,
  show: false,
  effects: undefined,
  animationType: undefined,
  duration: 300,
  customStyle: undefined,
  styles: undefined
})

const emit = defineEmits<{
  (e: 'click', payload: { visible: boolean }): void
  (e: 'change', payload: { visible: boolean }): void
}>()

// #ifdef APP-NVUE
const animation = uni.requireNativePlugin('animation')
// #endif

const aniRef = ref<any>(null)
const rendered = ref(false)
const fadeClass = ref('') // H5/小程序：控制 fade-in / fade-out
const transform = ref('')

let timer: any = null

const visible = computed(() => (props.modelValue !== undefined ? props.modelValue : props.show))

const effects = computed<Effect[]>(() => {
  const v = props.effects ?? props.animationType
  return (v && v.length ? v : (['fade'] as Effect[]))
})

const customStyle = computed(() => props.customStyle ?? props.styles ?? {})

const baseStyle = computed(() => {
  // 默认值（尽量不改变外部 UI，只提供居中能力）
  const def: Record<string, any> = {
    position: 'fixed',
    left: 0,
    right: 0,
    top: 0,
    bottom: 0,
    // #ifndef APP-NVUE
    display: 'flex',
    // #endif
    justifyContent: 'center',
    alignItems: 'center'
  }
  const merged = Object.assign({}, def, customStyle.value)
  return merged
})

const wrapStyle = computed(() => {
  const style: Record<string, any> = {
    ...baseStyle.value,
    transitionDuration: `${props.duration! / 1000}s`,
    transform: transform.value
  }
  return style
})

function handleTap() {
  emit('click', { visible: rendered.value })
}

function calcStyles(open: boolean) {
  const styles: any = { transform: '' }
  effects.value.forEach((m) => {
    switch (m) {
      case 'fade':
        styles.opacity = open ? 1 : 0
        break
      case 'slide-top':
        styles.transform += `translateY(${open ? '0' : '-100%'}) `
        break
      case 'slide-right':
        styles.transform += `translateX(${open ? '0' : '100%'}) `
        break
      case 'slide-bottom':
        styles.transform += `translateY(${open ? '0' : '100%'}) `
        break
      case 'slide-left':
        styles.transform += `translateX(${open ? '0' : '-100%'}) `
        break
      case 'zoom-in':
        styles.transform += `scale(${open ? 1 : 0.8}) `
        break
      case 'zoom-out':
        styles.transform += `scale(${open ? 1 : 1.2}) `
        break
    }
  })
  return styles
}

function open() {
  clearTimeout(timer)
  rendered.value = true
  transform.value = ''
  fadeClass.value = ''

  // 先设置到“关闭态”，再进入“打开态”
  const init = calcStyles(false)

  // #ifdef APP-NVUE
  // NVUE：先同步到初始状态（用原生动画直接 set）
  if (aniRef.value?.ref) {
    animation.transition(
      aniRef.value.ref,
      {
        styles: init,
        duration: 0,
        timingFunction: 'ease',
        needLayout: false,
        delay: 0
      },
      () => {}
    )
  }
  // #endif

  // #ifndef APP-NVUE
  // H5/小程序：用 class + transform 字符串
  if (init.opacity !== undefined) fadeClass.value = 'z-transition--fade-out'
  transform.value = init.transform || ''
  // #endif

  nextTick(() => {
    setTimeout(() => animate(true), 50)
  })
}

function close() {
  clearTimeout(timer)
  animate(false)
}

function animate(opening: boolean) {
  const styles = calcStyles(opening)

  // #ifdef APP-NVUE
  if (!aniRef.value?.ref) return
  animation.transition(
    aniRef.value.ref,
    {
      styles,
      duration: props.duration,
      timingFunction: 'ease',
      needLayout: false,
      delay: 0
    },
    () => {
      if (!opening) rendered.value = false
      emit('change', { visible: rendered.value })
    }
  )
  // #endif

  // #ifndef APP-NVUE
  transform.value = styles.transform || ''
  if (styles.opacity !== undefined) {
    fadeClass.value = `z-transition--fade-${opening ? 'in' : 'out'}`
  }
  timer = setTimeout(() => {
    if (!opening) rendered.value = false
    emit('change', { visible: rendered.value })
  }, props.duration)
  // #endif
}

watch(
  () => visible.value,
  (v) => {
    if (v) open()
    else if (rendered.value) close()
  },
  { immediate: true }
)
</script>

<style scoped>
.z-transition {
  transition-timing-function: ease;
  transition-property: transform, opacity;
  position: relative;
  z-index: 99;
}

.z-transition--fade-out {
  opacity: 0;
}

.z-transition--fade-in {
  opacity: 1;
}
</style>
