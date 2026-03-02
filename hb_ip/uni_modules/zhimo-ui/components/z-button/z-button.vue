<template>
  <view
    class="z-btn"
    :class="cls"
    :style="styleObj"
    @tap="onTap"
  >
    <view class="z-btn__inner">
      <view
        v-if="isLoading"
        class="z-btn__spinner"
        :style="spinnerStyle"
        aria-hidden="true"
      />
      <text v-if="displayText" class="z-btn__text" :style="{ color: textColor, fontSize: fontSize }">
        {{ displayText }}
      </text>
      <slot v-else />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type BtnType =
  | 'default'
  | 'primary'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'dark'
  | 'light'
  | 'gray'
  | 'purple'
  | 'pink'
  | 'teal'
  | 'cyan'
  | 'orange'
  | 'indigo'
  | 'black'
  | 'yellow'
  | 'link'

type BtnSize = 'xs' | 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    text?: string
    type?: BtnType
    size?: BtnSize
    plain?: boolean
    round?: boolean
    block?: boolean

    width?: string | boolean
    height?: string
    radius?: string
    margin?: string | string[]

    background?: string
    color?: string
    borderColor?: string

    disabled?: boolean
    disabledBackground?: string
    disabledColor?: string

    loading?: boolean
    loadingText?: string
    loadingColor?: string
    loadingSize?: string
  }>(),
  {
    text: '',
    type: 'default',
    size: 'md',
    plain: false,
    round: false,
    block: false,
    width: false,
    height: '',
    radius: '',
    margin: () => [],
    background: '',
    color: '',
    borderColor: '',
    disabled: false,
    disabledBackground: '',
    disabledColor: '',
    loading: false,
    loadingText: '',
    loadingColor: '',
    loadingSize: '26rpx'
  }
)

const emit = defineEmits<{
  (e: 'click', ev: any): void
  (e: 'update:loading', v: boolean): void
}>()

/**
 * Local loading state supports imperative control via component ref,
 * while still respecting external prop updates.
 */
const localLoading = ref<boolean>(false)
watch(
  () => props.loading,
  (v) => {
    localLoading.value = v
  },
  { immediate: true }
)

const isLoading = computed(() => !!localLoading.value)

const PALETTE: Record<BtnType, { bg: string; fg: string; bd: string }> = {
  default: { bg: '#ffffff', fg: '#1f2937', bd: '#d1d5db' },
  primary: { bg: '#3b82f6', fg: '#ffffff', bd: '#3b82f6' },
  success: { bg: '#22c55e', fg: '#ffffff', bd: '#22c55e' },
  warning: { bg: '#f59e0b', fg: '#111827', bd: '#f59e0b' },
  danger: { bg: '#ef4444', fg: '#ffffff', bd: '#ef4444' },
  info: { bg: '#06b6d4', fg: '#ffffff', bd: '#06b6d4' },
  dark: { bg: '#111827', fg: '#ffffff', bd: '#111827' },
  light: { bg: '#f3f4f6', fg: '#111827', bd: '#e5e7eb' },
  gray: { bg: '#6b7280', fg: '#ffffff', bd: '#6b7280' },
  purple: { bg: '#8b5cf6', fg: '#ffffff', bd: '#8b5cf6' },
  pink: { bg: '#ec4899', fg: '#ffffff', bd: '#ec4899' },
  teal: { bg: '#14b8a6', fg: '#ffffff', bd: '#14b8a6' },
  cyan: { bg: '#22d3ee', fg: '#0f172a', bd: '#22d3ee' },
  orange: { bg: '#fb923c', fg: '#111827', bd: '#fb923c' },
  indigo: { bg: '#6366f1', fg: '#ffffff', bd: '#6366f1' },
  black: { bg: '#000000', fg: '#ffffff', bd: '#000000' },
  yellow: { bg: '#fde047', fg: '#111827', bd: '#fde047' },
  link: { bg: 'transparent', fg: '#3b82f6', bd: 'transparent' }
}

function normalize4(v: string | string[]): [string, string, string, string] {
  const arr = Array.isArray(v) ? v : [v]
  const a0 = arr[0] ?? '0'
  const a1 = arr[1] ?? a0
  const a2 = arr[2] ?? a0
  const a3 = arr[3] ?? a1
  return [a0, a1, a2, a3]
}

const margin4 = computed(() => normalize4(props.margin))

const base = computed(() => PALETTE[props.type] ?? PALETTE.default)

const bgColor = computed(() => {
  if (props.disabled) return props.disabledBackground || '#e5e7eb'
  if (props.background) return props.background
  if (props.plain) return 'transparent'
  return base.value.bg
})

const bdColor = computed(() => {
  if (props.borderColor) return props.borderColor
  if (props.plain) return base.value.bg === 'transparent' ? base.value.fg : base.value.bg
  return base.value.bd
})

const textColor = computed(() => {
  if (props.disabled) return props.disabledColor || '#9ca3af'
  if (props.color) return props.color
  if (props.plain) return base.value.bg === 'transparent' ? base.value.fg : base.value.bg
  return base.value.fg
})

const radius = computed(() => {
  if (props.round) return '9999rpx'
  if (props.radius) return props.radius
  return '14rpx'
})

const height = computed(() => {
  if (props.height) return props.height
  if (props.size === 'xs') return '56rpx'
  if (props.size === 'sm') return '72rpx'
  if (props.size === 'lg') return '96rpx'
  return '84rpx'
})

const paddingX = computed(() => {
  if (props.size === 'xs') return '18rpx'
  if (props.size === 'sm') return '22rpx'
  if (props.size === 'lg') return '30rpx'
  return '26rpx'
})

const fontSize = computed(() => {
  if (props.size === 'xs') return '24rpx'
  if (props.size === 'sm') return '26rpx'
  if (props.size === 'lg') return '30rpx'
  return '28rpx'
})

const width = computed(() => {
  // block takes precedence
  if (props.block) return '100%'
  if (props.width === true) return '100%'
  if (typeof props.width === 'string' && props.width.length > 0) return props.width
  return 'auto'
})

const styleObj = computed(() => ({
  width: width.value,
  height: height.value,
  paddingLeft: paddingX.value,
  paddingRight: paddingX.value,
  marginTop: margin4.value[0],
  marginRight: margin4.value[1],
  marginBottom: margin4.value[2],
  marginLeft: margin4.value[3],
  borderRadius: radius.value,
  background: bgColor.value,
  borderColor: bdColor.value,
  opacity: props.disabled && !props.disabledBackground ? 0.55 : 1
}))

const cls = computed(() => [
  props.type === 'link' ? 'z-btn--link' : '',
  props.plain ? 'z-btn--plain' : '',
  props.block ? 'z-btn--block' : '',
  props.disabled ? 'z-btn--disabled' : '',
  isLoading.value ? 'z-btn--loading' : ''
])

const displayText = computed(() => {
  // loadingText has highest priority when loading
  if (isLoading.value && props.loadingText) return props.loadingText
  if (props.text) return props.text
  return ''
})

const spinnerStyle = computed(() => {
  const c = props.loadingColor || textColor.value
  return {
    width: props.loadingSize,
    height: props.loadingSize,
    borderTopColor: c,
    borderRightColor: c
  }
})

function onTap(ev: any) {
  if (props.disabled || isLoading.value) return
  emit('click', ev)
}

/**
 * Expose methods for imperative control if needed.
 * Example:
 *   const btnRef = ref()
 *   btnRef.value?.setLoading(true)
 */
function setLoading(v: boolean) {
  localLoading.value = !!v
  emit('update:loading', !!v)
}

defineExpose({ setLoading })
</script>

<style scoped>
.z-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  border-width: 1px;
  border-style: solid;
  overflow: hidden;
  transform: translateZ(0);
}

.z-btn--block {
  display: flex;
}

.z-btn__inner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  gap: 10rpx;
}

.z-btn__text {
    line-height: 1;
}

.z-btn--link {
  border-color: transparent !important;
  background: transparent !important;
}

.z-btn--plain {
  background: transparent !important;
}

.z-btn--disabled {
  pointer-events: none;
}

.z-btn__spinner {
  box-sizing: border-box;
  border-width: 3rpx;
  border-style: solid;
  border-left-color: transparent;
  border-bottom-color: transparent;
  border-radius: 9999rpx;
  animation: z-spin 0.8s linear infinite;
}

@keyframes z-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
