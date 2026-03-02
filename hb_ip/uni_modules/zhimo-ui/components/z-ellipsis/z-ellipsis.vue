<template>
  <view class="ze" :class="{ 'ze--card': card, 'ze--dense': dense }" :style="wrapStyle">
    <!-- content -->
    <view class="ze__content" :style="contentWrapStyle">
      <!-- text mode: clamp -->
      <text
        v-if="hasText"
        class="ze__text"
        :class="{
          'ze__text--clamp': isClampCollapsed,
          'ze__text--expanded': isExpanded,
          'ze__text--inline-toggle': showToggle && togglePosition === 'inline'
        }"
        :style="[textStyle, clampVarStyle, textPaddingStyle]"
        selectable="false"
        space="ensp"
      >{{ text }}</text>

      <!-- slot content (when no text provided) -->
      <view v-else class="ze__slot" :style="slotStyle">
        <slot />
      </view>

      <!-- fade mask when collapsed -->
      <view
        v-if="isFadeCollapsed"
        class="ze__fade"
        :style="fadeStyle"
        @tap.stop="onToggleTap"
      />
    </view>

    <!-- toggle -->
    <view
      v-if="showToggle"
      class="ze__toggle"
      :class="{
        'ze__toggle--inline': togglePosition === 'inline',
        'ze__toggle--bottom': togglePosition === 'bottom'
      }"
    >
      <view
        class="ze__toggleBtn"
        :class="{ 'ze__toggleBtn--expanded': isExpanded }"
        :style="[toggleBtnStyle, toggleStyle]"
        @tap.stop="onToggleTap"
      >
        <z-icon
          v-if="showIcon"
          :name="currentIconName"
          :size="iconSize"
          :color="props.toggleColor"
          class="ze__toggleIcon"
        />
        <text class="ze__toggleTxt" :style="{ color: props.toggleColor }">{{ toggleLabel }}</text>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const emit = defineEmits(['update:expanded', 'change'])

const props = defineProps({
  /** 文本内容（推荐用 text；也支持 slot） */
  text: { type: String, default: '' },

  /** 省略行数（1=单行省略；>1=多行省略） */
  lines: { type: Number, default: 2 },

  /** 展示模式：clamp=行数省略；fade=固定高度+渐隐 */
  mode: { type: String, default: 'clamp' }, // 'clamp' | 'fade'

  /** 是否允许展开/收起（lines=1 时会自动关闭展开） */
  expandable: { type: Boolean, default: true },

  /** v-model:expanded（传了就是受控） */
  expanded: { type: Boolean, default: undefined },

  /** 初始展开（仅在非受控时生效） */
  defaultExpanded: { type: Boolean, default: false },

  /** 渐隐模式下折叠高度（rpx/px/% 都可） */
  collapsedHeight: { type: [Number, String], default: 180 },

  /** 展开按钮位置：inline=右下角；bottom=底部 */
  togglePosition: { type: String, default: 'inline' }, // 'inline' | 'bottom'

  /** "更多/收起"文本 */
  moreText: { type: String, default: '更多' },
  lessText: { type: String, default: '收起' },

  /** toggle 按钮样式 */
  toggleColor: { type: String, default: '#007AFF' },
  toggleBackground: { type: String, default: '' }, // 默认无背景
  toggleBorder: { type: String, default: '' }, // 默认无边框
  toggleBorderRadius: { type: [Number, String], default: 999 }, // 圆角
  togglePadding: { type: String, default: '12rpx 20rpx' }, // 内边距
  toggleStyle: { type: Object, default: () => ({}) }, // 自定义样式对象

  /** toggle 图标 */
  showIcon: { type: Boolean, default: false }, // 是否显示图标
  iconName: { type: String, default: '' }, // 自定义图标名称
  moreIcon: { type: String, default: 'mdi:chevron-down' }, // 更多图标
  lessIcon: { type: String, default: 'mdi:chevron-up' }, // 收起图标
  iconSize: { type: [Number, String], default: 20 }, // 图标大小

  /** iOS 卡片风格 */
  card: { type: Boolean, default: true },
  dense: { type: Boolean, default: false },

  /** 字体与颜色 */
  fontSize: { type: [Number, String], default: 28 },
  lineHeight: { type: [Number, String], default: 40 },
  color: { type: String, default: '#111827' },
  align: { type: String, default: 'left' }, // left|center|right
  weight: { type: [Number, String], default: 400 },

  /** 内边距（card=true 时生效更明显） */
  padding: { type: [Number, String], default: 24 },

  /** 可覆盖容器样式 */
  background: { type: String, default: '#FFFFFF' },
  radius: { type: [Number, String], default: 24 },
  borderColor: { type: String, default: 'rgba(15, 23, 42, 0.08)' },
  shadow: { type: Boolean, default: true }
})

const hasText = computed(() => !!(props.text && props.text.trim().length))
const isControlled = computed(() => typeof props.expanded === 'boolean')

const innerExpanded = ref(!!props.defaultExpanded)
watch(
  () => props.expanded,
  (v) => {
    if (typeof v === 'boolean') innerExpanded.value = v
  }
)

function setExpanded(next) {
  if (!isControlled.value) innerExpanded.value = next
  emit('update:expanded', next)
  emit('change', { expanded: next })
}

const canToggle = computed(() => props.expandable && props.lines > 1)
/**
 * 规则：
 * - lines=1：永远不显示更多/收起（单行只做省略号）
 * - expandable=false：永远不显示更多/收起，只做省略号
 */
const effectiveExpanded = computed(() => {
  if (!canToggle.value) return false
  return isControlled.value ? props.expanded : innerExpanded.value
})

const isExpanded = computed(() => !!effectiveExpanded.value)

const showToggle = computed(() => canToggle.value)
const toggleLabel = computed(() => (isExpanded.value ? props.lessText : props.moreText))

// 当前图标名称
const currentIconName = computed(() => {
  if (props.iconName) return props.iconName
  return isExpanded.value ? props.lessIcon : props.moreIcon
})

function onToggleTap() {
  if (!canToggle.value) return
  setExpanded(!isExpanded.value)
}

const toUnit = (v, unit = 'rpx') => {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') return `${v}${unit}`
  const s = String(v)
  return /[a-z%]+$/i.test(s) ? s : `${s}${unit}`
}

const wrapStyle = computed(() => {
  const pad = toUnit(props.padding, 'rpx')
  const rad = toUnit(props.radius, 'rpx')
  const shadow = props.shadow ? '0 10rpx 30rpx rgba(15, 23, 42, 0.08)' : 'none'
  return {
    background: props.background,
  }
})


const clampVarStyle = computed(() => ({ '--ze-lines': String(Math.max(1, Number(props.lines) || 1)) }))
const textStyle = computed(() => ({
  fontSize: toUnit(props.fontSize, 'rpx'),
  lineHeight: toUnit(props.lineHeight, 'rpx'),
  color: props.color,
  textAlign: props.align,
  fontWeight: String(props.weight)
}))

const slotStyle = computed(() => ({
  // allow slot to inherit padding from card
}))

const isClampCollapsed = computed(() => props.mode === 'clamp' && !isExpanded.value)
const isFadeCollapsed = computed(() => props.mode === 'fade' && !isExpanded.value && canToggle.value)

const contentWrapStyle = computed(() => {
  if (props.mode !== 'fade') return {}
  if (isExpanded.value) return {}
  return { maxHeight: toUnit(props.collapsedHeight, 'rpx'), overflow: 'hidden', position: 'relative' }
})

const fadeStyle = computed(() => {
  // iOS-like bottom fade, tap to expand too
  return {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    height: toUnit(90, 'rpx'),
    background: 'linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,0.92))'
  }
})

// Add padding to text when expanded with inline toggle to prevent overlap
const textPaddingStyle = computed(() => {
  if (props.togglePosition === 'inline' && isExpanded.value && showToggle.value) {
    return {
      paddingBottom: toUnit(60, 'rpx') // Space for the inline toggle button
    }
  }
  return {}
})

// Toggle button style with dynamic color
const toggleBtnStyle = computed(() => {
  const bg = props.toggleBackground || 'transparent'
  const border = props.toggleBorder || 'none'
  const borderRadius = toUnit(props.toggleBorderRadius, 'rpx')
  const padding = props.togglePadding || '12rpx 20rpx'

  return {
    background: bg,
    border: border,
    borderRadius: borderRadius,
    padding: padding
  }
})
</script>

<style scoped lang="scss">
.ze{
  width: 100%;
  box-sizing: border-box;
  position: relative;
}
.ze--dense{
  padding: 18rpx !important;
  border-radius: 20rpx !important;
}
.ze__content{
  position: relative;
  width: 100%;
}

.ze__text{
  display: block;
  width: 100%;
  box-sizing: border-box;
  word-break: break-all;
  white-space: pre-wrap;
}

/* clamp mode (H5 / most app webview) */
.ze__text--clamp{
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* expanded just uses normal flow */
.ze__text--expanded{
  overflow: visible;
  display: block;
}

/* Add padding when expanded with inline toggle to prevent overlap */
.ze__text--expanded.ze__text--inline-toggle{
  padding-bottom: 60rpx;
}

/* fade overlay */
.ze__fade{
  z-index: 2;
}

/* toggle */
.ze__toggle{
  width: 100%;
  box-sizing: border-box;
}
.ze__toggle--inline{
  position: absolute;
  right: 18rpx;
  bottom: 18rpx;
  width: auto;
}
.ze__toggle--bottom{
  margin-top: 14rpx;
  display: flex;
  justify-content: flex-end;
}

.ze__toggleBtn{
  display: inline-flex;
  align-items: center;
  gap: 6rpx;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
}

.ze__toggleBtn:active{
  transform: scale(0.95);
  opacity: 0.8;
}

.ze__toggleBtn--expanded{
}

.ze__toggleIcon{
  line-height: 1;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.ze__toggleBtn--expanded .ze__toggleIcon{
}

.ze__toggleTxt{
  font-size: 26rpx;
  line-height: 1;
  font-weight: 600;
  letter-spacing: 0.5rpx;
}

/* IMPORTANT: apply dynamic line-clamp via CSS var approach */
</style>

<style scoped>
/* dynamic line clamp: use CSS variable fallback with inline style not supported in scoped scss well.
   We set it via :style on the element using --ze-lines, then here map it.
*/
.ze__text--clamp{
  -webkit-line-clamp: var(--ze-lines, 2);
}
</style>
