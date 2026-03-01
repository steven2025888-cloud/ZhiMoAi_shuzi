<template>
  <view v-if="show" class="znk-root" :style="rootStyle">
    <!-- overlay -->
    <view
      v-if="overlay"
      class="znk-overlay"
      :class="{ 'is-in': show }"
      @tap="onOverlayTap"
    />

    <!-- sheet -->
    <view
      class="znk-sheet"
      :class="['theme-' + theme, { 'is-in': show }]"
      :style="sheetStyle"
      @touchmove.stop.prevent="noop"
    >
      <!-- header -->
      <view v-if="hasHeader" class="znk-header">
        <slot name="header">
          <view class="znk-header__bar">
            <text class="znk-title" v-if="title">{{ title }}</text>
            <view class="znk-spacer" />
            <view v-if="closeable" class="znk-close" @tap="close">
              <!-- 使用纯文本 X 确保始终显示 -->
              <text class="znk-close__icon">✕</text>
            </view>
          </view>

          <view v-if="display !== 'none'" class="znk-preview">
            <text class="znk-preview__label">当前</text>
            <text class="znk-preview__value">{{ previewText }}</text>
            <view class="znk-preview__right" />
            <text v-if="maxLength > 0" class="znk-preview__hint">{{ innerValue.length }}/{{ maxLength }}</text>
          </view>
        </slot>
      </view>

      <!-- keys -->
      <view class="znk-keys">
        <view class="znk-grid">
          <view
            v-for="(k, i) in keys"
            :key="i"
            class="znk-key"
            :class="keyClass(k)"
            :style="keyStyle(k)"
            @tap="onKeyTap(k)"
          >
            <template v-if="k === '__del__'">
              <z-icon name="mdi:backspace-outline" :size="44" :color="theme === 'dark' ? '#D1D1D1' : '#333'" />
            </template>
            <template v-else>
              <text class="znk-key__txt" :style="{ fontSize: keyFontSize + 'rpx' }">{{ k }}</text>
            </template>
          </view>
        </view>

        <!-- actions -->
        <view class="znk-actions">
          <view
            class="znk-confirm"
            :class="{ 'is-disabled': disabled }"
            :style="confirmStyle"
            @tap="onConfirm"
          >
            <text class="znk-confirm__txt" :style="{ fontSize: confirmFontSize + 'rpx' }">{{ confirmText }}</text>
          </view>

          <view v-if="tips" class="znk-tips">
            <text class="znk-tips__txt">{{ tips }}</text>
          </view>
        </view>
      </view>

      <!-- footer slot -->
      <slot name="footer" />

      <!-- safe area -->
      <view v-if="safeArea" class="znk-safe" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type Theme = 'light' | 'dark'

type DisplayMode = 'none' | 'value' | 'mask'

const props = defineProps({
  show: { type: Boolean, default: false },
  modelValue: { type: String, default: '' },

  title: { type: String, default: '' },
  display: { type: String as () => DisplayMode, default: 'value' },
  maskChar: { type: String, default: '•' },

  overlay: { type: Boolean, default: true },
  closeOnClickOverlay: { type: Boolean, default: true },
  closeable: { type: Boolean, default: true },

  theme: { type: String as () => Theme, default: 'light' },
  zIndex: { type: [Number, String], default: 1000 },
  safeArea: { type: Boolean, default: true },

  decimal: { type: Boolean, default: false },
  extraKey: { type: String, default: '' }, // 例如：取消/清空/X

  maxLength: { type: Number, default: 0 }, // 0=不限

  primaryColor: { type: String, default: '#465CFF' },
  confirmText: { type: String, default: '确定' },
  confirmTextColor: { type: String, default: '#FFFFFF' },
  confirmFontSize: { type: Number, default: 30 },
  disabled: { type: Boolean, default: false },

  keyHeight: { type: Number, default: 92 },
  keyFontSize: { type: Number, default: 40 },
  keyRadius: { type: Number, default: 16 },

  tips: { type: String, default: '' },
  vibration: { type: Boolean, default: false }
})

const emit = defineEmits([
  'update:show',
  'update:modelValue',
  'input',
  'delete',
  'extra',
  'confirm'
])

const innerValue = ref(props.modelValue)

watch(
  () => props.modelValue,
  (v) => {
    if (v !== innerValue.value) innerValue.value = v
  }
)

function noop() {}

function close() {
  emit('update:show', false)
}

function onOverlayTap() {
  if (!props.closeOnClickOverlay) return
  close()
}

function vibrate() {
  if (!props.vibration) return
  // #ifdef APP || MP || H5
  try {
    uni.vibrateShort({})
  } catch (e) {}
  // #endif
}

const hasHeader = computed(() => !!props.title || props.display !== 'none' || !!(slots.header))

// Vue3 <script setup> slots 需要这样拿
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const slots = defineSlots<{ header?: any; footer?: any }>()

const keys = computed(() => {
  const base = ['1','2','3','4','5','6','7','8','9']
  const left = props.extraKey ? props.extraKey : (props.decimal ? '.' : '')
  return [...base, left, '0', '__del__']
})

const rootStyle = computed(() => ({
  zIndex: Number(props.zIndex)
}))

const sheetStyle = computed(() => ({
  zIndex: Number(props.zIndex) + 1
}))

const confirmStyle = computed(() => ({
  background: props.disabled ? (props.theme === 'dark' ? '#2B2B2B' : '#E7E7E7') : props.primaryColor,
  opacity: props.disabled ? 0.7 : 1
}))

const previewText = computed(() => {
  const v = innerValue.value || ''
  if (props.display === 'none') return ''
  if (props.display === 'mask') return props.maskChar.repeat(v.length)
  return v
})

function canAppend(nextChar: string) {
  if (props.maxLength > 0 && innerValue.value.length >= props.maxLength) return false
  if (nextChar === '.' && (innerValue.value.includes('.') || !props.decimal)) return false
  return true
}

function onKeyTap(k: string) {
  if (!props.show) return
  if (!k) return

  if (k === '__del__') {
    vibrate()
    const val = innerValue.value
    if (!val) return
    const next = val.slice(0, -1)
    innerValue.value = next
    emit('update:modelValue', next)
    emit('delete', { value: next })
    return
  }

  // extraKey：如果不是小数点，则认为是“备用键”
  if (props.extraKey && k === props.extraKey && k !== '.') {
    vibrate()
    emit('extra', { key: k, value: innerValue.value })
    return
  }

  // 小数点首位输入：自动补 0.
  let nextChar = k
  if (nextChar === '.' && !innerValue.value) {
    nextChar = '0.'
  }

  if (!canAppend(nextChar === '0.' ? '.' : nextChar)) {
    vibrate()
    return
  }

  vibrate()
  const next = innerValue.value + nextChar
  innerValue.value = next
  emit('update:modelValue', next)
  emit('input', { key: k, value: next })
}

function onConfirm() {
  if (!props.show || props.disabled) return
  vibrate()
  emit('confirm', { value: innerValue.value })
}

function keyClass(k: string) {
  return {
    'is-empty': !k,
    'is-extra': props.extraKey && k === props.extraKey && k !== '.',
    'is-del': k === '__del__'
  }
}

function keyStyle(k: string) {
  const base: Record<string, string> = {
    height: props.keyHeight + 'rpx',
    borderRadius: props.keyRadius + 'rpx'
  }
  if (!k) return { ...base, opacity: '0.45' }
  return base
}
</script>

<style scoped>
.znk-root {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
}

.znk-overlay {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,.45);
  opacity: 0;
  transition: opacity .25s ease;
}

.znk-overlay.is-in {
  opacity: 1;
}

.znk-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translate3d(0, 100%, 0);
  transition: transform .3s cubic-bezier(0.4, 0, 0.2, 1);
  border-top-left-radius: 28rpx;
  border-top-right-radius: 28rpx;
  overflow: hidden;
  box-shadow: 0 -4rpx 24rpx rgba(0, 0, 0, 0.12);
}

.znk-sheet.is-in {
  transform: translate3d(0, 0, 0);
}

.znk-sheet.theme-light {
  background: linear-gradient(180deg, #FAFAFA 0%, #F7F7F8 100%);
}

.znk-sheet.theme-dark {
  background: linear-gradient(180deg, #1A1A1A 0%, #141414 100%);
}

.znk-header {
  padding: 24rpx 24rpx 12rpx;
  background: transparent;
}

.znk-header__bar {
  display: flex;
  align-items: center;
}

.znk-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #111;
  letter-spacing: 0.5rpx;
}

.theme-dark .znk-title {
  color: #EDEDED;
}

.znk-spacer { flex: 1; }

.znk-close {
  width: 64rpx;
  height: 64rpx;
  border-radius: 999rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,.06);
  transition: all 0.25s ease;
  cursor: pointer;
}

.znk-close:active {
  transform: scale(0.9);
  background: rgba(0,0,0,.12);
}

.znk-close__icon {
  font-size: 36rpx;
  font-weight: 700;
  line-height: 1;
  color: #333;
}

.theme-dark .znk-close {
  background: rgba(255,255,255,.08);
}

.theme-dark .znk-close:active {
  background: rgba(255,255,255,.15);
}

.theme-dark .znk-close__icon {
  color: #D1D1D1;
}

.znk-preview {
  margin-top: 16rpx;
  padding: 16rpx 20rpx;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  background: rgba(0,0,0,.04);
  border: 2rpx solid rgba(0,0,0,.06);
  transition: all 0.25s ease;
}

.theme-dark .znk-preview {
  background: rgba(255,255,255,.06);
  border-color: rgba(255,255,255,.08);
}

.znk-preview__label {
  font-size: 22rpx;
  color: rgba(0,0,0,.55);
}

.theme-dark .znk-preview__label {
  color: rgba(255,255,255,.55);
}

.znk-preview__value {
  margin-left: 12rpx;
  font-size: 26rpx;
  font-weight: 700;
  color: #111;
  max-width: 520rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.theme-dark .znk-preview__value {
  color: #F3F3F3;
}

.znk-preview__right { flex: 1; }

.znk-preview__hint {
  font-size: 22rpx;
  color: rgba(0,0,0,.4);
}

.theme-dark .znk-preview__hint {
  color: rgba(255,255,255,.45);
}

.znk-keys {
  padding: 12rpx 24rpx 18rpx;
}

.znk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14rpx;
}

.znk-key {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #FFFFFF;
  color: #111;
  user-select: none;
  transition: all 0.2s ease;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
}

.theme-dark .znk-key {
  background: #1F1F1F;
  color: #EEE;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.3);
}

.znk-key.is-empty {
  background: rgba(0,0,0,.03);
  box-shadow: none;
}

.theme-dark .znk-key.is-empty {
  background: rgba(255,255,255,.06);
  box-shadow: none;
}

.znk-key.is-extra {
  background: linear-gradient(135deg, rgba(70,92,255,.15) 0%, rgba(70,92,255,.08) 100%);
  color: #2437FF;
  font-weight: 800;
  box-shadow: 0 2rpx 12rpx rgba(70, 92, 255, 0.2);
}

.theme-dark .znk-key.is-extra {
  background: linear-gradient(135deg, rgba(70,92,255,.25) 0%, rgba(70,92,255,.15) 100%);
  color: #AAB4FF;
}

.znk-key.is-del {
  background: rgba(0,0,0,.06);
}

.theme-dark .znk-key.is-del {
  background: rgba(255,255,255,.08);
}

.znk-key:active {
  opacity: .7;
  transform: scale(0.95);
}

.znk-key__txt {
  font-weight: 700;
  line-height: 1;
}

.znk-key__del {
  font-weight: 700;
  line-height: 1;
  font-size: 40rpx;
}

.znk-actions {
  margin-top: 16rpx;
}

.znk-confirm {
  height: 96rpx;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s ease;
  box-shadow: 0 4rpx 16rpx rgba(70, 92, 255, 0.3);
}

.znk-confirm:active {
  transform: scale(0.98);
  box-shadow: 0 2rpx 8rpx rgba(70, 92, 255, 0.2);
}

.znk-confirm__txt {
  font-weight: 800;
  font-size: 32rpx;
  color: var(--znk-confirm-color, #FFFFFF);
  letter-spacing: 1rpx;
}

.znk-confirm.is-disabled {
  pointer-events: none;
  opacity: 0.6;
  box-shadow: none;
}

.znk-tips {
  margin-top: 10rpx;
  padding: 0 6rpx;
}

.znk-tips__txt {
  font-size: 22rpx;
  color: rgba(0,0,0,.55);
}

.theme-dark .znk-tips__txt {
  color: rgba(255,255,255,.55);
}

.znk-safe {
  height: env(safe-area-inset-bottom);
}
</style>
