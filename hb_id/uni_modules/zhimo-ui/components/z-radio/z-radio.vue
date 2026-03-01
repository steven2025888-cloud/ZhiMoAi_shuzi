<template>
  <view
    class="z-radio"
    :class="[{ 'is-disabled': mergedDisabled }, sizeClass, { 'is-block': block }, { 'is-checked': isChecked } ]"
    :style="rootStyle"
    @tap.stop="onTap"
  >
    <view
      v-if="!isIndicatorRight"
      class="z-radio__icon"
      :class="[shapeClass, { 'is-checked': isChecked }, indicatorClass]"
      :style="iconStyle"
    >
      <slot name="icon" :checked="isChecked" :indicator="mergedIndicator">
        <view v-if="isChecked && mergedIndicator === 'dot'" class="z-radio__dot" />
        <view v-else-if="isChecked && mergedIndicator === 'check'" class="z-radio__check" />
      </slot>
    </view>

    <view class="z-radio__body">
      <view class="z-radio__label">
        <slot>{{ label }}</slot>
      </view>
      <view v-if="desc" class="z-radio__desc">
        {{ desc }}
      </view>
    </view>

    <view
      v-if="isIndicatorRight"
      class="z-radio__icon"
      :class="[shapeClass, { 'is-checked': isChecked }, indicatorClass]"
      :style="iconStyle"
    >
      <slot name="icon" :checked="isChecked" :indicator="mergedIndicator">
        <view v-if="isChecked && mergedIndicator === 'dot'" class="z-radio__dot" />
        <view v-else-if="isChecked && mergedIndicator === 'check'" class="z-radio__check" />
      </slot>
    </view>

    <view v-if="$slots.extra" class="z-radio__extra">
      <slot name="extra" :checked="isChecked" />
    </view>
  </view>
</template>

<script setup>
import { computed, inject } from 'vue'

const props = defineProps({
  /** 选项值（必须唯一） */
  value: { type: [String, Number, Boolean], required: true },
  /** 主文本 */
  label: { type: String, default: '' },
  /** 辅助描述 */
  desc: { type: String, default: '' },
  /** 禁用 */
  disabled: { type: Boolean, default: false },

  /** 尺寸：sm | md | lg */
  size: { type: String, default: '' },
  /** 形状：circle | square */
  shape: { type: String, default: '' },
  /** 块级样式（常用于列表） */
  block: { type: Boolean, default: false },

  /** 指示器：dot | check */
  indicator: { type: String, default: '' },
  /** 指示器位置：left | right */
  indicatorPosition: { type: String, default: '' },

  /** 视觉：选中颜色 */
  color: { type: String, default: '' },
  /** 视觉：未选中颜色（边框/对号可用） */
  inactiveColor: { type: String, default: '' },

  /** 文本颜色 */
  textColor: { type: String, default: '' },
  /** 描述颜色 */
  descColor: { type: String, default: '' },

  /** 图标尺寸（例如 32rpx） */
  iconSize: { type: String, default: '' },
  /** 图标边框宽度（例如 2rpx） */
  iconBorderWidth: { type: String, default: '' },
  /** dot 尺寸（例如 14rpx） */
  dotSize: { type: String, default: '' },
  /** check 尺寸（例如 14rpx） */
  checkSize: { type: String, default: '' },

  /** item 间距（例如 12rpx） */
  gap: { type: String, default: '' },
  /** 内边距（例如 8rpx 0 / 16rpx 18rpx） */
  padding: { type: String, default: '' },

  /** block 背景/边框 */
  background: { type: String, default: '' },
  borderColor: { type: String, default: '' },
  /** block 选中背景/边框 */
  activeBackground: { type: String, default: '' },
  activeBorderColor: { type: String, default: '' },

  /** block 圆角（例如 14rpx） */
  radius: { type: String, default: '' },

  /** 选中态外发光（dot 模式） */
  activeShadow: { type: String, default: '' },

  /** 对号颜色（indicator=check 时可单独控制；为空则使用 color） */
  checkColor: { type: String, default: '' },
  /** 对号未选中颜色（为空则使用 inactiveColor） */
  checkInactiveColor: { type: String, default: '' }
})

const group = inject('zRadioGroup', null)

function pick(first, second, fallback) {
  return first ? first : (second ? second : fallback)
}

const mergedDisabled = computed(() => !!(props.disabled || (group && group.props && group.props.disabled)))

const mergedSize = computed(() => pick(props.size, group && group.props && group.props.size, 'md'))
const mergedShape = computed(() => pick(props.shape, group && group.props && group.props.shape, 'circle'))
const mergedIndicator = computed(() => pick(props.indicator, group && group.props && group.props.indicator, 'dot'))
const mergedIndicatorPosition = computed(() => pick(props.indicatorPosition, group && group.props && group.props.indicatorPosition, 'left'))

const mergedColor = computed(() => pick(props.color, group && group.props && group.props.color, '#2b7cff'))
const mergedInactiveColor = computed(() => pick(props.inactiveColor, group && group.props && group.props.inactiveColor, 'rgba(0,0,0,.25)'))

const mergedCheckColor = computed(() => pick(props.checkColor, group && group.props && group.props.checkColor, ''))
const mergedCheckInactiveColor = computed(() => pick(props.checkInactiveColor, group && group.props && group.props.checkInactiveColor, ''))

const mergedTextColor = computed(() => pick(props.textColor, group && group.props && group.props.textColor, 'rgba(0,0,0,.88)'))
const mergedDescColor = computed(() => pick(props.descColor, group && group.props && group.props.descColor, 'rgba(0,0,0,.55)'))

const mergedIconSize = computed(() => pick(props.iconSize, group && group.props && group.props.iconSize, '32rpx'))
const mergedIconBorderWidth = computed(() => pick(props.iconBorderWidth, group && group.props && group.props.iconBorderWidth, '2rpx'))
const mergedDotSize = computed(() => pick(props.dotSize, group && group.props && group.props.dotSize, '14rpx'))
const mergedCheckSize = computed(() => pick(props.checkSize, group && group.props && group.props.checkSize, '14rpx'))

const mergedGap = computed(() => pick(props.gap, group && group.props && group.props.gap, '12rpx'))
const mergedPadding = computed(() => pick(props.padding, group && group.props && group.props.padding, '8rpx 0'))

const mergedBackground = computed(() => pick(props.background, group && group.props && group.props.background, '#fff'))
const mergedBorderColor = computed(() => pick(props.borderColor, group && group.props && group.props.borderColor, 'rgba(0,0,0,.08)'))
const mergedActiveBackground = computed(() => pick(props.activeBackground, group && group.props && group.props.activeBackground, 'rgba(43,124,255,.08)'))
const mergedActiveBorderColor = computed(() => pick(props.activeBorderColor, group && group.props && group.props.activeBorderColor, mergedColor.value))
const mergedRadius = computed(() => pick(props.radius, group && group.props && group.props.radius, '14rpx'))

const mergedActiveShadow = computed(() => {
  // 兼容 group 的 shadow=true/false
  const gp = group && group.props ? group.props : null
  const shadowFlag = gp && typeof gp.shadow === 'boolean' ? gp.shadow : true
  const val = pick(props.activeShadow, gp && gp.activeShadow, '')
  if (!shadowFlag) return 'none'
  return val
})

const isIndicatorRight = computed(() => mergedIndicatorPosition.value === 'right')

const isChecked = computed(() => {
  const gv = group && group.modelValue ? group.modelValue.value : undefined
  return gv === props.value
})

const shapeClass = computed(() => (mergedShape.value === 'square' ? 'is-square' : 'is-circle'))
const sizeClass = computed(() => `is-${mergedSize.value}`)
const indicatorClass = computed(() => (mergedIndicator.value === 'check' ? 'is-check' : 'is-dot'))

function toRgba(hex, alpha) {
  if (typeof hex !== 'string') return `rgba(0,0,0,${alpha})`
  const c = hex.trim()
  const m3 = /^#([0-9a-fA-F]{3})$/.exec(c)
  const m6 = /^#([0-9a-fA-F]{6})$/.exec(c)
  let r, g, b
  if (m3) {
    const h = m3[1]
    r = parseInt(h[0] + h[0], 16)
    g = parseInt(h[1] + h[1], 16)
    b = parseInt(h[2] + h[2], 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  if (m6) {
    const h = m6[1]
    r = parseInt(h.slice(0, 2), 16)
    g = parseInt(h.slice(2, 4), 16)
    b = parseInt(h.slice(4, 6), 16)
    return `rgba(${r},${g},${b},${alpha})`
  }
  return `rgba(0,0,0,${alpha})`
}

const rootStyle = computed(() => {
  const active = mergedColor.value
  const inactive = mergedInactiveColor.value

  const style = {
    '--z-radio-active': active,
    '--z-radio-inactive': inactive,
    '--z-radio-text': mergedTextColor.value,
    '--z-radio-desc': mergedDescColor.value,
    '--z-radio-gap': mergedGap.value,
    '--z-radio-padding': mergedPadding.value,
    '--z-radio-icon-size': mergedIconSize.value,
    '--z-radio-icon-border': mergedIconBorderWidth.value,
    '--z-radio-dot-size': mergedDotSize.value,
    '--z-radio-check-size': mergedCheckSize.value,
    '--z-radio-bg': mergedBackground.value,
    '--z-radio-border': mergedBorderColor.value,
    '--z-radio-bg-active': mergedActiveBackground.value,
    '--z-radio-border-active': mergedActiveBorderColor.value,
    '--z-radio-radius': mergedRadius.value
  }

  // dot 选中态外发光
  const shadow = mergedActiveShadow.value ? mergedActiveShadow.value : `0 0 0 6rpx ${toRgba(active, 0.14)}`
  style['--z-radio-active-shadow'] = shadow

  return style
})

const iconStyle = computed(() => {
  const active = mergedColor.value
  const inactive = mergedInactiveColor.value

  // check：只显示对号，不需要外圈/阴影/底色
  if (mergedIndicator.value === 'check') {
    const ckActive = mergedCheckColor.value ? mergedCheckColor.value : active
    const ckInactive = mergedCheckInactiveColor.value ? mergedCheckInactiveColor.value : inactive
    const color = isChecked.value ? ckActive : ckInactive
    return { borderColor: 'transparent', color, boxShadow: 'none', background: 'transparent' }
  }

  const borderColor = isChecked.value ? active : inactive
  const boxShadow = isChecked.value ? 'var(--z-radio-active-shadow)' : 'none'
  return { borderColor, color: active, boxShadow }
})

function onTap() {
  if (mergedDisabled.value) return
  if (group && typeof group.setValue === 'function') group.setValue(props.value)
}

</script>

<style scoped>
.z-radio{
  display:flex;
  align-items:center;
  gap: var(--z-radio-gap);
  padding: var(--z-radio-padding);
  color: var(--z-radio-text);
}
.z-radio.is-disabled{ opacity:.6; }

.z-radio.is-block{
  padding: 16rpx 16rpx;
  border: 1rpx solid var(--z-radio-border);
  border-radius: var(--z-radio-radius);
  background: var(--z-radio-bg);
}
.z-radio.is-block.is-checked{
  border-color: var(--z-radio-border-active);
  background: var(--z-radio-bg-active);
}

.z-radio__icon{
  position: relative;
  width: var(--z-radio-icon-size);
  height: var(--z-radio-icon-size);
  box-sizing: border-box;
  flex-shrink: 0;
  border-width: var(--z-radio-icon-border);
  border-style: solid;
  display:flex;
  align-items:center;
  justify-content:center;
  background: transparent;
}
.z-radio__icon.is-circle{ border-radius: 50%; }
.z-radio__icon.is-square{ border-radius: 8rpx; }
.z-radio__icon.is-check{ border-width: 0; box-shadow: none !important; background: transparent !important; }

.z-radio__dot{
  position: absolute;
  width: var(--z-radio-dot-size);
  height: var(--z-radio-dot-size);
  border-radius: 50%;
  background: currentColor;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.z-radio__check{
  width: var(--z-radio-check-size);
  height: calc(var(--z-radio-check-size) * 0.55);
  border-left: 3rpx solid currentColor;
  border-bottom: 3rpx solid currentColor;
  transform: rotate(-45deg);
  margin-top: -2rpx;
}

.z-radio__body{ flex:1; min-width: 0; }
.z-radio__label{ font-size: 28rpx; line-height: 1.2; }
.z-radio__desc{ margin-top: 6rpx; font-size: 24rpx; color: var(--z-radio-desc); }

.z-radio__extra{ margin-left: 8rpx; }

/* sizes（仅微调字体与 icon） */
.z-radio.is-sm{ --z-radio-icon-size: 28rpx; --z-radio-dot-size: 12rpx; --z-radio-check-size: 12rpx; }
.z-radio.is-sm .z-radio__label{ font-size: 26rpx; }
.z-radio.is-sm .z-radio__check{ border-left-width: 2rpx; border-bottom-width: 2rpx; }

.z-radio.is-lg{ --z-radio-icon-size: 36rpx; --z-radio-dot-size: 16rpx; --z-radio-check-size: 16rpx; }
.z-radio.is-lg .z-radio__label{ font-size: 30rpx; }

</style>
