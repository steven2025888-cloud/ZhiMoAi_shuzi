<template>
  <view
    class="z-divider"
    :class="[{ 'z-divider--vertical': props.vertical, 'z-divider--disabled': props.disabled }]"
    :style="wrapStyle"
  >
    <!-- horizontal -->
    <template v-if="!props.vertical">
      <view class="z-divider__line" :style="leftLineStyle"></view>

      <view
        v-if="hasContent"
        class="z-divider__content"
        :style="contentStyle"
      >
        <slot>
          <text
            v-if="props.text"
            class="z-divider__text"
            :style="textStyle"
          >{{ props.text }}</text>
        </slot>
      </view>

      <view class="z-divider__line" :style="rightLineStyle"></view>
    </template>

    <!-- vertical -->
    <template v-else>
      <view class="z-divider__vline" :style="vLineStyle"></view>
      <view v-if="hasContent" class="z-divider__vcontent" :style="vContentStyle">
        <slot>
          <text v-if="props.text" class="z-divider__text" :style="textStyle">{{ props.text }}</text>
        </slot>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'

type DividerAlign = 'left' | 'center' | 'right'
type DividerVariant = 'solid' | 'dashed' | 'dotted'

const slots = useSlots()

const props = withDefaults(defineProps<{
  /** text content */
  text?: string

  /** line color: support solid color or linear-gradient(...) */
  lineColor?: string
  /** text color */
  textColor?: string

  /** font size rpx */
  size?: number
  /** font weight */
  weight?: number | string

  /** total width (horizontal divider). default 100% */
  width?: string | number
  /** min height (horizontal) / height (vertical) */
  height?: string | number

  /** thickness of line */
  thickness?: string | number
  /** gap between line and content */
  gap?: string | number
  /** content position */
  align?: DividerAlign

  /** inset: left/right padding for lines (horizontal only) */
  inset?: string | number

  /** line style */
  variant?: DividerVariant

  /** vertical divider */
  vertical?: boolean

  /** disabled (reduce opacity) */
  disabled?: boolean

  /** tag passthrough (for future events) */
  tag?: any
}>(), {
  text: '',
  lineColor: 'rgba(0,0,0,0.12)',
  textColor: 'rgba(0,0,0,0.45)',
  size: 24,
  weight: 500,
  width: '100%',
  height: 80,
  thickness: 2,
  gap: 16,
  align: 'center',
  inset: 0,
  variant: 'solid',
  vertical: false,
  disabled: false,
  tag: 0
})

function toUnit(v: any, unit = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${unit}`
  return String(v)
}

const hasSlot = computed(() => !!slots.default)
const hasText = computed(() => !!(props.text && String(props.text).trim().length > 0))
const hasContent = computed(() => hasSlot.value || hasText.value)

const isGradient = computed(() => (props.lineColor || '').includes('gradient'))

const wrapStyle = computed(() => {
  const style: Record<string, any> = {
    width: props.vertical ? 'auto' : toUnit(props.width, 'rpx'),
    minHeight: props.vertical ? 'auto' : toUnit(props.height, 'rpx'),
    opacity: props.disabled ? 0.55 : 1
  }
  return style
})

const textStyle = computed(() => ({
  fontSize: `${props.size}rpx`,
  fontWeight: props.weight as any,
  color: props.textColor,
  lineHeight: 1.1
}))

const contentStyle = computed(() => ({
  marginLeft: toUnit(props.gap),
  marginRight: toUnit(props.gap),
  paddingLeft: '10rpx',
  paddingRight: '10rpx',
  borderRadius: '999rpx',
  background: 'transparent'
}))

const insetPx = computed(() => toUnit(props.inset))
const thick = computed(() => toUnit(props.thickness))

function lineBaseStyle() {
  const style: Record<string, any> = {
    height: thick.value,
    borderRadius: '999rpx',
    flex: 1,
    minWidth: 0,
    marginLeft: insetPx.value || '0rpx',
    marginRight: insetPx.value || '0rpx'
  }

  // border-style variants
  if (props.variant === 'solid') {
    if (isGradient.value) style.backgroundImage = props.lineColor
    else style.background = props.lineColor
  } else {
    style.background = 'transparent'
    style.borderTopWidth = thick.value
    style.borderTopStyle = props.variant
    style.borderTopColor = props.lineColor
    style.height = '0'
  }
  return style
}

const leftLineStyle = computed(() => {
  const s = lineBaseStyle()
  // align affects how lines split
  if (props.align === 'left') s.flex = 0.25
  if (props.align === 'right') s.flex = 1
  return s
})

const rightLineStyle = computed(() => {
  const s = lineBaseStyle()
  if (props.align === 'left') s.flex = 1
  if (props.align === 'right') s.flex = 0.25
  return s
})

/** vertical */
const vLineStyle = computed(() => {
  const style: Record<string, any> = {
    width: thick.value,
    height: toUnit(props.height, 'rpx') || '60rpx',
    borderRadius: '999rpx'
  }
  if (props.variant === 'solid') {
    if (isGradient.value) style.backgroundImage = props.lineColor
    else style.background = props.lineColor
  } else {
    style.background = 'transparent'
    style.borderLeftWidth = thick.value
    style.borderLeftStyle = props.variant
    style.borderLeftColor = props.lineColor
    style.width = '0'
  }
  return style
})

const vContentStyle = computed(() => ({
  marginTop: toUnit(props.gap),
  padding: '0 10rpx'
}))
</script>

<style scoped>
.z-divider{
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.z-divider__line{
  box-sizing: border-box;
}
.z-divider__content{
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 70%;
}
.z-divider__text{
  display: block;
  text-align: center;
  word-break: break-word;
}
.z-divider--vertical{
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.z-divider__vline{
  box-sizing: border-box;
}
.z-divider__vcontent{
  display:flex;
  align-items:center;
  justify-content:center;
}
.z-divider--disabled{
  pointer-events: none;
}
</style>
