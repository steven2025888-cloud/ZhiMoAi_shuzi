<template>
  <view class="zfb" :style="wrapStyle">
    <view class="zfb__row" :style="rowStyle">
      <view
        v-for="(it, idx) in localItems"
        :key="it.key ?? idx"
        class="zfb__item"
        :class="{
          'is-active': isItemActive(it),
          'is-switch': it.type === 'switch',
          'is-filter': it.type === 'filter'
        }"
        :style="itemStyle"
        @tap.stop="onItemTap(idx)"
      >
        <!-- text -->
        <template v-if="it.type !== 'switch'">
          <text
            class="zfb__text"
            :class="{ 'is-truncate': textTruncate }"
            :style="textStyle(it)"
          >{{ getLabel(it) }}</text>

          <!-- dropdown icon -->
          <view v-if="it.type === 'dropdown'" class="zfb__icon" :class="{ 'is-rotate': openIndex === idx }">
            <view class="zfb__chev" :style="chevStyle(it)"></view>
          </view>

          <!-- sort icon -->
          <view v-else-if="it.type === 'sort'" class="zfb__sort">
            <view class="zfb__tri up" :class="{ on: getSortDir(it) === 'asc' }" :style="triStyle(it)"></view>
            <view class="zfb__tri down" :class="{ on: getSortDir(it) === 'desc' }" :style="triStyle(it)"></view>
          </view>

          <!-- filter icon -->
          <view v-else-if="it.type === 'filter'" class="zfb__icon">
            <view class="zfb__funnel" :style="funnelStyle(it)"></view>
          </view>
        </template>

        <!-- switch -->
        <z-switch v-else :model-value="!!getSwitchVal(it)" @change="onSwitchChange(idx, $event)" size="small" />
      </view>
    </view>

    <!-- dropdown panel -->
    <view v-if="showDropdown" class="zfb__panel">
      <view v-if="mask" class="zfb__mask" :style="{ background: maskBackground }" @tap="closeDropdown('mask')"></view>

      <view class="zfb__panel-card" :style="panelStyle">
        <scroll-view
          scroll-y
          class="zfb__panel-scroll"
          :show-scrollbar="false"
          :style="{ maxHeight: maxHeight + 'rpx' }"
        >
          <view v-if="currentOptions.length === 0" style="padding: 40rpx; text-align: center; color: #999;">
            <text>暂无选项</text>
          </view>

          <view class="zfb__opt"
            v-for="(op, i) in currentOptions"
            :key="i"
            :class="{ on: isOptionActive(op) }"
            :style="optStyle(op)"
            @tap.stop="onOptionTap(op, i)"
          >
            <text class="zfb__opt-text" :style="optTextStyle(op)">{{ getOptionLabel(op) }}</text>
            <view v-if="isOptionActive(op)" class="zfb__check" :style="checkStyle"></view>
          </view>
        </scroll-view>

        <view v-if="panelFooter" class="zfb__panel-ft">
          <view class="zfb__ft-btn ghost" @tap="closeDropdown('cancel')">取消</view>
          <view class="zfb__ft-btn primary" :style="{ background: activeColor }" @tap="closeDropdown('ok')">确定</view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type AnyObj = Record<string, any>

type FilterItem = {
  key?: string | number
  type?: 'dropdown' | 'sort' | 'text' | 'switch' | 'filter'
  label?: string
  text?: string
  value?: any
  active?: boolean
  checked?: boolean
  disabled?: boolean
  // sort direction: 'asc' | 'desc' | ''
  sort?: 'asc' | 'desc' | '' | 0 | 1 | 2
}

type OptionItem = string | number | AnyObj

const props = defineProps({
  items: { type: Array as any, default: () => [] },
  dropdownOptions: { type: Array as any, default: () => [] }, // options per item index
  height: { type: [Number, String], default: 88 },
  size: { type: [Number, String], default: 28 },
  background: { type: String, default: '#ffffff' },
  color: { type: String, default: '#1f2937' },
  activeColor: { type: String, default: '#465CFF' },
  lineColor: { type: String, default: '#eeeeee' },
  paddingX: { type: [Number, String], default: 24 },

  // dropdown panel
  mask: { type: Boolean, default: true },
  maskBackground: { type: String, default: 'rgba(0,0,0,0.35)' },
  maxHeight: { type: Number, default: 560 },
  minWidth: { type: Number, default: 0 },
  splitLine: { type: Boolean, default: true },
  closeOnSelect: { type: Boolean, default: true },
  panelFooter: { type: Boolean, default: false },

  // behavior
  textTruncate: { type: Boolean, default: true }
})

const emit = defineEmits<{
  (e: 'update:items', v: FilterItem[]): void
  (e: 'change', payload: { index: number; item: FilterItem; items: FilterItem[]; type: string; extra?: any }): void
  (e: 'dropdown-open', payload: { index: number; item: FilterItem }): void
  (e: 'dropdown-close', payload: { index: number; reason: string }): void
  (e: 'filter', payload: { index: number; item: FilterItem; items: FilterItem[] }): void
}>()

const localItems = ref<FilterItem[]>([])

function cloneItems(v: any[]): FilterItem[] {
  try {
    return JSON.parse(JSON.stringify(v || []))
  } catch (e) {
    return (v || []).map(x => ({ ...(x || {}) }))
  }
}

watch(
  () => props.items,
  (v) => {
    localItems.value = cloneItems(v as any[])
  },
  { immediate: true, deep: true }
)

function setItems(next: FilterItem[], type: string, index: number, extra?: any) {
  localItems.value = next
  emit('update:items', cloneItems(next as any))
  emit('change', { index, item: next[index], items: cloneItems(next as any), type, extra })
}

function getLabel(it: FilterItem) {
  return String(it.label ?? it.text ?? '')
}

function isItemActive(it: FilterItem) {
  if (it.disabled) return false
  if (it.type === 'switch') return !!getSwitchVal(it)
  if (it.type === 'dropdown') return !!(it.value ?? '') || it.active
  if (it.type === 'sort') return getSortDir(it) !== ''
  return !!it.active
}

function getSwitchVal(it: FilterItem) {
  if (typeof it.checked === 'boolean') return it.checked
  if (typeof (it as any).switch === 'number') return (it as any).switch === 2
  return !!it.value
}

function getSortDir(it: FilterItem): 'asc' | 'desc' | '' {
  if (it.value === 'asc' || it.value === 'desc') return it.value
  if (it.sort === 'asc' || it.sort === 'desc') return it.sort
  //兼容旧值：1/2
  if (it.sort === 1) return ''
  if (it.sort === 2) return 'desc'
  return ''
}

// dropdown state
const openIndex = ref<number>(-1)
const showDropdown = computed(() => openIndex.value >= 0)

const currentItem = computed(() => {
  const idx = openIndex.value
  return idx >= 0 ? localItems.value[idx] : null
})

const currentOptions = computed<OptionItem[]>(() => {
  const idx = openIndex.value
  const all = props.dropdownOptions || []
  const ops = (idx >= 0 ? all[idx] : null) as any
  if (!ops) return []
  return Array.isArray(ops) ? ops : []
})

function getOptionLabel(op: OptionItem) {
  if (typeof op === 'string' || typeof op === 'number') return String(op)
  return String((op as any).label ?? (op as any).text ?? (op as any).name ?? '')
}

function getOptionValue(op: OptionItem) {
  if (typeof op === 'string' || typeof op === 'number') return op
  return (op as any).value ?? (op as any).id ?? getOptionLabel(op)
}

function isOptionActive(op: OptionItem) {
  const it = currentItem.value
  if (!it) return false
  return getOptionValue(op) === (it.value ?? '')
}

function onItemTap(index: number) {
  const it = localItems.value[index]
  if (!it || it.disabled) return

  const type = it.type || 'text'

  if (type === 'dropdown') {
    if (openIndex.value === index) {
      closeDropdown('toggle')
      return
    }
    openIndex.value = index
    // mark active
    localItems.value = localItems.value.map((x, i) => ({
      ...x,
      active: i === index ? true : (x.type === 'dropdown' ? false : x.active)
    }))
    emit('dropdown-open', { index, item: localItems.value[index] })
    return
  }

  if (type === 'switch') {
    const next = cloneItems(localItems.value)
    const cur = !!getSwitchVal(next[index])
    ;(next[index] as any).checked = !cur
    ;(next[index] as any).value = !cur
    setItems(next, 'switch', index, { checked: !cur })
    return
  }

  if (type === 'sort') {
    const next = cloneItems(localItems.value)
    const dir = getSortDir(next[index])
    const ndir = dir === '' ? 'asc' : (dir === 'asc' ? 'desc' : '')
    next[index].value = ndir
    // reset other sort if needed
    next.forEach((x, i) => {
      if (i !== index && x.type === 'sort') x.value = ''
    })
    setItems(next, 'sort', index, { dir: ndir })
    return
  }

  if (type === 'filter') {
    // just emit for parent to open panel/drawer
    const next = cloneItems(localItems.value)
    next[index].active = true
    setItems(next, 'filter', index)
    emit('filter', { index, item: next[index], items: cloneItems(next as any) })
    return
  }

  // text
  const next = cloneItems(localItems.value)
  next[index].active = !next[index].active
  setItems(next, 'text', index)
}

function onSwitchChange(index: number, checked: boolean) {
  const next = cloneItems(localItems.value)
  ;(next[index] as any).checked = checked
  ;(next[index] as any).value = checked
  setItems(next, 'switch', index, { checked })
}

function onOptionTap(op: OptionItem, optIndex: number) {
  const idx = openIndex.value
  if (idx < 0) return
  const next = cloneItems(localItems.value)
  next[idx].value = getOptionValue(op)
  next[idx].label = getOptionLabel(op)
  next[idx].active = true
  setItems(next, 'dropdown', idx, { option: op, optIndex })

  if (props.closeOnSelect && !props.panelFooter) {
    closeDropdown('select')
  }
}

function closeDropdown(reason: string) {
  const idx = openIndex.value
  if (idx < 0) return
  openIndex.value = -1
  emit('dropdown-close', { index: idx, reason })
}

// styles
const wrapStyle = computed(() => ({
  background: props.background,
  borderBottom: `1rpx solid ${props.lineColor}`
}))

const rowStyle = computed(() => ({
  height: `${Number(props.height)}rpx`,
  paddingLeft: `${Number(props.paddingX)}rpx`,
  paddingRight: `${Number(props.paddingX)}rpx`
}))

const itemStyle = computed(() => ({
  height: `${Number(props.height)}rpx`
}))

function textStyle(it: FilterItem) {
  return {
    fontSize: `${Number(props.size)}rpx`,
    lineHeight: `${Number(props.size)}rpx`,
    color: isItemActive(it) ? props.activeColor : props.color
  }
}

function chevStyle(it: FilterItem) {
  return {
    borderTopColor: isItemActive(it) ? props.activeColor : props.color
  }
}

function triStyle(it: FilterItem) {
  return {
    borderBottomColor: isItemActive(it) ? props.activeColor : props.color,
    borderTopColor: isItemActive(it) ? props.activeColor : props.color
  }
}

function funnelStyle(it: FilterItem) {
  return {
    borderTopColor: isItemActive(it) ? props.activeColor : props.color
  }
}

const panelStyle = computed(() => ({
  borderTop: `1rpx solid ${props.lineColor}`
}))

function optStyle(op: OptionItem) {
  return {
    borderBottom: props.splitLine ? `1rpx solid ${props.lineColor}` : 'none'
  }
}
function optTextStyle(op: OptionItem) {
  return {
    color: isOptionActive(op) ? props.activeColor : props.color
  }
}
const checkStyle = computed(() => ({
  borderColor: props.activeColor
}))
</script>

<style scoped>
.zfb{ position:relative; width:100%; }
.zfb__row{ display:flex; align-items:center; justify-content:space-between; box-sizing:border-box; }
.zfb__item{
  flex:1;
  display:flex;
  align-items:center;
  justify-content:center;
  box-sizing:border-box;
  position:relative;
  padding: 0 10rpx;
}
.zfb__text{
  max-width: 100%;
}
.zfb__text.is-truncate{
  overflow:hidden;
  text-overflow:ellipsis;
  white-space:nowrap;
}
.zfb__icon{ margin-left: 8rpx; display:flex; align-items:center; justify-content:center; }
.zfb__chev{
  width:0; height:0;
  border-left: 10rpx solid transparent;
  border-right: 10rpx solid transparent;
  border-top: 12rpx solid #333;
  transform-origin:center;
  transition: transform .18s ease;
}
.zfb__icon.is-rotate .zfb__chev{ transform: rotate(180deg); }

.zfb__sort{ margin-left: 10rpx; display:flex; flex-direction:column; line-height:0; gap: 4rpx; }
.zfb__tri{ width:0; height:0; }
.zfb__tri.up{
  border-left: 10rpx solid transparent;
  border-right: 10rpx solid transparent;
  border-bottom: 12rpx solid #9CA3AF;
  opacity:.5;
  transition: all 0.2s;
}
.zfb__tri.down{
  border-left: 10rpx solid transparent;
  border-right: 10rpx solid transparent;
  border-top: 12rpx solid #9CA3AF;
  opacity:.5;
  transition: all 0.2s;
}
.zfb__tri.on{ opacity: 1; transform: scale(1.1); }

.zfb__funnel{
  width:0; height:0;
  border-left: 12rpx solid transparent;
  border-right: 12rpx solid transparent;
  border-top: 14rpx solid #333;
  transform: translateY(2rpx);
}

.zfb__panel{ position:absolute; left:0; right:0; top:100%; z-index: 9999; }
.zfb__mask{ position:fixed; left:0; top:0; right:0; bottom:0; z-index: 9998; }
.zfb__panel-card{
  position:relative;
  z-index: 9999;
  background:#fff;
  border-radius: 0 0 24rpx 24rpx;
  overflow:hidden;
  box-shadow: 0 18rpx 44rpx rgba(0,0,0,.16);
  width: 100%;
  min-height: 100rpx;
}
.zfb__panel-scroll{ width:100%; min-width: 100%; }
.zfb__opt{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 22rpx 26rpx;
  box-sizing:border-box;
  min-height: 80rpx;
}
.zfb__opt.on{ background: rgba(70,92,255,.06); }
.zfb__opt-text{ font-size: 28rpx; line-height: 1.5; }
.zfb__check{
  width: 18rpx; height: 10rpx;
  border-left: 4rpx solid;
  border-bottom: 4rpx solid;
  transform: rotate(-45deg);
  margin-left: 16rpx;
}

.zfb__panel-ft{
  display:flex;
  gap: 18rpx;
  padding: 18rpx 18rpx;
  box-sizing:border-box;
  background:#fff;
  border-top: 1rpx solid #f1f5f9;
}
.zfb__ft-btn{
  flex:1;
  text-align:center;
  padding: 18rpx 0;
  border-radius: 999rpx;
  font-size: 28rpx;
}
.zfb__ft-btn.ghost{
  background:#f1f5f9;
  color:#111827;
}
.zfb__ft-btn.primary{
  color:#fff;
}
</style>
