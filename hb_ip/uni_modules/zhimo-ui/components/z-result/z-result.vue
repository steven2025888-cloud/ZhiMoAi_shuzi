<template>
  <view class="z-result" :style="{ paddingTop: toRpx(paddingTop) }">
    <view class="z-result__iconBox" v-if="showIcon">
      <!-- custom icon slot has highest priority -->
      <slot name="icon">
        <view
          class="z-result__icon"
          :class="iconClass"
          :style="iconStyle"
        >
          <!-- icon name (z-icon) -->
          <z-icon
            v-if="icon"
            :name="icon"
            :size="iconInnerSize"
            :color="iconColorResolved"
          />
          <!-- built-in shapes -->
          <template v-else>
            <view :class="['z-result__shape', `z-result__shape-${typeResolved}`]" :style="shapeStyle"></view>
            <view
              v-if="typeResolved === 'error' || typeResolved === 'warning'"
              :class="['z-result__shape2', `z-result__shape2-${typeResolved}`]"
              :style="{ background: iconColorResolved }"
            ></view>
          </template>
        </view>
      </slot>
    </view>

    <text
      v-if="title"
      class="z-result__title"
      :class="{ 'z-result__title--default': !titleColor }"
      :style="{ fontSize: toRpx(titleSize), color: titleColor || '' }"
    >{{ title }}</text>

    <text
      v-if="desc"
      class="z-result__desc"
      :class="{ 'z-result__desc--default': !descColor }"
      :style="{ fontSize: toRpx(descSize), color: descColor || '' }"
    >{{ desc }}</text>

    <view class="z-result__extra">
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
defineOptions({ name: 'z-result' })
type ResultType = 'success' | 'warning' | 'error' | 'waiting' | 'custom'

const props = defineProps({
  /** 顶部间距（rpx） */
  paddingTop: { type: [Number, String], default: 72 },

  /** success / warning / error / waiting / custom */
  type: { type: String, default: 'success' },

  /** 显示图标 */
  showIcon: { type: Boolean, default: true },

  /** 使用 z-icon 的图标名（如 mdi:check） */
  icon: { type: String, default: '' },

  /** 图标前景色（线条色 / z-icon color） */
  iconColor: { type: String, default: '#ffffff' },

  /** 图标背景色（不传则随 type 取默认色） */
  iconBg: { type: String, default: '' },

  /** 图标尺寸（rpx） */
  iconSize: { type: [Number, String], default: 128 },

  /** 图标缩放（1=原始） */
  iconScale: { type: Number, default: 1 },

  /** 展示风格：solid / soft / outline */
  variant: { type: String, default: 'solid' },

  title: { type: String, default: '' },
  desc: { type: String, default: '' },

  titleSize: { type: [Number, String], default: 40 },
  descSize: { type: [Number, String], default: 28 },

  titleColor: { type: String, default: '' },
  descColor: { type: String, default: '' },

  /** 自定义类型颜色（可选，优先于默认色） */
  color: { type: String, default: '' }
})

const typeResolved = computed<ResultType>(() => {
  const t = String(props.type || '').toLowerCase()
  if (t === 'fail') return 'error'
  if (t === 'success' || t === 'warning' || t === 'error' || t === 'waiting' || t === 'custom') return t as ResultType
  return 'custom'
})

const isBuiltin = computed(() => ['success', 'warning', 'error', 'waiting'].includes(typeResolved.value))
const iconColorResolved = computed(() => props.iconColor || '#ffffff')

const typeColor = computed(() => {
  if (props.color) return props.color
  switch (typeResolved.value) {
    case 'success': return 'var(--z-color-success, #09BE4F)'
    case 'warning': return 'var(--z-color-warning, #FFB703)'
    case 'error': return 'var(--z-color-danger, #FF2B2B)'
    case 'waiting': return 'var(--z-color-primary, #465CFF)'
    default: return 'var(--z-color-primary, #465CFF)'
  }
})

const iconBgResolved = computed(() => props.iconBg || typeColor.value)

const iconClass = computed(() => {
  const v = String(props.variant || 'solid')
  return [
    isBuiltin.value ? `z-result__bg-${typeResolved.value}` : '',
    v === 'soft' ? 'z-result__icon--soft' : '',
    v === 'outline' ? 'z-result__icon--outline' : ''
  ].filter(Boolean).join(' ')
})

const iconInnerSize = computed(() => {
  const s = Number(props.iconSize || 128)
  // keep icon inside circle comfortable
  return Math.max(28, Math.round(s * 0.62))
})

const iconStyle = computed(() => {
  const s = Number(props.iconSize || 128)
  const scale = props.iconScale || 1
  const bg = iconBgResolved.value
  // soft/outline handled by CSS; set bg as CSS var for consistency
  return {
    width: `${s}rpx`,
    height: `${s}rpx`,
    '--z-result-bg': bg,
    transform: `scale(${scale})`
  } as any
})

const shapeStyle = computed(() => {
  // success/waiting uses border-color, warning/error uses background
  if (typeResolved.value === 'error' || typeResolved.value === 'warning') return { background: iconColorResolved.value }
  return { borderColor: iconColorResolved.value }
})

function toRpx(v: any) {
  if (v == null) return '0rpx'
  const s = String(v)
  return /rpx$|px$|%$/.test(s) ? s : `${s}rpx`
}
</script>

<style scoped>
.z-result{
  width: 100%;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.z-result__iconBox{ padding-bottom: 36rpx; }

.z-result__icon{
  position: relative;
  overflow: hidden;
  border-radius: 999rpx;
  display:flex;
  flex-direction: row;
  align-items:center;
  justify-content:center;
  background: var(--z-result-bg, var(--z-color-primary, #465CFF));
}

/* solid: default uses bg; soft and outline change it */
.z-result__icon--soft{
  background: color-mix(in srgb, var(--z-result-bg) 14%, #ffffff 86%);
}
.z-result__icon--outline{
  background: transparent;
  border: 2rpx solid var(--z-result-bg);
}

/* built-in type bg fallback (when user doesn't pass iconBg) */
.z-result__bg-success{ background: var(--z-result-bg, var(--z-color-success, #09BE4F)); }
.z-result__bg-warning{ background: var(--z-result-bg, var(--z-color-warning, #FFB703)); }
.z-result__bg-error{ background: var(--z-result-bg, var(--z-color-danger, #FF2B2B)); }
.z-result__bg-waiting{ background: var(--z-result-bg, var(--z-color-primary, #465CFF)); }

.z-result__title{
  font-weight: 700;
  margin-bottom: 22rpx;
  text-align: center;
  padding: 0 48rpx;
  box-sizing: border-box;
  line-height: 1.2;
}
.z-result__title--default{ color: var(--z-color-title, #181818); }

.z-result__desc{
  font-weight: 400;
  text-align: center;
  padding: 0 64rpx;
  box-sizing: border-box;
  margin-bottom: 24rpx;
  line-height: 1.5;
}
.z-result__desc--default{ color: var(--z-color-text, #333333); }

.z-result__extra{
  width: 100%;
  display:flex;
  flex-direction: column;
  align-items:center;
  padding: 0 48rpx 32rpx;
  box-sizing: border-box;
}

/* ===== built-in shapes (similar but renamed) ===== */
.z-result__shape-success{
  width: 30rpx;
  height: 60rpx;
  border-style: solid;
  border-left-width: 0;
  border-top-width: 0;
  border-right-width: 8rpx;
  border-bottom-width: 8rpx;
  box-sizing: border-box;
  transform: rotate(45deg);
  margin-bottom: 12rpx;
  margin-left: 4rpx;
  border-bottom-right-radius: 8rpx;
}

.z-result__shape-error{
  width: 60rpx;
  height: 8rpx;
  transform: rotate(45deg);
  border-radius: 2rpx;
}
.z-result__shape2-error{
  width: 8rpx;
  height: 60rpx;
  position: absolute;
  left: 50%;
  top: 50%;
  margin-left: -4rpx;
  margin-top: -30rpx;
  transform: rotate(45deg);
  border-radius: 2rpx;
}

.z-result__shape-waiting{
  height: 48rpx;
  width: 48rpx;
  border-style: solid;
  border-top-width: 0;
  border-right-width: 0;
  border-bottom-width: 8rpx;
  border-left-width: 8rpx;
  border-bottom-left-radius: 8rpx;
  box-sizing: border-box;
  margin-left: 24rpx;
  margin-top: -24rpx;
}

.z-result__shape-warning{
  height: 48rpx;
  width: 8rpx;
  margin-top: -16rpx;
  border-radius: 2rpx;
}
.z-result__shape2-warning{
  height: 8rpx;
  width: 8rpx;
  position: absolute;
  top: 68%;
  border-radius: 2rpx;
}
</style>