<template>
  <view class="z-picker">
    <!-- mask -->
    <view
      class="z-picker__mask"
      :class="{ 'is-show': innerVisible }"
      :style="{ zIndex: zIndex, background: maskBackground }"
      @tap="onMaskTap"
      @touchmove.stop.prevent="noop"
    />
    <!-- panel -->
    <view
      class="z-picker__panel"
      :class="{ 'is-show': innerVisible, 'is-dark': theme === 'dark' }"
      :style="{ zIndex: zIndex + 1 }"
      @touchmove.stop.prevent="noop"
    >
      <view class="z-picker__header">
        <view class="z-picker__btn" @tap="onCancel">{{ cancelText }}</view>
        <view class="z-picker__title">{{ title }}</view>
        <view class="z-picker__btn z-picker__btn--primary" @tap="onConfirm">{{ confirmText }}</view>
      </view>

      <picker-view
        class="z-picker__body"
        :style="{ height: bodyHeight }"
        :value="indexes"
        :indicator-style="indicatorStyle"
        @change="onChange"
      >
        <picker-view-column v-for="(col, colIndex) in columns" :key="colIndex">
          <view
            v-for="(item, rowIndex) in col"
            :key="rowIndex"
            class="z-picker__item"
          >
            {{ getLabel(item) }}
          </view>
        </picker-view-column>
      </picker-view>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

/**
 * 支持两类数据：
 * 1) 非联动：options = ['A','B'] 或 [['A','B'],['1','2']]
 * 2) 联动：options = [{ label, value, children: [...] }]
 */
const props = defineProps({
  modelValue: { type: [Array, String, Number], default: () => [] },
  visible: { type: Boolean, default: false },

  options: { type: Array, default: () => [] },
  cascade: { type: Boolean, default: false },

  labelKey: { type: String, default: 'text' },
  valueKey: { type: String, default: 'value' },
  childrenKey: { type: String, default: 'children' },

  title: { type: String, default: '请选择' },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },

  height: { type: [Number, String], default: 520 }, // rpx
  itemHeight: { type: [Number, String], default: 70 }, // rpx
  theme: { type: String, default: 'light' }, // light | dark

  maskClosable: { type: Boolean, default: true },
  maskBackground: { type: String, default: 'rgba(0,0,0,.55)' },
  zIndex: { type: Number, default: 999 },

  // 自定义透传参数
  param: { type: [String, Number], default: '' }
})

const emit = defineEmits([
  'update:modelValue',
  'update:visible',
  'change',
  'confirm',
  'cancel'
])

const innerVisible = ref(false)

// columns & indexes
const columns = ref([])
const indexes = ref([])

const bodyHeight = computed(() => `${Number(props.height)}rpx`)
const indicatorStyle = computed(() => `height:${Number(props.itemHeight)}rpx;`)

const is2D = (arr) => Array.isArray(arr) && Array.isArray(arr[0])

function getLabel(item) {
  if (item == null) return ''
  if (typeof item === 'string' || typeof item === 'number') return String(item)
  return String(item[props.labelKey] ?? item.label ?? item.text ?? '')
}

function getValue(item) {
  if (item == null) return ''
  if (typeof item === 'string' || typeof item === 'number') return item
  return item[props.valueKey] ?? item.value ?? item.id ?? getLabel(item)
}

function getChildren(item) {
  if (!item || typeof item !== 'object') return []
  return item[props.childrenKey] ?? item.children ?? []
}

function toArrayValue(v) {
  return Array.isArray(v) ? v : (v === '' || v == null ? [] : [v])
}

/** 根据 modelValue 计算各列 index */
function calcIndexesByValue(cols, values) {
  const idx = []
  for (let i = 0; i < cols.length; i++) {
    const col = cols[i] || []
    const target = values[i]
    let found = 0
    if (target != null && col.length) {
      const hit = col.findIndex(it => String(getValue(it)) === String(target) || String(getLabel(it)) === String(target))
      found = hit >= 0 ? hit : 0
    }
    idx.push(found)
  }
  return idx
}

function buildNonCascade() {
  const opts = props.options || []
  const cols = is2D(opts) ? opts : [opts]
  columns.value = cols
  indexes.value = calcIndexesByValue(cols, toArrayValue(props.modelValue))
}

function buildCascade() {
  const root = Array.isArray(props.options) ? props.options : []
  const values = toArrayValue(props.modelValue)
  const cols = []
  const idx = []

  let levelList = root
  let level = 0
  while (levelList && levelList.length) {
    cols.push(levelList)
    const wanted = values[level]
    let hit = 0
    if (wanted != null) {
      const i = levelList.findIndex(it => String(getValue(it)) === String(wanted))
      hit = i >= 0 ? i : 0
    }
    idx.push(hit)
    const picked = levelList[hit]
    const next = getChildren(picked)
    if (!next || !next.length) break
    levelList = next
    level++
    // 防止无限层
    if (level > 20) break
  }

  columns.value = cols
  indexes.value = idx
}

function rebuild() {
  if (props.cascade) buildCascade()
  else buildNonCascade()
}

watch(
  () => [props.options, props.cascade, props.labelKey, props.valueKey, props.childrenKey],
  () => rebuild(),
  { deep: true, immediate: true }
)

watch(
  () => props.modelValue,
  () => {
    // 外部改值时同步回 picker
    rebuild()
  },
  { deep: true }
)

watch(
  () => props.visible,
  (v) => {
    innerVisible.value = !!v
    if (v) nextTick(() => rebuild())
  },
  { immediate: true }
)

function noop() {}

function onMaskTap() {
  if (!props.maskClosable) return
  close('mask')
}

function close(reason) {
  innerVisible.value = false
  emit('update:visible', false)
  emit('cancel', { reason, param: props.param })
}

function onCancel() {
  close('cancel')
}

function onChange(e) {
  const nextIdx = (e?.detail?.value || []).map(n => Number(n) || 0)

  if (!props.cascade) {
    indexes.value = nextIdx
    const payload = getResult(nextIdx)
    emit('change', payload)
    return
  }

  // cascade: 变更列后，重建后续列
  const oldIdx = indexes.value.slice()
  let changedCol = 0
  for (let i = 0; i < Math.max(oldIdx.length, nextIdx.length); i++) {
    if ((oldIdx[i] ?? 0) !== (nextIdx[i] ?? 0)) { changedCol = i; break }
  }

  // 固定当前列 index，并把后面重置为 0
  const fixed = nextIdx.slice(0, changedCol + 1)
  while (fixed.length < columns.value.length) fixed.push(0)

  // 根据 fixed 走树，生成新 columns
  const root = Array.isArray(props.options) ? props.options : []
  const cols = []
  const idx = []
  let list = root
  for (let lv = 0; lv < fixed.length; lv++) {
    if (!list || !list.length) break
    cols.push(list)
    const i = Math.min(Math.max(fixed[lv] ?? 0, 0), list.length - 1)
    idx.push(i)
    const picked = list[i]
    list = getChildren(picked)
  }
  columns.value = cols
  indexes.value = idx

  const payload = getResult(idx)
  emit('change', payload)
}

function getResult(idxArr) {
  const cols = columns.value || []
  const options = []
  const values = []
  const labels = []
  const indexesOut = []

  for (let c = 0; c < cols.length; c++) {
    const col = cols[c] || []
    const i = Math.min(Math.max(idxArr[c] ?? 0, 0), Math.max(col.length - 1, 0))
    const item = col[i]
    options.push(item)
    values.push(getValue(item))
    labels.push(getLabel(item))
    indexesOut.push(i)
  }

  const out = {
    values: props.cascade ? values : (values.length <= 1 ? values[0] : values),
    labels: props.cascade ? labels : (labels.length <= 1 ? labels[0] : labels),
    indexes: indexesOut,
    options,
    param: props.param
  }
  return out
}

function onConfirm() {
  const payload = getResult(indexes.value)
  emit('update:modelValue', payload.values)
  emit('confirm', payload)
  innerVisible.value = false
  emit('update:visible', false)
}
</script>

<style scoped>
.z-picker__mask{
  position: fixed;
  left:0; top:0; right:0; bottom:0;
  opacity: 0;
  pointer-events: none;
  transition: opacity .18s ease;
}
.z-picker__mask.is-show{ opacity: 1; pointer-events: auto; }

.z-picker__panel{
  position: fixed;
  left:0; right:0; bottom:0;
  transform: translateY(110%);
  transition: transform .22s ease;
  background: #ffffff;
  border-top-left-radius: 24rpx;
  border-top-right-radius: 24rpx;
  overflow: hidden;
}
.z-picker__panel.is-show{ transform: translateY(0); }
.z-picker__panel.is-dark{ background:#0f172a; }

.z-picker__header{
  height: 96rpx;
  padding: 0 28rpx;
  display:flex;
  align-items:center;
  justify-content: space-between;
  border-bottom: 1rpx solid rgba(0,0,0,.06);
}
.z-picker__panel.is-dark .z-picker__header{ border-bottom-color: rgba(255,255,255,.10); }

.z-picker__btn{
  font-size: 28rpx;
  color: rgba(17,24,39,.75);
  padding: 12rpx 10rpx;
}
.z-picker__panel.is-dark .z-picker__btn{ color: rgba(226,232,240,.80); }

.z-picker__btn--primary{
  color: #2563eb;
}
.z-picker__title{
  max-width: 60%;
  font-size: 30rpx;
  font-weight: 600;
  color: #111827;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.z-picker__panel.is-dark .z-picker__title{ color: #e2e8f0; }

.z-picker__body{
  width: 100%;
}

.z-picker__item{
  height: 70rpx;
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 28rpx;
  color:#111827;
}
.z-picker__panel.is-dark .z-picker__item{ color:#e2e8f0; }
</style>
