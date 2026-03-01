<template>
  <view class="zsb" :class="modeClass" :style="wrapStyle" @tap="onWrapTap">
    <!-- outside-left icon -->
    <view v-if="showIcon && iconPlacement === 'outside-left'" class="zsb__outer" @tap.stop="onIconTap">
      <slot name="icon">
        <z-icon :name="iconName" :size="iconSize" :color="iconColorResolved" />
      </slot>
    </view>

    <view class="zsb__field" :class="{ 'is-focus': isFocused, 'is-disabled': disabled }" :style="fieldStyle">
      <!-- inside-left icon -->
      <view v-if="showIcon && iconPlacement === 'inside-left'" class="zsb__in zsb__in--left" @tap.stop="onIconTap">
        <slot name="icon">
          <z-icon :name="iconName" :size="iconSize" :color="iconColorResolved" />
        </slot>
      </view>

      <input
        class="zsb__input"
        :value="modelValue"
        :disabled="disabled"
        :maxlength="maxlength"
        :placeholder="placeholder"
        :placeholder-class="placeholderClass"
        :confirm-type="confirmType"
        :focus="innerFocus"
        @focus="handleFocus"
        @blur="handleBlur"
        @input="handleInput"
        @confirm="handleConfirm"
        @tap.stop="emit('click')"
      />

      <!-- inside-right icon -->
      <view v-if="showIcon && iconPlacement === 'inside-right'" class="zsb__in zsb__in--right" @tap.stop="onIconTap">
        <slot name="icon">
          <z-icon :name="iconName" :size="iconSize" :color="iconColorResolved" />
        </slot>
      </view>

      <view class="zsb__right">
        <view v-if="clearable && !!modelValue && !disabled" class="zsb__clear" @tap.stop="clear">
          <z-icon name="mdi:close" :size="28" :color="mode === 'dark' ? 'rgba(255,255,255,.6)' : 'rgba(0,0,0,.4)'" />
        </view>

        <slot name="right" />

        <view
          v-if="showSearchButton"
          class="zsb__btn"
          :class="['v-' + buttonVariant, 's-' + buttonSize, 'r-' + buttonRadius]"
          :style="buttonStyle"
          @tap.stop="onSearchTap"
        >
          <z-icon v-if="buttonIcon" :name="buttonIcon" :size="buttonIconSize" :color="buttonIconColor" class="zsb__btn-icon" />
          <text v-if="searchText" class="zsb__btn-text">{{ searchText }}</text>
        </view>
      </view>
    </view>

    <!-- outside-right icon -->
    <view v-if="showIcon && iconPlacement === 'outside-right'" class="zsb__outer" @tap.stop="onIconTap">
      <slot name="icon">
        <z-icon :name="iconName" :size="iconSize" :color="iconColorResolved" />
      </slot>
    </view>

    <view
      v-if="showCancel"
      class="zsb__cancel"
      :class="{ 'is-disabled': disabled }"
      :style="{ color: cancelColor }"
      @tap.stop="onCancel"
    >
      {{ cancelText }}
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type ButtonVariant = 'solid' | 'outline' | 'ghost' | 'text' | 'gradient'
type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'
type ButtonRadius = 'none' | 'sm' | 'md' | 'lg' | 'full'
type Mode = 'light' | 'dark'
type IconPlacement = 'inside-left' | 'inside-right' | 'outside-left' | 'outside-right'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  disabled?: boolean
  clearable?: boolean
  focus?: boolean
  maxlength?: number
  confirmType?: string

  /** theme */
  mode?: Mode
  activeColor?: string

  /** container */
  background?: string
  padding?: number

  /** field */
  inputBackground?: string
  radius?: number
  height?: number
  borderColor?: string
  shadow?: boolean

  /** icon */
  showIcon?: boolean
  iconName?: string
  iconPlacement?: IconPlacement
  iconSize?: number
  iconColor?: string

  /** button */
  showSearchButton?: boolean
  searchText?: string
  buttonVariant?: ButtonVariant
  buttonSize?: ButtonSize
  buttonRadius?: ButtonRadius
  buttonMinWidth?: number
  buttonIcon?: string
  buttonIconSize?: number

  /** cancel */
  showCancel?: boolean
  cancelText?: string
  cancelColor?: string

  /** behavior */
  tapToFocus?: boolean
}>(), {
  placeholder: '搜索关键词',
  disabled: false,
  clearable: true,
  focus: false,
  maxlength: 140,
  confirmType: 'search',

  mode: 'light',
  activeColor: '#6366f1',

  background: 'transparent',
  padding: 0,

  inputBackground: '#ffffff',
  radius: 10,
  height: 76,
  borderColor: 'rgba(15,23,42,0.10)',
  shadow: false,

  showIcon: true,
  iconName: 'mdi:magnify',
  iconPlacement: 'inside-left',
  iconSize: 40,
  iconColor: '',

  showSearchButton: true,
  searchText: '搜索',
  buttonVariant: 'solid',
  buttonSize: 'md',
  buttonRadius: 'md',
  buttonMinWidth: 0,
  buttonIcon: '',
  buttonIconSize: 32,

  showCancel: false,
  cancelText: '取消',
  cancelColor: 'rgba(0,0,0,0.65)',

  tapToFocus: true
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
  (e: 'input', v: string): void
  (e: 'change', v: string): void
  (e: 'focus'): void
  (e: 'blur'): void
  (e: 'clear'): void
  (e: 'confirm', v: string): void
  (e: 'search', v: string): void
  (e: 'cancel'): void
  (e: 'click'): void
  (e: 'icon'): void
}>()

const isFocused = ref(false)
const innerFocus = ref(!!props.focus)

watch(() => props.focus, (v) => { innerFocus.value = !!v })

const sizeMap = {
  xs: { btnH: 40, btnFont: 20, padX: 10, iconSize: 22 },
  sm: { btnH: 46, btnFont: 22, padX: 12, iconSize: 24 },
  md: { btnH: 52, btnFont: 24, padX: 14, iconSize: 26 },
  lg: { btnH: 58, btnFont: 26, padX: 16, iconSize: 28 }
} as const


const radiusMap = {
  none: '0',
  sm: '8rpx',
  md: '14rpx',
  lg: '20rpx',
  full: '999rpx'
} as const

const cur = computed(() => sizeMap[props.buttonSize])

const modeClass = computed(() => props.mode === 'dark' ? 'is-dark' : 'is-light')

const placeholderClass = computed(() => props.mode === 'dark' ? 'zsb__placeholder--dark' : 'zsb__placeholder')

const iconColorResolved = computed(() => {
  if (props.iconColor) return props.iconColor
  return props.mode === 'dark' ? 'rgba(255,255,255,0.92)' : 'rgba(17,24,39,0.70)'
})

const wrapStyle = computed(() => ({
  background: props.background,
  padding: props.padding ? `${props.padding}rpx` : undefined
}))

const fieldStyle = computed(() => ({
  height: `${props.height}rpx`,
  borderRadius: `${props.radius}rpx`,
  background: props.inputBackground,
  borderColor: props.borderColor,
  boxShadow: props.shadow
    ? (props.mode === 'dark'
        ? '0 10rpx 28rpx rgba(0,0,0,0.40)'
        : '0 8rpx 24rpx rgba(15,23,42,0.08)')
    : 'none'
}))

const buttonStyle = computed(() => {
  const style: Record<string, string> = {
    height: `${cur.value.btnH}rpx`,
    borderRadius: radiusMap[props.buttonRadius],
    padding: `0 ${cur.value.padX}rpx`
  }
  if (props.buttonMinWidth > 0) {
    style.minWidth = `${props.buttonMinWidth}rpx`
  }
  // 主题色应用
  if (props.buttonVariant === 'solid') {
    style.background = props.activeColor
    style.borderColor = props.activeColor
  } else if (props.buttonVariant === 'outline') {
    style.borderColor = props.activeColor
    style.color = props.activeColor
  } else if (props.buttonVariant === 'gradient') {
    style.background = `linear-gradient(135deg, ${props.activeColor} 0%, ${adjustColor(props.activeColor, 30)} 100%)`
    style.border = 'none'
  }
  return style
})

// 按钮图标颜色
const buttonIconColor = computed(() => {
  if (props.buttonVariant === 'solid' || props.buttonVariant === 'gradient') return '#fff'
  if (props.buttonVariant === 'outline') return props.activeColor
  return props.mode === 'dark' ? 'rgba(255,255,255,.9)' : 'rgba(0,0,0,.7)'
})

// 颜色调整函数
function adjustColor(hex: string, percent: number): string {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = Math.min(255, ((num >> 16) & 0xff) + percent)
  const g = Math.min(255, ((num >> 8) & 0xff) + percent)
  const b = Math.min(255, (num & 0xff) + percent)
  return `rgb(${r},${g},${b})`
}

const placeholder = computed(() => props.placeholder)
const maxlength = computed(() => props.maxlength)
const confirmType = computed(() => props.confirmType)

const showIcon = computed(() => props.showIcon)
const iconName = computed(() => props.iconName)
const iconPlacement = computed(() => props.iconPlacement)
const iconSize = computed(() => props.iconSize)

function handleInput(e: any) {
  const v = (e?.detail?.value ?? '') as string
  emit('update:modelValue', v)
  emit('input', v)
  emit('change', v)
}

function handleConfirm() {
  emit('confirm', props.modelValue)
  emit('search', props.modelValue)
}

function handleFocus() {
  isFocused.value = true
  emit('focus')
}

function handleBlur() {
  isFocused.value = false
  emit('blur')
}

function clear() {
  emit('update:modelValue', '')
  emit('clear')
}

function onSearchTap() {
  if (props.disabled) return
  emit('search', props.modelValue)
}

function onCancel() {
  if (props.disabled) return
  emit('cancel')
}

function onIconTap() {
  if (props.disabled) return
  emit('icon')
}

function onWrapTap() {
  emit('click')
  if (!props.tapToFocus || props.disabled) return
  innerFocus.value = true
  setTimeout(() => (innerFocus.value = false), 10)
}
</script>

<style scoped>
.zsb{ display:flex; align-items:center; gap: 14rpx; }

.zsb__outer{
  width: 72rpx;
  height: 72rpx;
  border-radius: 18rpx;
  display:flex;
  align-items:center;
  justify-content:center;
}

.zsb__field{
  flex:1;
  display:flex;
  align-items:center;
  border: 2rpx solid rgba(15,23,42,0.10);
  padding: 0 14rpx;
  box-sizing:border-box;
  overflow:hidden;
  transition: all 0.2s ease;
}
.zsb__field.is-focus{
  border-color: rgba(99,102,241,0.5);
  box-shadow: 0 0 0 4rpx rgba(99,102,241,0.1);
}

.zsb__in{
  width: 56rpx;
  height: 56rpx;
  display:flex;
  align-items:center;
  justify-content:center;
  flex-shrink: 0;
}

.zsb__input{
  flex:1;
  font-size: 28rpx;
  height: 100%;
  padding: 0 8rpx;
  box-sizing:border-box;
  background: transparent;
}

.zsb__placeholder{ color: rgba(15,23,42,0.35); }
.zsb__placeholder--dark{ color: rgba(255,255,255,0.45); }

.zsb__right{ display:flex; align-items:center; gap: 8rpx; flex-shrink: 0; }

.zsb__clear{
  width: 44rpx;
  height: 44rpx;
  display:flex;
  align-items:center;
  justify-content:center;
  border-radius: 999rpx;
  background: rgba(0,0,0,0.06);
  transition: all 0.15s ease;
}
.zsb__clear:active{
  transform: scale(0.9);
  background: rgba(0,0,0,0.1);
}

/* 按钮基础样式 */
.zsb__btn{
  display:flex;
  align-items:center;
  justify-content:center;
  gap: 6rpx;
  box-sizing:border-box;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.zsb__btn:active{
  transform: scale(0.96);
  opacity: 0.9;
}
.zsb__btn-icon{
  flex-shrink: 0;
}
.zsb__btn-text{
  line-height: 1;
  white-space: nowrap;
}

/* 按钮变体 */
.zsb__btn.v-solid{
  background: #6366f1;
  border: none;
  box-shadow: 0 4rpx 12rpx rgba(99,102,241,0.3);
}
.zsb__btn.v-solid .zsb__btn-text{ color:#fff; font-weight: 500; }

.zsb__btn.v-outline{
  background: transparent;
  border: 2rpx solid #6366f1;
}
.zsb__btn.v-outline .zsb__btn-text{ color: #6366f1; }

.zsb__btn.v-ghost{
  background: rgba(99,102,241,0.08);
  border: none;
}
.zsb__btn.v-ghost .zsb__btn-text{ color: #6366f1; }

.zsb__btn.v-text{
  background: transparent;
  border: none;
  padding: 0 12rpx !important;
}
.zsb__btn.v-text .zsb__btn-text{ color: #6366f1; }

.zsb__btn.v-gradient{
  border: none;
  box-shadow: 0 4rpx 16rpx rgba(99,102,241,0.35);
}
.zsb__btn.v-gradient .zsb__btn-text{ color:#fff; font-weight: 500; }

/* 按钮尺寸 */
.zsb__btn.s-xs .zsb__btn-text{ font-size: 24rpx; }
.zsb__btn.s-sm .zsb__btn-text{ font-size: 26rpx; }
.zsb__btn.s-md .zsb__btn-text{ font-size: 28rpx; }
.zsb__btn.s-lg .zsb__btn-text{ font-size: 30rpx; }

/* 按钮圆角 */
.zsb__btn.r-none{ border-radius: 0; }
.zsb__btn.r-sm{ border-radius: 8rpx; }
.zsb__btn.r-md{ border-radius: 14rpx; }
.zsb__btn.r-lg{ border-radius: 20rpx; }
.zsb__btn.r-full{ border-radius: 999rpx; }

.zsb__cancel{
  font-size: 28rpx;
  padding: 8rpx 6rpx;
  color: rgba(0,0,0,0.65);
  transition: all 0.15s ease;
}
.zsb__cancel:active{
  opacity: 0.7;
}

.is-disabled{ opacity: .5; pointer-events: none; }

/* dark mode overrides */
.is-dark .zsb__field{ border-color: rgba(255,255,255,0.15); }
.is-dark .zsb__field.is-focus{
  border-color: rgba(129,140,248,0.5);
  box-shadow: 0 0 0 4rpx rgba(129,140,248,0.15);
}
.is-dark .zsb__input{ color: rgba(255,255,255,0.94); }
.is-dark .zsb__clear{ background: rgba(255,255,255,0.12); }

.is-dark .zsb__btn.v-outline{ border-color: rgba(255,255,255,0.25); }
.is-dark .zsb__btn.v-outline .zsb__btn-text{ color: rgba(255,255,255,0.9); }
.is-dark .zsb__btn.v-ghost{ background: rgba(255,255,255,0.1); }
.is-dark .zsb__btn.v-ghost .zsb__btn-text{ color: rgba(255,255,255,0.9); }
.is-dark .zsb__btn.v-text .zsb__btn-text{ color: rgba(255,255,255,0.9); }
</style>
