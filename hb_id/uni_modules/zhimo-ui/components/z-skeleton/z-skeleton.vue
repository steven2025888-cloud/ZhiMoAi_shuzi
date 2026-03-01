<template>
  <view class="z-skeleton" :style="wrapStyle">
    <!-- loading -->
    <template v-if="props.loading">
      <!-- preset variants -->
      <template v-if="props.variant !== 'custom'">
        <!-- list -->
        <view v-if="props.variant === 'list'" class="z-sk__list">
          <view v-for="i in rowsN" :key="i" class="z-sk__row" :style="{ marginBottom: toUnit(props.rowGap) }">
            <view v-if="props.avatar" class="z-sk z-sk--circle" :style="skStyle(avatarSize, avatarSize, 9999)" />
            <view class="z-sk__col" :style="{ marginLeft: props.avatar ? toUnit(props.gap) : '0' }">
              <view class="z-sk z-sk--line" :style="skStyle('62%', lineH, lineR)" />
              <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
              <view class="z-sk z-sk--line" :style="skStyle('88%', lineH, lineR, 0.85)" />
              <view v-if="props.lines >= 3" class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
              <view v-if="props.lines >= 3" class="z-sk z-sk--line" :style="skStyle('74%', lineH, lineR, 0.75)" />
            </view>
          </view>
        </view>

        <!-- card -->
        <view v-else-if="props.variant === 'card'" class="z-sk__card">
          <view class="z-sk z-sk--rect" :style="skStyle('100%', props.mediaHeight, props.cardRadius)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view class="z-sk z-sk--line" :style="skStyle('68%', lineH, lineR)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view class="z-sk z-sk--line" :style="skStyle('92%', lineH, lineR, 0.85)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view class="z-sk z-sk--line" :style="skStyle('56%', lineH, lineR, 0.75)" />
        </view>

        <!-- article -->
        <view v-else-if="props.variant === 'article'" class="z-sk__article">
          <view class="z-sk z-sk--line" :style="skStyle('78%', titleH, lineR)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view v-for="i in paragraphN" :key="i" class="z-sk z-sk--line"
            :style="skStyle(i === paragraphN ? '64%' : '100%', lineH, lineR, i === paragraphN ? 0.78 : 0.9)" />
        </view>

        <!-- grid -->
        <view v-else-if="props.variant === 'grid'" class="z-sk__grid" :style="gridStyle">
          <view v-for="i in gridN" :key="i" class="z-sk z-sk--rect" :style="skStyle('100%', '100%', props.gridRadius)" />
        </view>

        <!-- fallback: soft blocks -->
        <view v-else class="z-sk__custom">
          <view class="z-sk z-sk--rect" :style="skStyle('100%', 140, props.cardRadius)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view class="z-sk z-sk--line" :style="skStyle('70%', lineH, lineR)" />
          <view class="z-sk__sp" :style="{ height: toUnit(props.gap) }" />
          <view class="z-sk z-sk--line" :style="skStyle('92%', lineH, lineR, 0.85)" />
        </view>
      </template>

      <!-- custom blocks -->
      <template v-else>
        <view class="z-sk__custom">
          <view
            v-for="(b, idx) in blocksN"
            :key="idx"
            class="z-sk"
            :class="{ 'z-sk--circle': b.type === 'circle', 'z-sk--line': b.type === 'line' }"
            :style="customBlockStyle(b)"
          />
        </view>
      </template>
    </template>

    <!-- content -->
    <template v-else>
      <slot />
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type SkeletonTheme = 'light' | 'dark'
type SkeletonVariant = 'list' | 'card' | 'article' | 'grid' | 'custom'
type SkeletonBlockType = 'rect' | 'line' | 'circle'
type SkeletonBlock = {
  type?: SkeletonBlockType
  width?: string | number
  height?: string | number
  radius?: string | number
  opacity?: number
  marginTop?: string | number
  marginBottom?: string | number
}

const props = withDefaults(defineProps<{
  /** show skeleton when true */
  loading?: boolean

  /** preset */
  variant?: SkeletonVariant

  /** theme colors */
  theme?: SkeletonTheme

  /** enable shimmer animation */
  active?: boolean
  /** shimmer speed (ms) */
  duration?: number

  /** container */
  background?: string
  padding?: string | (string | number)[]
  radius?: string | number

  /** base / highlight colors override */
  baseColor?: string
  highlightColor?: string

  /** common spacing */
  gap?: number
  /** list rows */
  rows?: number
  /** list: show avatar */
  avatar?: boolean
  /** list: lines count per row (2~3) */
  lines?: number
  /** list: row gap */
  rowGap?: number

  /** card: media height */
  mediaHeight?: number
  /** card radius */
  cardRadius?: string | number

  /** article: paragraph lines */
  paragraph?: number

  /** grid: columns */
  cols?: number
  /** grid: rows */
  gridRows?: number
  /** grid: item radius */
  gridRadius?: string | number

  /** custom blocks */
  blocks?: SkeletonBlock[]

  /** tag passthrough */
  tag?: any
}>(), {
  loading: true,
  variant: 'list',
  theme: 'light',
  active: true,
  duration: 1200,

  background: 'transparent',
  padding: '0',
  radius: 0,

  baseColor: '',
  highlightColor: '',

  gap: 14,
  rows: 3,
  avatar: true,
  lines: 2,
  rowGap: 18,

  mediaHeight: 240,
  cardRadius: 18,

  paragraph: 6,

  cols: 3,
  gridRows: 2,
  gridRadius: 16,

  blocks: () => ([
    { type: 'rect', width: '100%', height: 160, radius: 18 },
    { type: 'line', width: '72%', height: 26, radius: 999, marginTop: 14 },
    { type: 'line', width: '92%', height: 26, radius: 999, marginTop: 12, opacity: 0.85 },
    { type: 'line', width: '58%', height: 26, radius: 999, marginTop: 12, opacity: 0.75 }
  ]),
  tag: 0
})

function toUnit(v: any, unit = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${unit}`
  return String(v)
}

function normalizePadding(p: any): string {
  if (!p) return ''
  if (typeof p === 'string') return p
  if (!Array.isArray(p)) return ''
  const a = p.map((x) => (typeof x === 'number' ? `${x}rpx` : String(x)))
  if (a.length === 1) return a[0]
  if (a.length === 2) return `${a[0]} ${a[1]}`
  if (a.length === 3) return `${a[0]} ${a[1]} ${a[2]}`
  return `${a[0]} ${a[1]} ${a[2]} ${a[3]}`
}

const themeBase = computed(() => {
  if (props.baseColor) return props.baseColor
  return props.theme === 'dark' ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.06)'
})
const themeHi = computed(() => {
  if (props.highlightColor) return props.highlightColor
  return props.theme === 'dark' ? 'rgba(255,255,255,0.20)' : 'rgba(255,255,255,0.70)'
})

const wrapStyle = computed(() => ({
  width: '100%',
  boxSizing: 'border-box',
  background: props.background,
  padding: normalizePadding(props.padding),
  borderRadius: toUnit(props.radius),
}))

const lineH = computed(() => 24)
const titleH = computed(() => 30)
const lineR = computed(() => 999)
const avatarSize = computed(() => 84)

const rowsN = computed(() => Math.max(1, Math.min(20, props.rows)))
const paragraphN = computed(() => Math.max(3, Math.min(30, props.paragraph)))
const gridN = computed(() => Math.max(1, Math.min(60, props.cols * props.gridRows)))
const blocksN = computed(() => Array.isArray(props.blocks) ? props.blocks : [])

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(${Math.max(1, props.cols)}, 1fr)`,
  gridAutoRows: '1fr',
  gap: toUnit(props.gap),
}))

function shimmerStyle(opacity = 1) {
  return {
    position: 'relative',
    overflow: 'hidden',
    background: themeBase.value,
    opacity,
    '--z-sk-hi': themeHi.value,
    '--z-sk-dur': `${props.duration}ms`,
    '--z-sk-active': props.active ? 1 : 0
  } as any
}

function skStyle(w: any, h: any, r: any, opacity = 1) {
  return {
    width: typeof w === 'number' ? toUnit(w) : String(w),
    height: typeof h === 'number' ? toUnit(h) : String(h),
    borderRadius: typeof r === 'number' ? toUnit(r) : String(r),
    ...shimmerStyle(opacity)
  }
}

function customBlockStyle(b: SkeletonBlock) {
  const type = b.type || 'rect'
  const r = type === 'circle' ? 9999 : (b.radius ?? (type === 'line' ? 999 : 16))
  return {
    width: b.width === undefined ? '100%' : (typeof b.width === 'number' ? toUnit(b.width) : String(b.width)),
    height: b.height === undefined ? toUnit(26) : (typeof b.height === 'number' ? toUnit(b.height) : String(b.height)),
    borderRadius: typeof r === 'number' ? toUnit(r) : String(r),
    marginTop: toUnit(b.marginTop || 0),
    marginBottom: toUnit(b.marginBottom || 0),
    ...shimmerStyle(b.opacity ?? 1)
  }
}
</script>

<style scoped>
.z-skeleton{ width: 100%; }

/* skeleton block */
.z-sk{
  position: relative;
  background: rgba(0,0,0,0.06);
}
.z-sk::after{
  content: '';
  position: absolute;
  top: 0;
  left: -60%;
  width: 60%;
  height: 100%;
  background-image: linear-gradient(90deg, transparent, var(--z-sk-hi, rgba(255,255,255,0.65)), transparent);
  transform: translateX(0);
  opacity: calc(var(--z-sk-active, 1) * 1);
  animation: zSkMove var(--z-sk-dur, 1200ms) ease-in-out infinite;
}
@keyframes zSkMove{
  0%{ left: -60%; }
  100%{ left: 120%; }
}

.z-sk--circle{ border-radius: 9999rpx; }
.z-sk--line{ border-radius: 999rpx; }

.z-sk__sp{ width: 1rpx; }

/* list */
.z-sk__row{
  display: flex;
  align-items: flex-start;
}
.z-sk__col{
  flex: 1;
  min-width: 0;
}

/* card/article/custom */
.z-sk__card,.z-sk__article,.z-sk__custom{
  width: 100%;
}

/* grid */
.z-sk__grid{
  width: 100%;
}
.z-sk__grid .z-sk{
  aspect-ratio: 1 / 1;
}
</style>
