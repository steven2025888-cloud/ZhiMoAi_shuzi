<template>
  <view
    class="z-switch"
    :class="[{ 'is-disabled': disabled }, `is-${type}`]"
    :style="wrapStyle"
    @tap="onWrapTap"
  >
    <!-- switch 模式：自绘轨道 + 隐藏原生 switch（用于表单/平台一致性） -->
    <!-- #ifdef APP-NVUE -->
    <view class="z-switch__native-wrap" @tap.stop>
      <switch
        v-if="type === 'switch'"
        class="z-switch__native"
        :checked="inner"
        :disabled="disabled"
        :color="activeColorResolved"
        :name="name"
        @change="onNativeChange"
      />
    </view>
    <!-- #endif -->

    <!-- #ifndef APP-NVUE -->
    <view v-if="type === 'switch'" class="z-switch__track" @tap.stop :style="trackStyle">
      <view class="z-switch__track-bg" :style="trackBgStyle" />
      <view class="z-switch__knob" :class="{ 'is-on': inner }" :style="knobStyle">
        <slot />
      </view>

      <!-- 隐藏原生开关：保证各端 change 行为一致 -->
      <switch
        class="z-switch__hidden"
        :class="{ 'pe-none': inLabel }"
        :checked="inner"
        :disabled="disabled"
        :color="activeColorResolved"
        :name="name"
        @change="onNativeChange"
      />
    </view>
    <!-- #endif -->

    <!-- checkbox 模式：圆形/方形勾选 -->
    <view
      v-else
      class="z-check" @tap.stop
      :class="{ 'is-on': inner }"
      :style="checkStyle"
    >
      <view v-if="inner" class="z-check__mark" :style="markStyle" />
      <switch
        class="z-switch__hidden"
        :class="{ 'pe-none': inLabel }"
        type="checkbox"
        :checked="inner"
        :disabled="disabled"
        :name="name"
        @change="onNativeChange"
      />
    </view>

    <text v-if="label" class="z-switch__label">{{ label }}</text>
  </view>
</template>

<script setup>
import { computed, inject, ref, watch } from 'vue'

/**
 * z-switch
 * - type: 'switch' | 'checkbox'
 * - 支持 slot（放在滑块里：文字/图标都可以）
 * - 支持 tapToggle：点击整个容器切换
 * - 支持 scale：缩放显示尺寸
 */
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  name: { type: String, default: '' },

  type: { type: String, default: 'switch' }, // 'switch' | 'checkbox'
  disabled: { type: Boolean, default: false },

  // switch 颜色
  activeColor: { type: String, default: '#2b7cff' }, // 选中轨道色
  inactiveColor: { type: String, default: '#e5e7eb' }, // 未选中轨道色
  trackBg: { type: String, default: '#ffffff' }, // 轨道底层（用于做更柔和的层次）

  // 滑块/按钮
  knobColor: { type: String, default: '' }, // 选中时滑块背景（可选）
  knobBg: { type: String, default: '#ffffff' }, // 未选中滑块背景

  // checkbox 颜色
  borderColor: { type: String, default: '#cbd5e1' },
  checkColor: { type: String, default: '#ffffff' },
  checkBg: { type: String, default: '#ffffff' },

  // 文案
  label: { type: String, default: '' },

  // 交互
  tapToggle: { type: Boolean, default: false },

  // 尺寸
  scale: { type: [Number, String], default: 1 }
})

const emit = defineEmits(['update:modelValue', 'change'])

const inner = ref(!!props.modelValue)
watch(() => props.modelValue, v => { inner.value = !!v })

/** 可选：与 z-label 之类的父组件联动（有则禁用 pointer-events 防止双触发） */
const labelCtx = inject('zLabel', null)
const inLabel = computed(() => !!labelCtx)

function setValue(v, rawEvent = null) {
  inner.value = !!v
  emit('update:modelValue', inner.value)
  emit('change', { value: inner.value, event: rawEvent })
}

function onNativeChange(e) {
  if (props.disabled) return
  const v = !!(e?.detail?.value)
  setValue(v, e)
}

function onWrapTap() {
  if (!props.tapToggle || props.disabled) return
  setValue(!inner.value, null)
}

// 兼容 nvue 缩放
let isNvue = false
// #ifdef APP-NVUE
isNvue = true
// #endif

const scaleNum = computed(() => {
  const n = Number(props.scale)
  return Number.isFinite(n) && n > 0 ? n : 1
})

const wrapStyle = computed(() => {
  const s = scaleNum.value
  // 非 nvue 用 zoom 更省心；nvue 用 transform
  return {
    zoom: isNvue ? 1 : s,
    transform: `scale(${isNvue ? s : 1})`,
    transformOrigin: 'left center'
  }
})

const activeColorResolved = computed(() => props.activeColor || '#2b7cff')

const trackStyle = computed(() => ({
  background: inner.value ? activeColorResolved.value : props.inactiveColor,
  borderColor: inner.value ? activeColorResolved.value : props.borderColor
}))

const trackBgStyle = computed(() => ({
  background: props.trackBg,
  opacity: inner.value ? 0.14 : 0.10
}))

const knobStyle = computed(() => ({
  background: inner.value
    ? (props.knobColor || props.knobBg)
    : props.knobBg
}))

const checkStyle = computed(() => ({
  background: inner.value ? activeColorResolved.value : props.checkBg,
  borderColor: inner.value ? activeColorResolved.value : props.borderColor
}))

const markStyle = computed(() => ({
  borderBottomColor: props.checkColor,
  borderRightColor: props.checkColor
}))
</script>

<style scoped>
.z-switch{
  display:flex;
  align-items:center;
  gap:16rpx;
}
.z-switch.is-disabled{ opacity:.6; }

.z-switch__label{
  font-size:28rpx;
  color:#111827;
}

/* switch（非 nvue 自绘） */
.z-switch__track{
  position:relative;
  width: 96rpx;
  height: 56rpx;
  border-radius: 999rpx;
  border-width: 2rpx;
  border-style: solid;
  overflow:hidden;
  box-sizing:border-box;
}
.z-switch__track-bg{
  position:absolute;
  inset:0;
}
.z-switch__knob{
  position:absolute;
  top: 50%;
  left: 6rpx;
  width: 44rpx;
  height: 44rpx;
  border-radius: 999rpx;
  display:flex;
  align-items:center;
  justify-content:center;
  box-shadow: 0 6rpx 16rpx rgba(0,0,0,.18);
  transform: translate3d(0, -50%, 0);
  transition: transform .22s ease;
}
.z-switch__knob.is-on{
  transform: translate3d(40rpx, -50%, 0);
}
.z-switch__native{
  transform: scale(1);
}

/* checkbox */
.z-check{
  position:relative;
  width: 44rpx;
  height: 44rpx;
  border-radius: 12rpx;
  border-width: 2rpx;
  border-style: solid;
  box-sizing:border-box;
  overflow:hidden;
}
.z-check__mark{
  position:absolute;
  left: 14rpx;
  top: 6rpx;
  width: 14rpx;
  height: 24rpx;
  border-bottom-style: solid;
  border-bottom-width: 4rpx;
  border-right-style: solid;
  border-right-width: 4rpx;
  transform: rotate(45deg);
  transform-origin: 50% 50%;
}

/* 隐藏原生 */
.z-switch__hidden{
  position:absolute;
  inset:-2rpx;
  opacity:0;
  width:100%;
  height:100%;
  border:0;
}
.pe-none{ pointer-events:none; }
</style>