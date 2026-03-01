<template>
  <view 
    class="z-input" 
    :class="rootClasses" 
    :style="rootStyle"
  >
    <!-- 前缀插槽 -->
    <view v-if="$slots.prefix" class="z-input__prefix">
      <slot name="prefix" />
    </view>

    <!-- 原生输入框 -->
    <input
      class="z-input__native"
      :value="innerValue"
      :type="computedType"
      :password="props.type === 'password'"
      :placeholder="placeholder"
      :placeholder-style="computedPlaceholderStyle"
      :disabled="disabled"
      :maxlength="maxlength"
      :focus="focus"
      :confirm-type="confirmType"
      :cursor-spacing="cursorSpacing"
      @input="handleInput"
      @focus="handleFocus"
      @blur="handleBlur"
      @confirm="handleConfirm"
    />

    <!-- 清除按钮 -->
    <view 
      v-if="showClearButton" 
      class="z-input__clear" 
      @tap.stop="handleClear"
    >
      <text class="z-input__clear-icon">×</text>
    </view>

    <!-- 后缀插槽 -->
    <view v-if="$slots.suffix" class="z-input__suffix">
      <slot name="suffix" />
    </view>
  </view>

  <!-- 字数统计 -->
  <view v-if="showCount && maxlength > 0" class="z-input__count">
    <text class="z-input__count-text">
      {{ currentLength }}/{{ maxlength }}
    </text>
  </view>

  <!-- 错误提示 -->
  <view v-if="errorText" class="z-input__error">
    <text class="z-input__error-text">{{ errorText }}</text>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

// ========== Props 定义 ==========
const props = defineProps({
  // 双向绑定值
  modelValue: {
    type: [String, Number],
    default: ''
  },
  // 输入框类型
  type: {
    type: String,
    default: 'text',
    validator: (val) => ['text', 'number', 'idcard', 'digit', 'password'].includes(val)
  },
  // 占位符
  placeholder: {
    type: String,
    default: ''
  },
  // 是否禁用
  disabled: {
    type: Boolean,
    default: false
  },
  // 是否显示清除按钮
  clearable: {
    type: Boolean,
    default: true
  },
  // 最大长度
  maxlength: {
    type: Number,
    default: 140
  },
  // 是否自动聚焦
  focus: {
    type: Boolean,
    default: false
  },
  // 确认按钮文字
  confirmType: {
    type: String,
    default: 'done'
  },
  // 光标与键盘距离
  cursorSpacing: {
    type: Number,
    default: 0
  },
  // 内边距 [垂直, 水平] 单位 rpx
  padding: {
    type: Array,
    default: () => [16, 18]
  },
  // 圆角大小 rpx
  radius: {
    type: Number,
    default: 14
  },
  // 背景色
  background: {
    type: String,
    default: '#fff'
  },
  // 是否显示边框
  border: {
    type: Boolean,
    default: true
  },
  // 无边框时是否显示下划线
  underline: {
    type: Boolean,
    default: true
  },
  // 边框颜色
  borderColor: {
    type: String,
    default: 'rgba(0,0,0,0.12)'
  },
  // 激活时颜色(聚焦)
  activeColor: {
    type: String,
    default: '#2b7cff'
  },
  // 是否显示阴影
  shadow: {
    type: Boolean,
    default: true
  },
  // 文字颜色
  textColor: {
    type: String,
    default: '#111'
  },
  // 占位符颜色
  placeholderColor: {
    type: String,
    default: 'rgba(0,0,0,0.45)'
  },
  // 占位符透明度
  placeholderOpacity: {
    type: Number,
    default: 0.45
  },
  // 错误信息
  error: {
    type: String,
    default: ''
  },
  // 是否显示字数统计
  showCount: {
    type: Boolean,
    default: false
  }
})

// ========== Emits 定义 ==========
const emit = defineEmits([
  'update:modelValue',
  'change',
  'focus',
  'blur',
  'confirm',
  'input',
  'clear'
])

// ========== 状态管理 ==========
const isFocused = ref(false)
const innerValue = ref(String(props.modelValue ?? ''))

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  innerValue.value = String(newVal ?? '')
})

// ========== 计算属性 ==========
// 原生输入框类型
const computedType = computed(() => {
  return props.type === 'password' ? 'text' : props.type
})

// 是否显示清除按钮
const showClearButton = computed(() => {
  return props.clearable && !props.disabled && innerValue.value
})

// 当前字符长度
const currentLength = computed(() => {
  return (innerValue.value || '').length
})

// 错误提示文本
const errorText = computed(() => props.error || '')

// 占位符样式
const computedPlaceholderStyle = computed(() => {
  return `color:${props.placeholderColor};opacity:${props.placeholderOpacity};`
})

// 根元素类名
const rootClasses = computed(() => ({
  'is-disabled': props.disabled,
  'is-error': !!errorText.value,
  'is-focused': isFocused.value,
  'is-underline': !props.border && props.underline
}))

// 根元素样式
const rootStyle = computed(() => {
  const styles = {
    padding: `${props.padding[0]}rpx ${props.padding[1]}rpx`,
    borderRadius: `${props.radius}rpx`,
    background: props.background,
    color: props.textColor
  }

  // 边框样式
  if (props.border) {
    styles.borderWidth = '1px'
    styles.borderStyle = 'solid'
    styles.borderColor = isFocused.value ? props.activeColor : props.borderColor
    
    // 聚焦阴影
    if (isFocused.value && props.shadow) {
      styles.boxShadow = `0 0 0 6rpx ${hexToRgba(props.activeColor, 0.14)}`
    }
  } else {
    styles.borderWidth = '0px'
    
    // 下划线模式
    if (props.underline) {
      const isDefaultActive = props.activeColor === '#2b7cff'
      const userActive = !isDefaultActive ? props.activeColor : ''
      const focusColor = userActive || 'rgba(0,0,0,0.28)'
      
      styles['--underline-color'] = isFocused.value ? focusColor : 'rgba(0,0,0,0.18)'
      styles['--underline-inset'] = `${props.padding[1]}rpx`
    }
  }

  return styles
})

// ========== 工具函数 ==========
/**
 * 将十六进制颜色转换为 rgba
 * @param {string} hex - 十六进制颜色值
 * @param {number} alpha - 透明度
 * @returns {string} rgba 颜色值
 */
function hexToRgba(hex, alpha = 0.18) {
  if (typeof hex !== 'string') {
    return `rgba(0,0,0,${alpha})`
  }

  const color = hex.trim()
  
  // 匹配 #RGB 格式
  const hex3Match = color.match(/^#([0-9a-fA-F]{3})$/)
  if (hex3Match) {
    const [r, g, b] = hex3Match[1].split('').map(c => parseInt(c + c, 16))
    return `rgba(${r},${g},${b},${alpha})`
  }
  
  // 匹配 #RRGGBB 格式
  const hex6Match = color.match(/^#([0-9a-fA-F]{6})$/)
  if (hex6Match) {
    const hex = hex6Match[1]
    const r = parseInt(hex.slice(0, 2), 16)
    const g = parseInt(hex.slice(2, 4), 16)
    const b = parseInt(hex.slice(4, 6), 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  
  return `rgba(0,0,0,${alpha})`
}

// ========== 事件处理 ==========
function handleInput(e) {
  const value = e?.detail?.value ?? ''
  innerValue.value = value
  emit('update:modelValue', value)
  emit('input', value)
  emit('change', value)
}

function handleFocus(e) {
  isFocused.value = true
  emit('focus', e)
}

function handleBlur(e) {
  isFocused.value = false
  emit('blur', e)
}

function handleConfirm(e) {
  emit('confirm', e?.detail?.value ?? innerValue.value)
}

function handleClear() {
  innerValue.value = ''
  emit('update:modelValue', '')
  emit('clear')
  emit('change', '')
}
</script>

<style scoped>
/* ========== 容器样式 ========== */
.z-input {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 80rpx;
  box-sizing: border-box;
  transition: all 0.2s ease;
}

/* 禁用状态 */
.z-input.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 错误状态 */
.z-input.is-error {
  border-color: rgba(255, 0, 0, 0.35) !important;
}

/* 下划线模式 */
.z-input.is-underline::after {
  content: '';
  position: absolute;
  left: var(--underline-inset, 18rpx);
  right: var(--underline-inset, 18rpx);
  bottom: 0;
  height: 1px;
  background: var(--underline-color, rgba(0, 0, 0, 0.18));
  transition: background-color 0.2s ease;
}

/* ========== 输入框样式 ========== */
.z-input__native {
  flex: 1;
  min-width: 0;
  font-size: 26rpx;
  line-height: 1.25;
  background: transparent;
  outline: none;
}

/* ========== 前缀/后缀样式 ========== */
.z-input__prefix,
.z-input__suffix {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.z-input__prefix {
  margin-right: 10rpx;
}

.z-input__suffix {
  margin-left: 10rpx;
}

/* ========== 清除按钮样式 ========== */
.z-input__clear {
  width: 46rpx;
  height: 46rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 8rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.z-input__clear:active {
  opacity: 0.75;
}

.z-input__clear-icon {
  font-size: 30rpx;
  opacity: 0.6;
  line-height: 1;
}

/* ========== 字数统计样式 ========== */
.z-input__count {
  padding: 8rpx 6rpx 0;
  text-align: right;
}

.z-input__count-text {
  font-size: 20rpx;
  opacity: 0.55;
}

/* ========== 错误提示样式 ========== */
.z-input__error {
  padding: 8rpx 6rpx 0;
}

.z-input__error-text {
  font-size: 20rpx;
  color: rgba(255, 0, 0, 0.75);
}
</style>