\
<template>
  <!-- z-number: 默认 DigitalNumbers（本地字体）；金额(price)自动切换“金额常用字体” -->
  <text
    class="z-number"
    :class="[presetClass, { 'is-money': isMoney, 'is-clickable': isClickable }]"
    :style="styleObj"
    @click="onClick"
    @touchstart="onPressStart"
    @touchend="onPressEnd"
    @touchcancel="onPressCancel"
  >
    {{ displayText }}
  </text>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

type Preset = 'digital' | 'system' | 'mono' | 'condensed' | 'square' | 'din' | 'lcd' | 'tech' | 'rounded' | 'slim' | 'bold' | 'retro'
type PressEffect = 'none' | 'opacity' | 'scale' | 'both'
type Format = 'text' | 'price'
type MoneyFont = 'system' | 'mono'

type Props = {
  value?: number | string
  text?: number | string

  format?: Format
  type?: Format
  price?: boolean

  size?: number | string
  color?: string
  activeColor?: string

  bold?: boolean
  fontWeight?: number | string
  weight?: number | string

  preset?: Preset
  family?: string
  tracking?: number | string

  clickable?: boolean
  highlight?: boolean

  pressEffect?: PressEffect
  pressOpacity?: number
  pressScale?: number
  pressDuration?: number

  currencySymbol?: string
  decimals?: number

  /** 金额字体：system（默认）或 mono（账单对齐风） */
  moneyFont?: MoneyFont
}

const props = withDefaults(defineProps<Props>(), {
  value: undefined,
  text: '',
  format: 'text',
  type: undefined,
  price: false,

  size: 28,
  color: '#333',
  activeColor: '',

  bold: false,
  fontWeight: '',
  weight: '',

  preset: 'digital', // ✅ 普通数字默认 DigitalNumbers
  family: '',
  tracking: 0,

  clickable: false,
  highlight: false,

  pressEffect: 'opacity',
  pressOpacity: 0.6,
  pressScale: 0.98,
  pressDuration: 90,

  currencySymbol: '¥',
  decimals: 2,

  moneyFont: 'system'
})

const emit = defineEmits<{
  (e: 'click', payload: { text: string; value: number | string | undefined; event: any }): void
}>()

// #ifdef APP-NVUE
declare const weex: any
const domModule = weex.requireModule('dom')
// @ts-ignore
import digitalFont from './DigitalNumbers.ttf'
domModule.addRule('fontFace', {
  fontFamily: 'DigitalNumbers',
  src: "url('" + digitalFont + "')"
})
// #endif

function toRpx(val: number | string): string {
  const n = typeof val === 'number' ? val : Number(val)
  return Number.isFinite(n) ? `${n}rpx` : ''
}

function formatCnyPrice(input: number | string, symbol: string, decimals: number): string {
  const raw = String(input ?? '').trim()
  const cleaned = raw.replace(/[\s,]/g, '').replace(/^¥|^￥/g, '')
  const n = Number(cleaned)
  if (!Number.isFinite(n)) return raw

  const neg = n < 0
  const abs = Math.abs(n)
  const fixed = abs.toFixed(Math.max(0, decimals))
  const parts = fixed.split('.')
  const intPart = parts[0]
  const decPart = parts.length > 1 ? parts[1] : ''
  const withComma = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const out = decPart.length > 0 ? `${withComma}.${decPart}` : withComma
  return `${neg ? '-' : ''}${symbol}${out}`
}

const pressed = ref(false)
const isClickable = computed(() => props.clickable || props.highlight)

function onPressStart() {
  if (!isClickable.value || props.pressEffect === 'none') return
  pressed.value = true
}
function onPressEnd() {
  pressed.value = false
}
function onPressCancel() {
  pressed.value = false
}

function onClick(evt: any) {
  if (!isClickable.value) return
  emit('click', { text: displayText.value, value: rawValue.value, event: evt })
}

const rawValue = computed(() => (props.value !== undefined ? props.value : props.text))

const isMoney = computed(() => {
  const mode = (props.format || props.type || 'text') as Format
  return props.price === true || mode === 'price'
})

const displayText = computed(() => {
  const v = rawValue.value
  if (isMoney.value) return formatCnyPrice(v as any, props.currencySymbol, props.decimals)
  return String(v ?? '')
})

const presetClass = computed(() => `z-number--${props.preset}`)

const resolvedWeight = computed(() => {
  const w = props.fontWeight !== '' && props.fontWeight != null
    ? props.fontWeight
    : (props.weight !== '' ? props.weight : '')
  if (w !== '' && w != null) return String(w)
  return props.bold ? '700' : '600'
})

const resolvedColor = computed(() => {
  if (pressed.value && props.activeColor && props.activeColor.length > 0) return props.activeColor
  return props.color
})

const resolvedOpacity = computed(() => {
  if (!isClickable.value || props.pressEffect === 'none') return 1
  if (!pressed.value) return 1
  return (props.pressEffect === 'opacity' || props.pressEffect === 'both') ? props.pressOpacity : 1
})

const resolvedTransform = computed(() => {
  if (!isClickable.value || props.pressEffect === 'none') return ''
  if (!pressed.value) return ''
  return (props.pressEffect === 'scale' || props.pressEffect === 'both') ? `scale(${props.pressScale})` : ''
})

const moneySystemStack =
  '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", sans-serif'

const moneyMonoStack =
  'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, "Roboto Mono", "Noto Sans Mono", "Liberation Mono", monospace'

const styleObj = computed(() => {
  const style: Record<string, string> = {
    fontSize: toRpx(props.size) || '28rpx',
    color: resolvedColor.value,
    fontWeight: resolvedWeight.value,
    letterSpacing: toRpx(props.tracking) || '0rpx',
    fontVariantNumeric: 'tabular-nums lining-nums',
    opacity: String(resolvedOpacity.value),
    transform: resolvedTransform.value,
    transition: `transform ${props.pressDuration}ms ease, opacity ${props.pressDuration}ms ease, color ${props.pressDuration}ms ease`
  }

  // ✅ family 最高优先级
  if (props.family && props.family.length > 0) {
    style.fontFamily = props.family
    return style
  }

  // ✅ 金额：自动切换“金额常用字体”
  if (isMoney.value) {
    style.fontFamily = props.moneyFont === 'mono' ? moneyMonoStack : moneySystemStack
    return style
  }

  // 非金额：保持预设（digital 默认）
  return style
})
</script>

<style scoped>
/* #ifndef APP-NVUE */
@font-face {
  font-family: DigitalNumbers;
  src: url("./digitalnumbers.ttf") format("truetype");
  font-weight: normal;
  font-style: normal;
}
/* #endif */

.z-number {
  /* ✅ 普通数字默认 DigitalNumbers */
  font-family: DigitalNumbers;
  line-height: 1.1;
  display: inline-block;
}

.is-clickable {
  cursor: pointer;
}

/* 预设：默认 digital 不需要额外设置 */
.z-number--digital {}

/* 其它预设（非金额时使用） */
.z-number--system {
  font-family: -apple-system, BlinkMacSystemFont,
    "SF Pro Display", "SF Pro Text",
    "Segoe UI", Roboto, "Helvetica Neue", Arial,
    "Noto Sans", "PingFang SC", "Hiragino Sans", "Microsoft YaHei",
    sans-serif;
}
.z-number--mono {
  font-family: ui-monospace, SFMono-Regular,
    "SF Mono", Menlo, Monaco, Consolas,
    "Roboto Mono", "Noto Sans Mono",
    "Liberation Mono", monospace;
}
.z-number--condensed {
  font-family: "Roboto Condensed", "Helvetica Neue", Arial,
    "SF Pro Display", Roboto,
    "PingFang SC", "Hiragino Sans", "Microsoft YaHei",
    sans-serif;
}
.z-number--square {
  font-family: "ZDigits-Square",
    "DIN Alternate", "DIN Condensed",
    "SF Pro Display", "Roboto Condensed", Roboto,
    "Helvetica Neue", Arial,
    "PingFang SC", "Hiragino Sans", "Microsoft YaHei",
    sans-serif;
  letter-spacing: 0.5rpx;
}

/* DIN 风格 - 经典德国工业设计字体，常用于仪表盘、汽车 */
.z-number--din {
  font-family: "DIN Alternate", "DIN Condensed", "DIN",
    "Oswald", "Bebas Neue",
    "SF Pro Display", "Roboto Condensed", Roboto,
    "Helvetica Neue", Arial,
    "PingFang SC", "Microsoft YaHei",
    sans-serif;
  letter-spacing: 1rpx;
}

/* LCD 风格 - 液晶显示屏风格，适合计时器、仪表 */
.z-number--lcd {
  font-family: DigitalNumbers,
    "DSEG7 Classic", "DSEG14 Classic",
    "LCD", "Digital-7",
    ui-monospace, monospace;
  letter-spacing: 2rpx;
}

/* Tech 风格 - 科技感字体，适合数据展示、游戏 */
.z-number--tech {
  font-family: "Orbitron", "Audiowide", "Rajdhani",
    "Share Tech Mono", "Exo 2",
    "SF Pro Display", Roboto,
    "Helvetica Neue", Arial,
    "PingFang SC", "Microsoft YaHei",
    sans-serif;
  letter-spacing: 1.5rpx;
}

/* Rounded 风格 - 圆润友好，适合社交、娱乐类 App */
.z-number--rounded {
  font-family: "Nunito", "Quicksand", "Comfortaa",
    "Varela Round", "Poppins",
    -apple-system, BlinkMacSystemFont,
    "SF Pro Rounded", "SF Pro Display",
    Roboto, "Helvetica Neue", Arial,
    "PingFang SC", "Microsoft YaHei",
    sans-serif;
  letter-spacing: 0.5rpx;
}

/* Slim 风格 - 纤细优雅，适合时尚、奢侈品类 App */
.z-number--slim {
  font-family: "Lato", "Raleway", "Montserrat",
    "Open Sans", "Source Sans Pro",
    -apple-system, BlinkMacSystemFont,
    "SF Pro Text", Roboto,
    "Helvetica Neue", Arial,
    "PingFang SC", "Microsoft YaHei",
    sans-serif;
  font-weight: 300;
  letter-spacing: 2rpx;
}

/* Bold 风格 - 粗壮有力，适合运动、健身类 App */
.z-number--bold {
  font-family: "Impact", "Anton", "Oswald",
    "Bebas Neue", "Black Ops One",
    -apple-system, BlinkMacSystemFont,
    "SF Pro Display", Roboto,
    "Helvetica Neue", Arial,
    "PingFang SC", "Microsoft YaHei",
    sans-serif;
  font-weight: 900;
  letter-spacing: 1rpx;
}

/* Retro 风格 - 复古像素风，适合游戏、怀旧类 App */
.z-number--retro {
  font-family: "Press Start 2P", "VT323", "Silkscreen",
    "Pixel", "DOS",
    ui-monospace, monospace;
  letter-spacing: 1rpx;
}
</style>
