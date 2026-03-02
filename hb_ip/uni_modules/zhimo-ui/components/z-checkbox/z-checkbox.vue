<template>
  <view
    class="z-checkbox"
    :class="[{ 'is-disabled': isDisabled }, layoutClass]"
    :style="{ marginRight: gapStyle }"
    @tap.stop="onTap"
  >
    <view
      class="z-checkbox__box"
      :class="[{ 'is-checked': isChecked }, shapeClass, styleClass, { 'is-no-border': isMarkMode && !props.markBorder }]"
      :style="boxStyle"
    >
      <slot name="icon" :checked="isChecked">
        <!-- 有 mark 时显示文字，否则显示图标 -->
        <text v-if="isChecked && isMarkMode" class="z-checkbox__mark" :style="markStyle">{{ props.mark }}</text>
        <z-icon
          v-else-if="isChecked && !isMarkMode"
          :name="checkIcon"
          :size="iconSize"
          :color="checkIconColor"
          class="z-checkbox__icon"
        />
      </slot>

      <checkbox
        class="z-checkbox__native"
        :color="mergedColor"
        :disabled="isDisabled"
        :value="nativeValue"
        :checked="isChecked"
      />
    </view>

    <view v-if="hasText" class="z-checkbox__text" :style="textStyle">
      <slot>{{ props.label }}</slot>
    </view>
  </view>
</template>

<script setup>
import { computed, inject } from 'vue'
import ZIcon from '../z-icon/z-icon.vue'

const props = defineProps({
  /* group usage */
  value: { type: [String, Number, Boolean], default: undefined },

  /* standalone usage */
  modelValue: { type: Boolean, default: undefined },
  checked: { type: Boolean, default: undefined }, // alias for non-vmodel usage

  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },

  // visuals
  color: { type: String, default: '' },       // selected color
  activeColor: { type: String, default: '' }, // alias
  borderColor: { type: String, default: '' }, // unselected border alias
  inactiveColor: { type: String, default: '#d4d4d4' },

  // 样式类型: filled(默认填充) | outline(只���边框) | soft(柔和背景)
  type: { type: String, default: 'filled' },

  shape: { type: String, default: '' },       // square | circle (inherit from group)
  radius: { type: [Number, String], default: '' }, // for square
  size: { type: [Number, String], default: 40 },   // rpx
  gap: { type: Number, default: 14 },              // rpx

  // check appearance
  checkColor: { type: String, default: '' }, // color for check mark (auto detect)
  checkIcon: { type: String, default: 'mdi:check' }, // icon name
  mark: { type: String, default: '' },          // mark text (有值则显示文字而非图标)
  markBorder: { type: Boolean, default: true },  // mark模式是否显示边框
  scale: { type: [Number, String], default: 1 },  // scale for box

  // effects
  shadow: { type: Boolean, default: true },       // colored glow when checked
  shadowStrength: { type: Number, default: 0.18 }, // alpha

  // 文字样式
  textSize: { type: [Number, String], default: 28 }, // rpx
  textColor: { type: String, default: '#333' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const group = inject('zCheckboxGroup', null)

const merged = computed(() => {
  const gp = group?.props || {}
  return {
    color: props.color || props.activeColor || gp.color || '#10b981',
    shape: props.shape || gp.shape || 'square',
    gap: (props.gap ?? gp.gap ?? 16),
    shadow: (gp.shadow ?? props.shadow),
    disabled: !!(gp.disabled || props.disabled),
    type: props.type || gp.type || 'filled',
  }
})

const mergedColor = computed(() => merged.value.color)

const isDisabled = computed(() => merged.value.disabled)

const inGroup = computed(() => !!group && props.value !== undefined)

const nativeValue = computed(() => (props.value === undefined || props.value === null) ? '' : String(props.value))

const isChecked = computed(() => {
  if (inGroup.value) {
    const list = group.value.value || []
    return list.includes(props.value)
  }
  if (props.modelValue !== undefined) return !!props.modelValue
  if (props.checked !== undefined) return !!props.checked
  return false
})

function setStandalone(next) {
  if (props.modelValue !== undefined) emit('update:modelValue', next)
  emit('change', { checked: next, value: props.value })
}

function onTap() {
  if (isDisabled.value) return
  if (inGroup.value) {
    group.toggle(props.value)
    return
  }
  const next = !isChecked.value
  setStandalone(next)
}

import { useSlots } from 'vue'
const slots = useSlots()
const hasText = computed(() => !!props.label || !!slots.default)
const gapStyle = computed(() => `${merged.value.gap}rpx`)

const shapeClass = computed(() => (merged.value.shape === 'circle' ? 'is-circle' : 'is-square'))
const styleClass = computed(() => `is-${merged.value.type}`)
const layoutClass = computed(() => 'is-inline')

// 是否为 mark 模式（有 mark 文字时）
const isMarkMode = computed(() => !!props.mark)

function toRgba(hex, alpha = 0.16) {
  if (typeof hex !== 'string') return `rgba(0,0,0,${alpha})`
  const c = hex.trim()
  const h3 = /^#([0-9a-fA-F]{3})$/
  const h6 = /^#([0-9a-fA-F]{6})$/
  let r, g, b
  if (h3.test(c)) {
    const m = c.match(h3)[1]
    r = parseInt(m[0] + m[0], 16)
    g = parseInt(m[1] + m[1], 16)
    b = parseInt(m[2] + m[2], 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  if (h6.test(c)) {
    const m = c.match(h6)[1]
    r = parseInt(m.slice(0, 2), 16)
    g = parseInt(m.slice(2, 4), 16)
    b = parseInt(m.slice(4, 6), 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  return `rgba(0,0,0,${alpha})`
}

const mergedInactive = computed(() => props.borderColor || props.inactiveColor)

const sizeRpx = computed(() => `${props.size}rpx`)
const radiusStyle = computed(() => {
  if (merged.value.shape === 'circle') return '9999rpx'
  if (props.radius !== '') return typeof props.radius === 'number' ? `${props.radius}rpx` : String(props.radius)
  return '8rpx'
})

// 图标大小（相对于box大小）
const iconSize = computed(() => Math.round(Number(props.size) * 0.6))

// 图标颜色
const checkIconColor = computed(() => {
  if (props.checkColor) return props.checkColor
  const t = merged.value.type
  if (t === 'filled') return '#fff'
  if (t === 'outline') return merged.value.color
  if (t === 'soft') return merged.value.color
  return '#fff'
})

const boxStyle = computed(() => {
  const active = merged.value.color
  const inactive = mergedInactive.value
  const checked = isChecked.value
  const t = merged.value.type
  const markMode = isMarkMode.value
  const noBorder = markMode && !props.markBorder

  let bg, bd
  if (noBorder) {
    // 无边框 mark：透明背景，彩色文字
    bg = 'transparent'
    bd = 'transparent'
  } else if (markMode) {
    // 有边框 mark：强制使用 filled 样式（填充背景 + 白色文字）
    bg = checked ? active : 'transparent'
    bd = checked ? active : inactive
  } else if (t === 'filled') {
    bg = checked ? active : 'transparent'
    bd = checked ? active : inactive
  } else if (t === 'outline') {
    bg = 'transparent'
    bd = checked ? active : inactive
  } else if (t === 'soft') {
    bg = checked ? toRgba(active, 0.12) : 'transparent'
    bd = checked ? active : inactive
  } else {
    bg = checked ? active : 'transparent'
    bd = checked ? active : inactive
  }

  const shadow = (checked && merged.value.shadow && !noBorder && t === 'filled')
    ? `0 4rpx 12rpx ${toRgba(active, props.shadowStrength)}`
    : 'none'

  const scale = Number(props.scale || 1)
  const style = {
    width: sizeRpx.value,
    height: sizeRpx.value,
    borderColor: bd,
    backgroundColor: bg,
    borderRadius: radiusStyle.value,
    boxShadow: shadow,
    transform: scale !== 1 ? `scale(${scale})` : 'none',
    transformOrigin: 'center'
  }
  return style
})

const textStyle = computed(() => ({
  fontSize: `${props.textSize}rpx`,
  color: props.textColor,
}))

// mark 文字颜色：有边框时白色（填充背景），无边框时用主色
const markStyle = computed(() => {
  const noBorder = isMarkMode.value && !props.markBorder
  return {
    color: noBorder ? merged.value.color : '#fff'
  }
})
</script>

<style scoped>
.z-checkbox{
  display:inline-flex;
  align-items:center;
  vertical-align: middle;
}
.z-checkbox.is-disabled{ opacity:.5; }
.z-checkbox__box{
  box-sizing: border-box;
  border-width: 2rpx;
  border-style: solid;
  display:flex;
  align-items:center;
  justify-content:center;
  flex-shrink:0;
  position: relative;
  overflow:hidden;
  transition: all 0.2s ease;
}
.z-checkbox__box.is-no-border{
  border-width: 0;
}

/* 图标居中 */
.z-checkbox__icon{
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-checkbox__mark{
  font-size: 26rpx;
  line-height: 1;
}
.z-checkbox__text{
  margin-left: 10rpx;
  line-height: 1.4;
}

.z-checkbox__native{
  opacity:0;
  position:absolute;
  inset:0;
  width:100%;
  height:100%;
  pointer-events:none;
}

/* 样式类型 */
.z-checkbox__box.is-filled.is-checked{
  border-color: currentColor;
}
.z-checkbox__box.is-outline.is-checked{
  background: transparent;
}
.z-checkbox__box.is-soft.is-checked{
  border-width: 2rpx;
}
</style>