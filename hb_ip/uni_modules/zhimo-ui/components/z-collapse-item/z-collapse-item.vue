<template>
  <view class="z-coli" :style="wrapStyle">
    <!-- header -->
    <view
      class="z-coli__hd"
      :class="{ 'z-coli__hd--disabled': props.disabled }"
      :style="headerStyle"
      @tap.stop="onHeaderTap"
    >
      <view class="z-coli__hd-left">
        <slot name="icon">
          <view v-if="props.icon" class="z-coli__icon">
            <z-icon :name="props.icon" :size="props.iconSize" :color="resolvedIconColor" />
          </view>
        </slot>

        <view class="z-coli__titles">
          <slot>
            <text class="z-coli__title" :style="titleStyle">{{ props.title }}</text>
          </slot>
          <text v-if="hasDesc" class="z-coli__desc" :class="{ 'z-ellipsis-1': props.singleLine }" :style="descStyle">
            {{ props.desc }}
          </text>
        </view>
      </view>

      <view class="z-coli__hd-right">
        <slot name="right" />
        <slot name="arrow">
          <view v-if="props.arrow" class="z-coli__arrow" :class="{ 'z-coli__arrow--open': isOpen }" :style="arrowWrapStyle">
            <z-icon :name="props.arrowIcon" :size="props.arrowSize" :color="resolvedArrowColor" />
          </view>
        </slot>
      </view>

      <view v-if="props.divider" class="z-coli__divider" :style="dividerStyle"></view>
    </view>

    <!-- body -->
    <view
      class="z-coli__bd-wrap"
      :style="bodyWrapStyle"
      :class="{ 'z-coli__bd-ani': enableAni }"
    >
      <view
        :id="contentId"
        ref="contentRef"
        class="z-coli__bd"
        :style="bodyStyle"
      >
        <slot name="content" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, inject, nextTick, onMounted, ref, watch } from 'vue'

// #ifdef APP-NVUE
const dom = weex.requireModule('dom')
// #endif

type NameType = string | number

const props = withDefaults(defineProps<{
  name?: NameType
  index?: NameType

  disabled?: boolean

  title?: string
  desc?: string
  singleLine?: boolean

  headerBg?: string
  titleColor?: string
  descColor?: string
  padding?: string | (string | number)[]
  radius?: string | number

  icon?: string
  iconColor?: string
  iconSize?: number

  arrow?: boolean
  arrowIcon?: string
  arrowSize?: number
  arrowColor?: string

  divider?: boolean
  dividerColor?: string
  dividerInset?: string | number

  contentBg?: string

  animation?: boolean
  duration?: number
  lazy?: boolean

  open?: boolean

  tag?: any
}>(), {
  name: undefined,
  index: 0,

  disabled: false,

  title: 'Title',
  desc: '',
  singleLine: false,

  headerBg: '',
  titleColor: '',
  descColor: '',
  padding: '',
  radius: '',

  icon: '',
  iconColor: '',
  iconSize: 22,

  arrow: true,
  arrowIcon: 'mdi:chevron-right',
  arrowSize: 22,
  arrowColor: '',

  divider: true,
  dividerColor: 'rgba(0,0,0,0.06)',
  dividerInset: 0,

  contentBg: '#FFFFFF',

  animation: undefined,
  duration: undefined,
  lazy: undefined,

  open: false,

  tag: 0
})

const emit = defineEmits<{
  (e: 'change', payload: { name: NameType; open: boolean; tag: any }): void
  (e: 'update:open', v: boolean): void
}>()

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

const contentId = `zcoli_${Math.ceil(Math.random() * 10e6).toString(36)}`
const contentRef = ref<any>(null)
const measured = ref(0)
const localOpen = ref(!!props.open)

watch(() => props.open, (v) => { localOpen.value = !!v })

const inst = getCurrentInstance()

// inject from parent z-collapse (string key)
type CollapseCtx = {
  hasActive: (name: NameType) => boolean
  toggle: (name: NameType) => void
  defaults: any
  key: string
}
const ctx = inject<CollapseCtx | null>('z-collapse-ctx', null)

const itemName = computed<NameType>(() => (props.name ?? props.index) as any)

const isOpen = computed<boolean>(() => {
  if (ctx) return !!ctx.hasActive(itemName.value)
  return !!localOpen.value
})

const defaults = computed(() => (ctx && ctx.defaults?.value) ? ctx.defaults.value : ({
  animation: true,
  duration: 220,
  lazy: false,
  gap: '16rpx',
  radius: '16rpx',
  bordered: false,
  borderColor: 'rgba(0,0,0,0.08)',
  background: 'transparent',
  shadow: false
}))

const enableAni = computed(() => {
  const v = props.animation
  return (v === undefined ? defaults.value.animation : v) && !props.disabled
})
const aniDuration = computed(() => {
  const v = props.duration
  return v === undefined ? defaults.value.duration : v
})
const enableLazy = computed(() => {
  const v = props.lazy
  return v === undefined ? defaults.value.lazy : v
})

const hasDesc = computed(() => !!(props.desc && String(props.desc).trim().length > 0))

const baseAccent = computed(() => '#465CFF')
const resolvedIconColor = computed(() => props.iconColor || baseAccent.value)
const resolvedArrowColor = computed(() => props.arrowColor || 'rgba(0,0,0,0.45)')

const wrapStyle = computed(() => ({
  width: '100%',
  boxSizing: 'border-box',
  marginTop: defaults.value.gap
}))

const headerStyle = computed(() => {
  const style: Record<string, any> = {
    background: props.headerBg || '#FFFFFF',
    borderRadius: toUnit(props.radius) || defaults.value.radius,
    padding: normalizePadding(props.padding) || '22rpx 24rpx',
    boxSizing: 'border-box'
  }
  if (defaults.value.shadow) style.boxShadow = '0 10rpx 24rpx rgba(0,0,0,0.06)'
  if (defaults.value.bordered) {
    style.borderWidth = '2rpx'
    style.borderStyle = 'solid'
    style.borderColor = defaults.value.borderColor
  }
  return style
})

const titleStyle = computed(() => ({
  color: props.titleColor || 'rgba(15,23,42,0.92)',
  fontSize: '30rpx',
  fontWeight: 700,
  lineHeight: 1.2
}))
const descStyle = computed(() => ({
  color: props.descColor || 'rgba(15,23,42,0.62)',
  fontSize: '25rpx',
  marginTop: '8rpx',
  lineHeight: 1.35
}))
const dividerStyle = computed(() => ({
  background: props.dividerColor,
  left: toUnit(props.dividerInset) || '0rpx'
}))
const arrowWrapStyle = computed(() => ({ marginLeft: '14rpx' }))

const bodyWrapStyle = computed(() => ({
  height: (isOpen.value ? measured.value : 0) + 'px',
  background: props.contentBg,
  borderRadius: toUnit(props.radius) || defaults.value.radius,
  overflow: 'hidden',
  marginTop: '10rpx',
  transitionDuration: `${aniDuration.value}ms`
}))

const bodyStyle = computed(() => ({
  padding: '18rpx 24rpx 22rpx',
  boxSizing: 'border-box',
  background: props.contentBg
}))

async function measure() {
  await nextTick()

  // #ifdef APP-NVUE
  try {
    const el = contentRef.value
    if (!el) return
    dom.getComponentRect(el, (ret: any) => {
      if (ret && ret.size) measured.value = Math.ceil(ret.size.height || 0)
    })
    return
  } catch (e) {}
  // #endif

  try {
    const q = uni.createSelectorQuery()
    // #ifndef MP-ALIPAY
    if (inst) q.in(inst)
    // #endif
    q.select('#' + contentId).boundingClientRect((r: any) => {
      measured.value = Math.ceil((r && r.height) ? r.height : 0)
    }).exec()
  } catch (e) {}
}

watch(isOpen, async (v) => {
  if (v) await measure()
})

onMounted(async () => {
  if (isOpen.value) await measure()
  if (!enableLazy.value) await measure()
})

function onHeaderTap() {
  if (props.disabled) return

  if (ctx) {
    ctx.toggle(itemName.value)
    return
  }

  const next = !localOpen.value
  localOpen.value = next
  emit('update:open', next)
  emit('change', { name: itemName.value, open: next, tag: props.tag })
  if (next) measure()
}
</script>

<style scoped>
.z-coli{ width: 100%; box-sizing: border-box; }
.z-coli__hd{ position: relative; width: 100%; display:flex; align-items: center; justify-content: space-between; }
.z-coli__hd--disabled{ opacity: 0.55; }
.z-coli__hd-left{ display:flex; align-items:flex-start; flex:1; min-width:0; }
.z-coli__icon{ margin-right: 14rpx; margin-top: 2rpx; }
.z-coli__titles{ flex:1; min-width:0; }
.z-coli__title{ display:block; word-break: break-word; }
.z-coli__desc{ display:block; word-break: break-word; }
.z-ellipsis-1{ overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.z-coli__hd-right{ display:flex; align-items:center; margin-left: 10rpx; }
.z-coli__arrow{ transform: rotate(0deg); transition: transform 0.22s ease; }
.z-coli__arrow--open{ transform: rotate(90deg); }
.z-coli__divider{ position:absolute; left:0; right:0; bottom:0; height: 2rpx; background: rgba(0,0,0,0.06); }
.z-coli__bd-wrap{ width:100%; transition-property: height; transition-timing-function: ease; }
.z-coli__bd-ani{ transition-property: height; }
</style>
