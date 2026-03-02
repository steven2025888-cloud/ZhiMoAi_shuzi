<template>
  <view
    v-if="rendered"
    class="z-toast"
    :class="[{ 'is-visible': visible }]"
    :style="containerStyle"
      >
    <view class="z-toast__card" :style="cardStyle">
      <slot>
        <view v-if="cfg.loading" class="z-toast__spinner" aria-hidden="true" />
        <ZIcon
          v-else-if="showIcon"
          class="z-toast__icon"
          :src="cfg.iconSrc"
          :name="iconName"
          :size="cfg.iconSize"
          :color="iconColorFinal"
        />
        <text
          v-if="cfg.text"
          class="z-toast__text"
          :style="{ fontSize: textSizeVal, color: cfg.textColor }"
        >
          {{ cfg.text }}
        </text>
        <text
          v-if="cfg.subText"
          class="z-toast__sub"
          :style="{ fontSize: subTextSizeVal, color: cfg.subTextColor }"
        >
          {{ cfg.subText }}
        </text>
      </slot>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import ZIcon from '../z-icon/z-icon.vue'

/**
 * z-toast（轻提示）
 * ✅ 无遮罩层（不会拦截底层点击）
 * ✅ 位置：top / center / bottom（默认居中）
 * ✅ 每次 show 都会从默认配置重置，避免“串状态”
 */
const props = defineProps({
  /** v-model（可选） */
  modelValue: { type: Boolean, default: false },

  /** 默认文案 */
  text: { type: String, default: '' },
  subText: { type: String, default: '' },

  /** 预设：success / error / warning / info / none */
  preset: { type: String, default: 'none' },

  /** Iconify 名（优先级低于 iconSrc） */
  icon: { type: String, default: '' },

  /** 图片地址（本地/线上都可，例如：/static/logo.png） */
  iconSrc: { type: String, default: '' },

  /** 图标尺寸（rpx / px 都可） */
  iconSize: { type: [String, Number], default: 44 },

  /** 图标颜色（仅 Iconify H5 / iconfont可生效；图片不一定） */
  iconColor: { type: String, default: '' },

  /** loading 模式（会显示转圈，不展示 icon） */
  loading: { type: Boolean, default: false },

  /** 自动关闭时间（ms），0 表示不自动关闭 */
  duration: { type: Number, default: 2000 },

  /** 位置：top / center / bottom */
  position: { type: String, default: 'center' },

  /** top/bottom 额外偏移（rpx/px） */
  offset: { type: [Number, String], default: 0 },

  /** 卡片背景 */
  background: { type: String, default: 'rgba(0,0,0,.72)' },

  /** 文案颜色 */
  textColor: { type: String, default: '#fff' },
  subTextColor: { type: String, default: 'rgba(255,255,255,.85)' },

  /** 文案大小（rpx/px 都可） */
  textSize: { type: [Number, String], default: 28 },
  subTextSize: { type: [Number, String], default: 24 },

  /** 内边距 */
  padding: {
    type: Array,
    default() { return ['22rpx', '28rpx'] },
  },

  /** 圆角 */
  radius: { type: [Number, String], default: 16 },

  /** 最大宽度（建议百分比） */
  maxWidth: { type: [Number, String], default: '72%' },

  /** 层级 */
  zIndex: { type: Number, default: 1001 },
})

const emit = defineEmits(['update:modelValue', 'show', 'hide'])

const rendered = ref(false)
const visible = ref(false)
const timer = ref(null)
const unmountTimer = ref(null)

const presetIcons = {
  success: 'mdi:check-circle-outline',
  error: 'mdi:close-circle-outline',
  warning: 'mdi:alert-circle-outline',
  info: 'mdi:information-outline',
}

const presetColors = {
  success: '#ffffff',
  error: '#ff4d4f',
  warning: '#faad14',
  info: '#1677ff',
}

function toSize(v) {
  if (v === '' || v === null || v === undefined) return ''
  const s = String(v)
  return /[a-z%]/i.test(s) ? s : `${s}rpx`
}

function getBaseCfg() {
  return {
    text: props.text,
    subText: props.subText,
    preset: props.preset,
    icon: props.icon,
    iconSrc: props.iconSrc,
    iconSize: props.iconSize,
    iconColor: props.iconColor,
    loading: props.loading,
    duration: props.duration,
    position: props.position,
    offset: props.offset,
    background: props.background,
    textColor: props.textColor,
    subTextColor: props.subTextColor,
    textSize: props.textSize,
    subTextSize: props.subTextSize,
    padding: props.padding,
    radius: props.radius,
    maxWidth: props.maxWidth,
    zIndex: props.zIndex,
  }
}

/** 当前配置（show 时会先重置成 base 再覆盖） */
const cfg = reactive(getBaseCfg())

function resetCfg() {
  const base = getBaseCfg()
  Object.keys(base).forEach((k) => { cfg[k] = base[k] })
}

const textSizeVal = computed(() => toSize(cfg.textSize))
const subTextSizeVal = computed(() => toSize(cfg.subTextSize))
const radiusVal = computed(() => toSize(cfg.radius))
const maxWidthVal = computed(() => toSize(cfg.maxWidth))
const offsetVal = computed(() => toSize(cfg.offset || 0))

const pad = computed(() => {
  const p = Array.isArray(cfg.padding) ? cfg.padding : []
  const top = p[0] || '32rpx'
  const right = p[1] || '32rpx'
  const bottom = p[2] || top
  const left = p[3] || right
  return [top, right, bottom, left]
})

const iconName = computed(() => {
  if (cfg.iconSrc) return ''
  const preset = String(cfg.preset || 'none').toLowerCase()
  if (preset !== 'none' && presetIcons[preset]) return presetIcons[preset]
  return cfg.icon || ''
})

const showIcon = computed(() => !!(cfg.iconSrc || iconName.value))

const iconColorFinal = computed(() => {
  // 图片图标不做染色
  if (cfg.iconSrc) return ''
  // 用户显式传入 iconColor 时优先
  if (cfg.iconColor) return cfg.iconColor
  const preset = String(cfg.preset || 'none').toLowerCase()
  if (presetColors[preset]) return presetColors[preset]
  return '#fff'
})

const containerStyle = computed(() => {
  const pos = String(cfg.position || 'center')
  const style = {
    zIndex: cfg.zIndex,
    pointerEvents: 'none',
    paddingLeft: '24rpx',
    paddingRight: '24rpx',
  }

  if (pos === 'top') {
    style.justifyContent = 'flex-start'
    style.paddingTop = offsetVal.value || '24rpx'
    if (!cfg.offset) style.paddingTop = '24rpx'
  } else if (pos === 'bottom') {
    style.justifyContent = 'flex-end'
    style.paddingBottom = offsetVal.value || '24rpx'
    if (!cfg.offset) style.paddingBottom = '24rpx'
  } else {
    style.justifyContent = 'center'
  }
  return style
})

const cardStyle = computed(() => ({
  maxWidth: maxWidthVal.value,
  paddingTop: pad.value[0],
  paddingRight: pad.value[1],
  paddingBottom: pad.value[2],
  paddingLeft: pad.value[3],
  background: cfg.background,
  borderRadius: radiusVal.value,
  pointerEvents: 'auto',

  opacity: visible.value ? 1 : 0,
  transform: visible.value ? 'scale(1)' : 'scale(.96)',
  transition: 'opacity .18s ease, transform .18s ease',
}))

function clearTimer() {
  if (timer.value) {
    clearTimeout(timer.value)
    timer.value = null
  }
}

function clearUnmountTimer() {
  if (unmountTimer.value) {
    clearTimeout(unmountTimer.value)
    unmountTimer.value = null
  }
}

function hide() {
  clearTimer()
  clearUnmountTimer()
  visible.value = false
  emit('update:modelValue', false)
  emit('hide')

  // 等动画结束再卸载，避免闪烁
  unmountTimer.value = setTimeout(() => {
    rendered.value = false
  }, 200)
}

function show(options = {}) {
  clearTimer()
  clearUnmountTimer()

  // 每次 show 都重置一次，避免串状态
  resetCfg()

  // 覆盖配置（只覆盖传入项）
  Object.keys(options).forEach((k) => {
    if (k in cfg) cfg[k] = options[k]
  })

  rendered.value = true
  nextTick(() => {
    // 已经显示时，直接更新并重新计时
    if (!visible.value) {
      setTimeout(() => { visible.value = true }, 16)
    }

    emit('update:modelValue', true)
    emit('show', { ...cfg })

    const d = Number(cfg.duration || 0)
    if (d > 0) timer.value = setTimeout(() => hide(), d)
  })
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) show()
    else hide()
  }
)

onBeforeUnmount(() => {
  clearTimer()
  clearUnmountTimer()
})

defineExpose({ show, hide })
</script>

<style scoped>
.z-toast {
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;

  display: flex;
  flex-direction: column;
  align-items: center;

  /* 不拦截底层点击 */
  pointer-events: none;
}

.z-toast__card {
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.z-toast__icon {
  margin-bottom: 10rpx;
}

.z-toast__text {
  font-weight: 400;
  text-align: center;
  /* #ifndef APP-NVUE */
  word-break: break-all;
  /* #endif */
  line-height: 1.35;
}

.z-toast__sub {
  margin-top: 10rpx;
  text-align: center;
  /* #ifndef APP-NVUE */
  word-break: break-all;
  /* #endif */
  line-height: 1.35;
}

.z-toast__spinner {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  border-width: 5rpx;
  border-style: solid;
  border-color: rgba(255,255,255,.25);
  border-top-color: rgba(255,255,255,.95);
  margin-bottom: 10rpx;

  /* #ifndef APP-NVUE */
  animation: zToastSpin 0.9s linear infinite;
  /* #endif */
}

/* #ifndef APP-NVUE */
@keyframes zToastSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
/* #endif */
</style>
