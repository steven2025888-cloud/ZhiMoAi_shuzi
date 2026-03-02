<template>
  <!-- H5: use native <a> when native=true or for tel/mailto links -->
  <!-- #ifdef H5 -->
  <a
    v-if="useNativeA"
    class="z-link"
    :class="cls"
    :href="href || 'javascript:void(0)'"
    :target="target"
    rel="noopener noreferrer"
    :download="download || undefined"
    @click="onH5AnchorClick"
    :style="rootStyle"
  >
    <slot name="left">
      <z-icon v-if="icon" :name="icon" :size="iconSize" class="z-link__icon" />
    </slot>

    <span class="z-link__text">
      <slot>{{ displayText }}</slot>
    </span>

    <slot name="right">
      <z-icon v-if="iconRight" :name="iconRight" :size="iconSize" class="z-link__icon z-link__icon--right" />
    </slot>
  </a>
  <!-- #endif -->

  <!-- #ifndef H5 -->
  <text class="z-link" :class="cls" :style="rootStyle" @tap="onTap">
    <slot name="left">
      <z-icon v-if="icon" :name="icon" :size="iconSize" class="z-link__icon" />
    </slot>

    <text class="z-link__text">
      <slot>{{ displayText }}</slot>
    </text>

    <slot name="right">
      <z-icon v-if="iconRight" :name="iconRight" :size="iconSize" class="z-link__icon z-link__icon--right" />
    </slot>
  </text>
  <!-- #endif -->

  <!-- H5 fallback when not using native anchor -->
  <!-- #ifdef H5 -->
  <span
    v-if="!useNativeA"
    class="z-link"
    :class="cls"
    :style="rootStyle"
    role="link"
    @click="onTap"
  >
    <slot name="left">
      <z-icon v-if="icon" :name="icon" :size="iconSize" class="z-link__icon" />
    </slot>

    <span class="z-link__text">
      <slot>{{ displayText }}</slot>
    </span>

    <slot name="right">
      <z-icon v-if="iconRight" :name="iconRight" :size="iconSize" class="z-link__icon z-link__icon--right" />
    </slot>
  </span>
  <!-- #endif -->
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Variant = 'text' | 'chip'

const props = defineProps({
  href: { type: String, default: '' },
  text: { type: String, default: '' },

  /** H5 原生 <a> 的 download 属性（仅 H5 生效） */
  download: { type: String, default: '' },
  /** H5 原生 <a> 的 target（仅 H5 生效） */
  target: { type: String, default: '_blank' },

  color: { type: String, default: '' },
  size: { type: [Number, String], default: 28 },

  underline: { type: Boolean, default: false },
  highlight: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },

  /** 点击后是否执行默认行为（打开/复制/拨号） */
  action: { type: Boolean, default: true },

  /** MP：是否复制到剪贴板 */
  copyOnMp: { type: Boolean, default: true },
  copyTips: { type: String, default: '链接已复制' },

  /** 强制 H5 使用原生 <a>（默认仅 tel/mailto 才使用） */
  native: { type: Boolean, default: false },

  /** 图标（可选，依赖你已有的 z-icon） */
  icon: { type: String, default: '' },
  iconRight: { type: String, default: '' },
  iconSize: { type: [Number, String], default: 30 },
  gap: { type: [Number, String], default: 8 },

  /** 外观：纯文本 / 胶囊 */
  variant: { type: String as unknown as () => Variant, default: 'text' },
  bg: { type: String, default: '' },
  borderColor: { type: String, default: '' },
  radius: { type: [Number, String], default: 999 },
  padX: { type: [Number, String], default: 18 },
  padY: { type: [Number, String], default: 10 },

  /** 字重：bold=true 会覆盖 weight */
  bold: { type: Boolean, default: false },
  weight: { type: [Number, String], default: 400 },

  /** 兜底：当 href 为空时仍可点击，仅触发事件 */
  allowEmpty: { type: Boolean, default: false }
})

const emit = defineEmits<{
  (e: 'click', payload: { href: string; text: string }): void
}>()

const displayText = computed(() => props.text || props.href || '')

const isTel = computed(() => (props.href || '').startsWith('tel:'))
const isMail = computed(() => (props.href || '').startsWith('mailto:'))

const useNativeA = computed(() => {
  // #ifdef H5
  return !!(props.native || isTel.value || isMail.value)
  // #endif
  // #ifndef H5
  return false
  // #endif
})

const cls = computed(() => ({
  'is-underline': !!props.underline,
  'is-highlight': !!props.highlight,
  'is-disabled': !!props.disabled,
  'is-chip': props.variant === 'chip',
  'has-left': !!props.icon,
  'has-right': !!props.iconRight
}))

function toRpx(v: string | number, unit = 'rpx') {
  if (v === '' || v == null) return undefined
  const s = String(v).trim()
  if (s === '0') return '0'
  if (/^\d+(\.\d+)?(rpx|px|rem|em|%)$/.test(s)) return s
  if (/^\d+(\.\d+)?$/.test(s)) return `${s}${unit}`
  return s
}

const rootStyle = computed(() => {
  const fs = toRpx(props.size, 'rpx')
  const icGap = toRpx(props.gap, 'rpx')
  const radius = toRpx(props.radius, 'rpx')
  const padX = toRpx(props.padX, 'rpx')
  const padY = toRpx(props.padY, 'rpx')

  const weight = props.bold ? 600 : props.weight
  const color = props.color || 'var(--z-color-link, #465CFF)'

  const st: Record<string, any> = {
    '--z-link-color': color,
    '--z-link-size': fs,
    '--z-link-weight': weight,
    '--z-link-gap': icGap
  }

  if (props.variant === 'chip') {
    st['--z-link-bg'] = props.bg || 'rgba(70, 92, 255, 0.10)'
    st['--z-link-bd'] = props.borderColor || 'rgba(70, 92, 255, 0.22)'
    st['--z-link-radius'] = radius
    st['--z-link-pad-x'] = padX
    st['--z-link-pad-y'] = padY
  }

  return st
})

function canDoAction() {
  if (props.disabled) return false
  if (!props.action) return false
  if (!props.href && !props.allowEmpty) return false
  return true
}

function onTap() {
  emit('click', { href: props.href, text: displayText.value })
  if (!canDoAction()) return

  // tel: 优先走系统拨号
  if (isTel.value) {
    const num = props.href.replace(/^tel:/, '')
    if (!num) return
    uni.makePhoneCall({ phoneNumber: num })
    return
  }

  // #ifdef APP-PLUS
  // APP：打开外部浏览器
  // (mailto 也会交给系统处理)
  plus.runtime.openURL(props.href)
  return
  // #endif

  // #ifdef MP
  // 小程序：无法直接打开外部网页，默认复制链接
  if (props.copyOnMp) {
    uni.setClipboardData({
      data: props.href,
      success: () => {
        uni.showToast({ title: props.copyTips, icon: 'none' })
      }
    })
  } else {
    uni.showToast({ title: props.copyTips, icon: 'none' })
  }
  return
  // #endif

  // #ifdef H5
  // 非原生 <a>：新开窗口
  try {
    window.open(props.href, props.target || '_blank')
  } catch (e) {
    // ignore
  }
  // #endif
}

function onH5AnchorClick(e: MouseEvent) {
  emit('click', { href: props.href, text: displayText.value })

  if (props.disabled || !props.action || (!props.href && !props.allowEmpty)) {
    e.preventDefault()
    return
  }

  // 若非 tel/mailto 且 target 为空，统一新开
  // (保留原生 <a> 行为：download、长按复制等)
}
</script>

<style scoped>
/* H5 鼠标态 */
.z-link {
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */

  display: inline-flex;
  align-items: center;
  vertical-align: middle;

  color: var(--z-link-color);
  font-size: var(--z-link-size);
  font-weight: var(--z-link-weight);

  line-height: 1.2;
  text-decoration: none;

  user-select: none;
}

/* 文本部分保持可选中（复制更友好） */
.z-link__text {
  user-select: text;
}

/* icon */
.z-link__icon {
  flex: 0 0 auto;
  margin-right: var(--z-link-gap);
}
.z-link__icon--right {
  margin-right: 0;
  margin-left: var(--z-link-gap);
}

/* underline */
.is-underline {
  text-decoration: underline;
}

/* active highlight */
.is-highlight:active {
  opacity: 0.55;
}

/* disabled */
.is-disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* chip */
.is-chip {
  padding: var(--z-link-pad-y) var(--z-link-pad-x);
  border-radius: var(--z-link-radius);
  background: var(--z-link-bg);
  border: 1px solid var(--z-link-bd);
  text-decoration: none;
}
</style>
