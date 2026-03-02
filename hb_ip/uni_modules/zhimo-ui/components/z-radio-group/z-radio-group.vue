<template>
  <view class="z-radio-group" :class="[directionClass]">
    <slot />
    <view v-if="options && options.length" class="z-radio-group__options" :class="[directionClass]">
      <ZRadio
        v-for="(opt, i) in options"
        :key="i"
        :value="opt[valueKey]"
        :label="opt[labelKey]"
        :desc="opt[descKey]"
        :disabled="!!opt[disabledKey]"
        :block="block"
      >
        <template v-if="opt[iconKey]" #extra>
          <image class="z-radio-group__icon" :src="opt[iconKey]" mode="aspectFit" />
        </template>
      </ZRadio>
    </view>
  </view>
</template>

<script setup>
import { computed, provide, toRef } from 'vue'
import ZRadio from '../z-radio/z-radio.vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: undefined },

  /** 是否禁用整个组 */
  disabled: { type: Boolean, default: false },

  /** 选中颜色 */
  color: { type: String, default: '#2b7cff' },
  /** 未选中颜色（边框/对号可用） */
  inactiveColor: { type: String, default: 'rgba(0,0,0,.25)' },

  /** circle | square */
  shape: { type: String, default: 'circle' },
  /** sm | md | lg */
  size: { type: String, default: 'md' },

  /** 指示器样式：dot | check */
  indicator: { type: String, default: 'dot' },
  /** 指示器位置：left | right */
  indicatorPosition: { type: String, default: 'left' },

  /** 文本/描述颜色 */
  textColor: { type: String, default: 'rgba(0,0,0,.88)' },
  descColor: { type: String, default: 'rgba(0,0,0,.55)' },

  /** 图标尺寸与线宽 */
  iconSize: { type: String, default: '32rpx' },
  iconBorderWidth: { type: String, default: '2rpx' },
  dotSize: { type: String, default: '14rpx' },
  checkSize: { type: String, default: '14rpx' },

  /** item 间距与内边距 */
  gap: { type: String, default: '12rpx' },
  padding: { type: String, default: '8rpx 0' },

  /** block 背景/边框 */
  background: { type: String, default: '#fff' },
  borderColor: { type: String, default: 'rgba(0,0,0,.08)' },
  /** block 选中背景/边框 */
  activeBackground: { type: String, default: 'rgba(43,124,255,.08)' },
  activeBorderColor: { type: String, default: '' },
  /** block 圆角 */
  radius: { type: String, default: '14rpx' },

  /** dot 选中态外发光（可传 none 关闭） */
  activeShadow: { type: String, default: '' },

  /** 是否开启 dot 选中外发光（兼容演示用的 :shadow="true/false"） */
  shadow: { type: Boolean, default: true },

  /** 对号颜色（indicator=check 时可单独控制；为空则使用 color） */
  checkColor: { type: String, default: '' },
  /** 对号未选中颜色（为空则使用 inactiveColor） */
  checkInactiveColor: { type: String, default: '' },

  /** row | column */
  direction: { type: String, default: 'column' },

  /** 使用 options 渲染（可选，slot 方式也支持） */
  options: { type: Array, default: () => [] },

  /** options 映射键 */
  labelKey: { type: String, default: 'label' },
  valueKey: { type: String, default: 'value' },
  descKey: { type: String, default: 'desc' },
  iconKey: { type: String, default: 'icon' },
  disabledKey: { type: String, default: 'disabled' },

  /** options 渲染时用块级样式 */
  block: { type: Boolean, default: true },

  /** 兼容旧数据字段（不会影响 v-model） */
  checkedKey: { type: String, default: 'checked' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const modelValue = toRef(props, 'modelValue')

function setValue(v) {
  emit('update:modelValue', v)
  emit('change', v)
}

provide('zRadioGroup', { props, modelValue, setValue })

const directionClass = computed(() => props.direction === 'row' ? 'is-row' : 'is-column')
</script>

<style scoped>
.z-radio-group{ width: 100%; }
.z-radio-group.is-row,
.z-radio-group__options.is-row{
  display:flex;
  flex-wrap: wrap;
  gap: 16rpx 18rpx;
}
.z-radio-group.is-column,
.z-radio-group__options.is-column{
  display:flex;
  flex-direction: column;
  gap: 14rpx;
}
.z-radio-group__icon{
  width: 34rpx;
  height: 34rpx;
  opacity: .9;
}
</style>
