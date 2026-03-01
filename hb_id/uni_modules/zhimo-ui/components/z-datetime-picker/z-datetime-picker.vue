<template>
  <view class="zdtp-root">
    <!-- overlay -->
    <view v-if="innerShow" class="zdtp-overlay" :style="{ zIndex: zIndex }" @tap="onMaskTap">
      <view class="zdtp-panel" :style="{ borderTopLeftRadius: radiusPx, borderTopRightRadius: radiusPx }" @tap="onPanelTap">
        <view class="zdtp-head">
          <text class="zdtp-head__btn" @tap="onCancel">{{ cancelText }}</text>
          <text class="zdtp-head__title">{{ title }}</text>
          <text class="zdtp-head__btn zdtp-head__btn--ok" @tap="onConfirm">{{ confirmText }}</text>
        </view>

        <view v-if="range" class="zdtp-rangebar">
          <view class="zdtp-rangebar__chip" :class="{ 'is-on': editingSide === 'start' }" @tap="setSide('start')">
            <text class="zdtp-rangebar__label">开始</text>
            <text class="zdtp-rangebar__val">{{ startText }}</text>
          </view>
          <view class="zdtp-rangebar__chip" :class="{ 'is-on': editingSide === 'end' }" @tap="setSide('end')">
            <text class="zdtp-rangebar__label">结束</text>
            <text class="zdtp-rangebar__val">{{ endText }}</text>
          </view>
        </view>

        <picker-view class="zdtp-picker" :indicator-style="indicatorStyle" :value="activeIndexes" @change="onPickerChange">
          <picker-view-column v-for="(col, cIdx) in columns" :key="cIdx">
            <view v-for="(opt, oIdx) in col" :key="opt.v + '_' + oIdx" class="zdtp-item">
              <text class="zdtp-item__txt">{{ opt.t }}</text>
            </view>
          </picker-view-column>
        </picker-view>

        <view v-if="showHint" class="zdtp-hint">
          <text class="zdtp-hint__txt">{{ hintText }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { addDays, clampDate, daysInMonth, formatDate, toDate, diffDays } from '../../utils/datetime/index'

type Mode = 'year-month' | 'date' | 'datetime' | 'time'

type PickerOption = { v: number; t: string }

const props = withDefaults(
  defineProps<{
    show?: boolean
    modelValue?: string | string[]
    // picker mode
    mode?: Mode
    // range selection
    range?: boolean
    // min/max for date part
    minDate?: string | number | Date
    maxDate?: string | number | Date
    // limit range length (days). 0 / undefined means no limit
    maxDays?: number

    title?: string
    confirmText?: string
    cancelText?: string

    minuteStep?: number
    secondStep?: number

    zIndex?: number
    radius?: number

    // When true, show small hint text below
    showHint?: boolean
  }>(),
  {
    show: false,
    modelValue: '',
    mode: 'datetime',
    range: false,
    maxDays: 0,
    title: '选择日期时间',
    confirmText: '确定',
    cancelText: '取消',
    minuteStep: 1,
    secondStep: 1,
    zIndex: 1000,
    radius: 18,
    showHint: true
  }
)

const emit = defineEmits<{
  (e: 'update:show', v: boolean): void
  (e: 'update:modelValue', v: string | string[]): void
  (e: 'confirm', v: string | string[]): void
  (e: 'cancel'): void
  (e: 'change', v: string | string[]): void
}>()

const innerShow = ref<boolean>(false)
watch(
  () => props.show,
  (v) => (innerShow.value = !!v),
  { immediate: true }
)

function close() {
  innerShow.value = false
  emit('update:show', false)
}

const radiusPx = computed(() => `${props.radius}rpx`)
const indicatorStyle = computed(() => `height: 88rpx;`)
const columns = ref<PickerOption[][]>([])

// range state
const editingSide = ref<'start' | 'end'>('start')

const startDraft = ref<Date | null>(null)
const endDraft = ref<Date | null>(null)

const singleDraft = ref<Date | null>(null)

function asDateSafe(input: any, fallback: Date): Date {
  const d = toDate(input)
  return d ? d : fallback
}

function nowBase(): Date {
  return new Date()
}

function normalizeDraftsFromValue() {
  const baseNow = nowBase()
  if (props.range) {
    const arr = Array.isArray(props.modelValue) ? props.modelValue : []
    const s = arr[0] ? asDateSafe(arr[0], baseNow) : baseNow
    const e = arr[1] ? asDateSafe(arr[1], s) : s
    startDraft.value = clampDate(s, props.minDate, props.maxDate)
    endDraft.value = clampDate(e, props.minDate, props.maxDate)
    if (diffDays(startDraft.value, endDraft.value) < 0) endDraft.value = startDraft.value
  } else {
    const v = Array.isArray(props.modelValue) ? props.modelValue[0] : props.modelValue
    const d = v ? asDateSafe(v, baseNow) : baseNow
    singleDraft.value = clampDate(d, props.minDate, props.maxDate)
  }
}

watch(
  () => [props.modelValue, props.range, props.mode, props.minDate, props.maxDate, props.minuteStep, props.secondStep, props.show] as const,
  () => {
    normalizeDraftsFromValue()
    rebuildColumns()
    syncIndexesFromDraft()
  },
  { immediate: true }
)

const activeIndexes = ref<number[]>([])
const startIndexes = ref<number[]>([])
const endIndexes = ref<number[]>([])

const activeDraft = computed<Date | null>(() => {
  if (props.range) return editingSide.value === 'start' ? startDraft.value : endDraft.value
  return singleDraft.value
})

const startText = computed(() => (startDraft.value ? formatForMode(startDraft.value) : '未选择'))
const endText = computed(() => (endDraft.value ? formatForMode(endDraft.value) : '未选择'))

const hintText = computed(() => {
  if (!props.range) return formatForMode(singleDraft.value || nowBase())
  const s = startDraft.value ? formatForMode(startDraft.value) : '未选择'
  const e = endDraft.value ? formatForMode(endDraft.value) : '未选择'
  if (props.maxDays && props.maxDays > 0) return `区间：${s} ~ ${e}（最多 ${props.maxDays} 天）`
  return `区间：${s} ~ ${e}（不限制天数）`
})

function setSide(side: 'start' | 'end') {
  editingSide.value = side
  syncIndexesFromDraft()
}

function modeFmt(m: Mode) {
  if (m === 'year-month') return 'ym'
  if (m === 'date') return 'ymd'
  if (m === 'datetime') return 'ymdhm'
  return 'time'
}

function formatForMode(d: Date): string {
  const m = props.mode
  if (m === 'time') return formatDate(d, 'time')
  if (m === 'datetime') return formatDate(d, 'ymdhm')
  if (m === 'year-month') return formatDate(d, 'ym')
  return formatDate(d, 'ymd')
}

function rebuildColumns() {
  const mode = props.mode
  const base = activeDraft.value || nowBase()

  // Years range: based on min/max (if present), otherwise +-60 years
  const minD = toDate(props.minDate)
  const maxD = toDate(props.maxDate)
  const yMin = minD ? minD.getFullYear() : base.getFullYear() - 60
  const yMax = maxD ? maxD.getFullYear() : base.getFullYear() + 60

  const years: PickerOption[] = []
  for (let y = yMin; y <= yMax; y++) years.push({ v: y, t: `${y}年` })

  const months: PickerOption[] = []
  for (let m = 1; m <= 12; m++) months.push({ v: m, t: `${m}月` })

  // day column depends on year/month; use base selection at build time
  const y0 = base.getFullYear()
  const m0 = base.getMonth() + 1
  const dCount = daysInMonth(y0, m0)
  const days: PickerOption[] = []
  for (let d = 1; d <= dCount; d++) days.push({ v: d, t: `${d}日` })

  const hours: PickerOption[] = []
  for (let h = 0; h <= 23; h++) hours.push({ v: h, t: `${h}时` })

  const minutes: PickerOption[] = []
  const minStep = Math.max(1, Number(props.minuteStep || 1))
  for (let mi = 0; mi <= 59; mi += minStep) minutes.push({ v: mi, t: `${mi}分` })

  const seconds: PickerOption[] = []
  const secStep = Math.max(1, Number(props.secondStep || 1))
  for (let s = 0; s <= 59; s += secStep) seconds.push({ v: s, t: `${s}秒` })

  let cols: PickerOption[][] = []
  if (mode === 'year-month') cols = [years, months]
  else if (mode === 'date') cols = [years, months, days]
  else if (mode === 'datetime') cols = [years, months, days, hours, minutes]
  else cols = [hours, minutes] // time
  columns.value = cols
}

function ensureDaysColumnBy(y: number, m: number) {
  const mode = props.mode
  if (mode === 'time') return
  if (mode === 'year-month') return
  const dCount = daysInMonth(y, m)
  const days: PickerOption[] = []
  for (let d = 1; d <= dCount; d++) days.push({ v: d, t: `${d}日` })
  // day column index: 2
  columns.value = columns.value.map((c, idx) => (idx === 2 ? days : c))
}

function findIndexByValue(col: PickerOption[], v: number): number {
  const idx = col.findIndex((x) => x.v === v)
  return idx >= 0 ? idx : 0
}

function syncIndexesFromDraft() {
  const d = activeDraft.value || nowBase()
  const mode = props.mode
  if (mode === 'time') {
    const h = d.getHours()
    const mi = d.getMinutes()
    const idxH = findIndexByValue(columns.value[0] || [], h)
    // minutes column uses step, may not contain exact minute
    const miCol = columns.value[1] || []
    let idxM = findIndexByValue(miCol, mi)
    if (idxM === 0 && miCol.length) {
      // pick nearest
      let best = 0
      let bestDiff = 999
      miCol.forEach((o, i) => {
        const diff = Math.abs(o.v - mi)
        if (diff < bestDiff) {
          bestDiff = diff
          best = i
        }
      })
      idxM = best
    }
    activeIndexes.value = [idxH, idxM]
  } else {
    const y = d.getFullYear()
    const m = d.getMonth() + 1
    ensureDaysColumnBy(y, m)
    const cols = columns.value
    const idxY = findIndexByValue(cols[0] || [], y)
    const idxM = findIndexByValue(cols[1] || [], m)
    const baseArr = [idxY, idxM]
    if (mode !== 'year-month') {
      const da = d.getDate()
      const idxD = findIndexByValue(cols[2] || [], da)
      baseArr.push(idxD)
    }
    if (mode === 'datetime') {
      const h = d.getHours()
      const mi = d.getMinutes()
      const idxH = findIndexByValue(cols[3] || [], h)
      let idxMin = findIndexByValue(cols[4] || [], mi)
      if (idxMin === 0 && (cols[4] || []).length) {
        let best = 0
        let bestDiff = 999
        ;(cols[4] || []).forEach((o, i) => {
          const diff = Math.abs(o.v - mi)
          if (diff < bestDiff) {
            bestDiff = diff
            best = i
          }
        })
        idxMin = best
      }
      baseArr.push(idxH, idxMin)
    }
    activeIndexes.value = baseArr
  }

  if (props.range) {
    if (editingSide.value === 'start') startIndexes.value = [...activeIndexes.value]
    else endIndexes.value = [...activeIndexes.value]
  }
}

function draftFromIndexes(idxs: number[]): Date {
  const base = activeDraft.value || nowBase()
  const mode = props.mode
  if (mode === 'time') {
    const h = (columns.value[0] || [])[idxs[0]]?.v ?? base.getHours()
    const mi = (columns.value[1] || [])[idxs[1]]?.v ?? base.getMinutes()
    const d = new Date(base.getTime())
    d.setHours(h, mi, 0, 0)
    return clampDate(d, props.minDate, props.maxDate)
  }

  const y = (columns.value[0] || [])[idxs[0]]?.v ?? base.getFullYear()
  const m = (columns.value[1] || [])[idxs[1]]?.v ?? base.getMonth() + 1
  ensureDaysColumnBy(y, m)
  const dayCol = columns.value[2] || []
  const da = mode === 'year-month' ? 1 : dayCol[idxs[2]]?.v ?? 1
  const d = new Date(y, m - 1, da, base.getHours(), base.getMinutes(), 0)

  if (mode === 'datetime') {
    const h = (columns.value[3] || [])[idxs[3]]?.v ?? 0
    const mi = (columns.value[4] || [])[idxs[4]]?.v ?? 0
    d.setHours(h, mi, 0, 0)
  } else {
    d.setHours(0, 0, 0, 0)
  }
  return clampDate(d, props.minDate, props.maxDate)
}

function applyDraft(d: Date) {
  if (props.range) {
    if (editingSide.value === 'start') startDraft.value = d
    else endDraft.value = d

    // enforce order
    const s = startDraft.value || d
    let e = endDraft.value || d
    if (diffDays(s, e) < 0) e = s

    // enforce maxDays if set
    if (props.maxDays && props.maxDays > 0) {
      const dd = diffDays(s, e)
      if (dd > props.maxDays) e = addDays(s, props.maxDays)
    }
    startDraft.value = s
    endDraft.value = clampDate(e, props.minDate, props.maxDate)
  } else {
    singleDraft.value = d
  }
}

function valueForEmit(): string | string[] {
  if (!props.range) {
    const d = singleDraft.value || nowBase()
    return formatForMode(d)
  }
  const s = startDraft.value ? formatForMode(startDraft.value) : ''
  const e = endDraft.value ? formatForMode(endDraft.value) : ''
  return [s, e]
}

function onPickerChange(e: any) {
  const idxs = e?.detail?.value || []
  activeIndexes.value = idxs
  const d = draftFromIndexes(idxs)
  applyDraft(d)
  emit('change', valueForEmit())
}

function onConfirm() {
  const v = valueForEmit()
  emit('update:modelValue', v)
  emit('confirm', v)
  close()
}

function onCancel() {
  emit('cancel')
  close()
}

function onMaskTap() {
  // click mask to close (same as cancel)
  onCancel()
}

function onPanelTap(e: any) {
  // stop bubbling in the most compatible way
  try {
    e?.stopPropagation?.()
  } catch (err) {}
}

function stop() {}

function setShow(v: boolean) {
  innerShow.value = v
  emit('update:show', v)
}
</script>

<style>
/* Keep style independent from other libraries to avoid collisions. */
.zdtp-overlay{
  position: fixed;
  left: 0; right: 0; top: 0; bottom: 0;
  background: rgba(0,0,0,.42);
  display: flex;
  align-items: flex-end;
}
.zdtp-panel{
  width: 100%;
  background: #fff;
  padding-bottom: env(safe-area-inset-bottom);
  overflow: hidden;
  box-shadow: 0 -12rpx 40rpx rgba(0,0,0,.12);
}
.zdtp-head{
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  border-bottom: 1px solid rgba(0,0,0,.06);
}
.zdtp-head__btn{
  font-size: 28rpx;
  padding: 14rpx 16rpx;
  color: rgba(0,0,0,.65);
}
.zdtp-head__btn--ok{
  color: #1677ff;
  font-weight: 600;
}
.zdtp-head__title{
  font-size: 30rpx;
  font-weight: 600;
  color: rgba(0,0,0,.88);
}
.zdtp-rangebar{
  display: flex;
  gap: 16rpx;
  padding: 18rpx 20rpx;
}
.zdtp-rangebar__chip{
  flex: 1;
  border-radius: 18rpx;
  background: rgba(0,0,0,.04);
  padding: 16rpx 18rpx;
  border: 1px solid rgba(0,0,0,.06);
}
.zdtp-rangebar__chip.is-on{
  border-color: rgba(22,119,255,.4);
  background: rgba(22,119,255,.08);
}
.zdtp-rangebar__label{
  font-size: 22rpx;
  color: rgba(0,0,0,.55);
}
.zdtp-rangebar__val{
  display: block;
  margin-top: 6rpx;
  font-size: 26rpx;
  color: rgba(0,0,0,.85);
}
.zdtp-picker{
  height: 520rpx;
}
.zdtp-item{
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.zdtp-item__txt{
  font-size: 30rpx;
  color: rgba(0,0,0,.85);
}
.zdtp-hint{
  padding: 18rpx 24rpx 26rpx;
  border-top: 1px solid rgba(0,0,0,.06);
}
.zdtp-hint__txt{
  font-size: 24rpx;
  color: rgba(0,0,0,.6);
}
</style>
