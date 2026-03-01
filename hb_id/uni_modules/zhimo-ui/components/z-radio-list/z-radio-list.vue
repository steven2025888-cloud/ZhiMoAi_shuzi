<template>
  <view class="z-radio-list">
    <view
      v-for="(opt, idx) in normOptions"
      :key="opt.value ?? idx"
      class="z-radio-list__item"
      :class="{ 'is-disabled': disabled || opt.disabled, 'is-checked': modelValue === opt.value }"
      @tap="onPick(opt)"
    >
      <view class="z-radio-list__left">
        <text class="z-radio-list__label">{{ opt.label }}</text>
        <text v-if="opt.desc" class="z-radio-list__desc">{{ opt.desc }}</text>
      </view>

      <view class="z-radio-list__right">
        <view class="z-radio-list__check" :style="checkStyle(opt)">
          <text class="z-radio-list__checkmark">✓</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  options: { type: Array, default: () => [] },
  color: { type: String, default: '#2b7cff' },
  disabled: { type: Boolean, default: false },
  radius: { type: Number, default: 16 },
  itemPadding: { type: Array, default: () => [18, 18] },
})

const emit = defineEmits(['update:modelValue', 'change'])

const normOptions = computed(() => props.options.map(o => {
  if (typeof o === 'string' || typeof o === 'number') return { label: String(o), value: o }
  return { label: o?.label ?? String(o?.value ?? ''), value: o?.value, desc: o?.desc ?? '', disabled: !!o?.disabled }
}))

function onPick(opt) {
  if (props.disabled || opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
}

function checkStyle(opt) {
  const checked = props.modelValue === opt.value
  if (!checked) return { opacity: 0 }
  return {
    background: props.color,
    borderColor: props.color,
    boxShadow: `0 0 0 6rpx rgba(0,0,0,.06)`
  }
}
</script>

<style scoped>
.z-radio-list{
  width: 100%;
}
.z-radio-list__item{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 18rpx 18rpx;
  border-radius: 16rpx;
  background: #fff;
  border: 1px solid rgba(0,0,0,.06);
  box-sizing: border-box;
  margin-bottom: 12rpx;
}
.z-radio-list__item:active{ opacity: .85; }
.z-radio-list__item.is-disabled{ opacity: .55; }
.z-radio-list__left{ display:flex; flex-direction:column; }
.z-radio-list__label{ font-size: 26rpx; color:#111; }
.z-radio-list__desc{ margin-top: 6rpx; font-size: 22rpx; opacity:.6; }
.z-radio-list__right{ margin-left: 18rpx; flex-shrink:0; }
.z-radio-list__check{
  width: 34rpx;
  height: 34rpx;
  border-radius: 999rpx;
  border: 1px solid rgba(0,0,0,.18);
  display:flex;
  align-items:center;
  justify-content:center;
  box-sizing:border-box;
  opacity: 0;
}
.z-radio-list__checkmark{
  font-size: 20rpx;
  color: #fff;
  line-height: 1;
}
</style>
