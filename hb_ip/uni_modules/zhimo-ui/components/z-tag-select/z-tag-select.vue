<template>
  <view
    class="z-tag-select"
    :class="[
      nowrap ? 'z-tag-select--nowrap' : 'z-tag-select--wrap',
      disabled ? 'is-disabled' : ''
    ]"
    :style="[wrapStyle]"
  >
    <view
      v-for="(it, index) in viewList"
      :key="it.__key"
      class="z-tag-select__item"
      :class="[
        it.selected ? 'is-active' : '',
        it[disabledKey] ? 'is-item-disabled' : ''
      ]"
      :style="[getItemStyle(it)]"
      @tap.stop="onTap(index)"
    >
      <view v-if="showMark && it.selected" class="z-tag-select__mark" :style="[markStyle]">
        <slot name="mark" :item="it" :index="index">
          <text class="z-tag-select__mark-text" :style="markTextStyle">
            {{ getMarkText(it) }}
          </text>
        </slot>
      </view>

      <slot name="item" :item="it" :index="index" :active="it.selected">
        <text class="z-tag-select__text" :style="[getTextStyle(it)]">
          {{ it[labelKey] }}
        </text>
      </slot>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({
  /** 数据源：支持 string[] 或 object[] */
  items: { type: Array, default: () => [] },

  /** v-model: 单选 string/number；多选 array */
  modelValue: { type: [Array, String, Number], default: undefined },

  /** 兼容旧写法（不推荐）：value */
  value: { type: [Array, String, Number], default: undefined },

  /** 多选 */
  multiple: { type: Boolean, default: false },

  /** 单选：最小选择数（只允许 0 或 1）。=1 时不能取消已选 */
  min: { type: [Number, String], default: 1 },

  /** 多选：最少选几个 */
  multipleMin: { type: [Number, String], default: 0 },

  /** 最大可选个数（-1 不限制） */
  max: { type: [Number, String], default: -1 },

  /** 文本/值/禁用/全选 key */
  labelKey: { type: String, default: 'text' },
  valueKey: { type: String, default: 'value' },
  disabledKey: { type: String, default: 'disabled' },
  allKey: { type: String, default: 'isAll' },

  /** 单行不换行（外层建议配合 scroll-view） */
  nowrap: { type: Boolean, default: false },

  /** 交互禁用 */
  disabled: { type: Boolean, default: false },

  /** 外观 */
  gap: { type: [Number, String], default: 20 }, // rpx
  radius: { type: [Number, String], default: 10 }, // rpx
  size: { type: [Number, String], default: 24 }, // rpx
  width: { type: [Number, String], default: 0 }, // rpx, 0 auto
  height: { type: [Number, String], default: 0 }, // rpx, 0 auto
  padding: { type: Array, default: () => ['16rpx', '28rpx'] }, // [y, x] or [t,r,b,l]

  color: { type: String, default: '#333' },
  activeColor: { type: String, default: '' },

  background: { type: String, default: '#ffffff' },
  activeBgColor: { type: String, default: '#ffffff' },

  /** 边框颜色：未选 & 已选 */
  borderColor: { type: String, default: '#E5E7EB' },
  activeBorderColor: { type: String, default: '' },

  /** 主题色（未传 activeColor/activeBorderColor 时的兜底） */
  primaryColor: { type: String, default: '#465CFF' },

  /** 风格：filled / outline / soft */
  variant: { type: String, default: 'outline' },

  /** 角标/勾选标记 */
  mark: { type: Boolean, default: false },
  markChar: { type: String, default: '✓' },
  markSize: { type: [Number, String], default: 22 }, // rpx - 进一步缩小默认尺寸
  markPosition: { type: String, default: 'top-left' }, // top-left, top-right, bottom-left, bottom-right
  markShape: { type: String, default: 'triangle' }, // triangle, square
  markTextKey: { type: String, default: 'markText' }, // 自定义角标文字的字段名
})

const emit = defineEmits(['change', 'input', 'update:modelValue', 'update:value'])

function toNumber(v, d = 0) {
  const n = Number(v)
  return Number.isFinite(n) ? n : d
}

function toUnit(v, unit = 'rpx') {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'number') return `${v}${unit}`
  const s = String(v).trim()
  if (!s) return ''
  if (/[a-z%]+$/i.test(s)) return s
  const n = Number(s)
  if (Number.isFinite(n)) return `${n}${unit}`
  return s
}

function pad4(pad) {
  const arr = Array.isArray(pad) ? pad.slice() : []
  // 支持 [y, x]
  if (arr.length === 2) return [arr[0], arr[1], arr[0], arr[1]]
  // 支持 [t, r, b, l]
  if (arr.length >= 4) return [arr[0], arr[1], arr[2], arr[3]]
  // 单值
  if (arr.length === 1) return [arr[0], arr[0], arr[0], arr[0]]
  return ['0', '0', '0', '0']
}

const controlled = computed(() => {
  // 优先 modelValue，其次 value
  return props.modelValue !== undefined ? props.modelValue : props.value
})

const localValue = ref(props.multiple ? [] : '')

const normalizedList = ref([])

function normalizeItems(list) {
  const src = Array.isArray(list) ? list : []
  const out = src.map((it, idx) => {
    if (typeof it !== 'object') {
      return {
        __key: `k_${idx}_${String(it)}`,
        [props.labelKey]: it,
        [props.valueKey]: it,
        [props.disabledKey]: false,
        [props.allKey]: false,
        selected: false,
      }
    }
    const o = { ...it }
    if (o[props.valueKey] === undefined) o[props.valueKey] = o[props.labelKey]
    if (o.selected === undefined) o.selected = false
    o.__key = o.__key || `k_${idx}_${String(o[props.valueKey])}`
    return o
  })
  return out
}

function applySelection(list, v) {
  const isMulti = !!props.multiple
  if (isMulti) {
    const arr = Array.isArray(v) ? v.slice() : []
    list.forEach((it) => (it.selected = arr.includes(it[props.valueKey])))
  } else {
    list.forEach((it) => (it.selected = v !== '' && v !== null && v !== undefined && v == it[props.valueKey]))
  }
}

function pickFromSelected(list) {
  if (props.multiple) {
    return list.filter((it) => it.selected).map((it) => it[props.valueKey])
  }
  const hit = list.find((it) => it.selected)
  return hit ? hit[props.valueKey] : ''
}

function init() {
  const list = normalizeItems(props.items)
  // 如果外部没传值：优先用 items 自带 selected
  const cv = controlled.value
  if (cv === undefined || cv === null || (Array.isArray(cv) && cv.length === 0) || (!Array.isArray(cv) && cv === '')) {
    const picked = pickFromSelected(list)
    localValue.value = props.multiple ? (Array.isArray(picked) ? picked : []) : (picked ?? '')
    applySelection(list, localValue.value)
  } else {
    localValue.value = props.multiple ? (Array.isArray(cv) ? cv.slice() : []) : cv
    applySelection(list, localValue.value)
  }
  normalizedList.value = list
}

watch(
  () => [props.items, props.multiple, props.labelKey, props.valueKey, props.disabledKey, props.allKey],
  () => init(),
  { deep: true, immediate: true }
)

watch(
  () => controlled.value,
  (v) => {
    if (v === undefined || v === null) return
    localValue.value = props.multiple ? (Array.isArray(v) ? v.slice() : []) : v
    const list = normalizedList.value.slice()
    applySelection(list, localValue.value)
    normalizedList.value = list
  },
  { deep: true }
)

const viewList = computed(() => normalizedList.value)

const showMark = computed(() => props.mark)

const markStyle = computed(() => {
  const s = toNumber(props.markSize, 22)  // 与 props 默认值保持一致
  const color =
    props.variant === 'filled'
      ? (props.activeBgColor || props.primaryColor)
      : (props.activeBorderColor || props.borderColor || props.primaryColor)

  const pos = props.markPosition || 'top-left'
  const shape = props.markShape || 'triangle'

  // 正方形角标
  if (shape === 'square') {
    const baseStyle = {
      width: `${s}rpx`,
      height: `${s}rpx`,
      background: color,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }

    if (pos === 'top-left') {
      return { ...baseStyle, left: '0', top: '0', borderTopLeftRadius: toUnit(props.radius, 'rpx') }
    } else if (pos === 'top-right') {
      return { ...baseStyle, right: '0', top: '0', borderTopRightRadius: toUnit(props.radius, 'rpx') }
    } else if (pos === 'bottom-left') {
      return { ...baseStyle, left: '0', bottom: '0', borderBottomLeftRadius: toUnit(props.radius, 'rpx') }
    } else if (pos === 'bottom-right') {
      return { ...baseStyle, right: '0', bottom: '0', borderBottomRightRadius: toUnit(props.radius, 'rpx') }
    }
    return { ...baseStyle, left: '0', top: '0', borderTopLeftRadius: toUnit(props.radius, 'rpx') }
  }

  const d=s+10
  // 三角形角标（使用 border 技巧）
  if (pos === 'top-left') {
    return {
      borderTop: `${d}rpx solid ${color}`,
      borderRight: `${d}rpx solid transparent`,
      width: '0',
      height: '0',
      left: '0',
      top: '0',
    }
  } else if (pos === 'top-right') {
    return {
      borderTop: `${d}rpx solid ${color}`,
      borderLeft: `${d}rpx solid transparent`,
      width: '0',
      height: '0',
      right: '0',
      top: '0',
    }
  } else if (pos === 'bottom-left') {
    return {
      borderBottom: `${d}rpx solid ${color}`,
      borderRight: `${d}rpx solid transparent`,
      width: '0',
      height: '0',
      left: '0',
      bottom: '0',
    }
  } else if (pos === 'bottom-right') {
    return {
      borderBottom: `${d}rpx solid ${color}`,
      borderLeft: `${d}rpx solid transparent`,
      width: '0',
      height: '0',
      right: '0',
      bottom: '0',
    }
  }

  // 默认左上角三角形
  return {
    borderTop: `${s}rpx solid ${color}`,
    borderRight: `${s}rpx solid transparent`,
    width: '0',
    height: '0',
    left: '0',
    top: '0',
  }
})

const markTextStyle = computed(() => {
  const s = toNumber(props.markSize, 22)
  const pos = props.markPosition || 'top-left'
  const shape = props.markShape || 'triangle'
  const variant = props.variant || 'outline'

  // 字体大小：大幅缩小到极小
  const fontSize = Math.max(4, s * 0.85)

  // 正方形：居中显示
  if (shape === 'square') {
    return {
      fontSize: `${fontSize}rpx`,
      color: '#fff',
      lineHeight: '1',
      fontWeight: '700',
      position: 'static',
    }
  }

  // 三角形：根据 variant 使用不同的偏移量
  let offset = 1
  let adjust = -30

  // filled 风格的三角形更大（d = s + 10），需要不同的偏移
  if (variant === 'filled') {
    offset = 3
    adjust = 1
  }

  const baseStyle = {
    fontSize: `${fontSize}rpx`,
    color: '#fff',
    lineHeight: '1',
    fontWeight: '700',
    position: 'absolute',
  }

  // 左上角
  if (pos === 'top-left') {
    return {
      ...baseStyle,
      left: `${offset}rpx`,
      top: `${adjust}rpx`,
      right: 'auto',
      bottom: 'auto',
    }
  }
  // 右上角
  else if (pos === 'top-right') {
    return {
      ...baseStyle,
      left: 'auto',
      top: `${adjust}rpx`,
      right: `${offset}rpx`,
      bottom: 'auto',
    }
  }
  // 左下角
  else if (pos === 'bottom-left') {
    return {
      ...baseStyle,
      left: `${offset}rpx`,
      top: 'auto',
      right: 'auto',
      bottom: `${adjust}rpx`,
    }
  }
  // 右下角
  else if (pos === 'bottom-right') {
    return {
      ...baseStyle,
      left: 'auto',
      top: 'auto',
      right: `${offset}rpx`,
      bottom: `${adjust}rpx`,
    }
  }

  // 默认左上角
  return {
    ...baseStyle,
    left: `${offset}rpx`,
    top: `${adjust}rpx`,
    right: 'auto',
    bottom: 'auto',
  }
})


const wrapStyle = computed(() => {
  const g = toNumber(props.gap, 0)
  return {
    marginBottom: g ? `-${g}rpx` : '0',
  }
})

function getItemStyle(it) {
  const g = toNumber(props.gap, 0)
  const [pt, pr, pb, pl] = pad4(props.padding)
  const isActive = !!it.selected

  const inactiveBorder = props.borderColor || props.background
  const activeBorder = props.activeBorderColor || props.borderColor || props.primaryColor

  const bg =
    props.variant === 'filled'
      ? isActive
        ? (props.activeBgColor || props.primaryColor)
        : props.background
      : props.variant === 'soft'
        ? isActive
          ? (props.activeBgColor || 'rgba(70,92,255,0.12)')
          : props.background
        : (isActive ? props.activeBgColor : props.background)

  const bd = props.variant === 'filled' ? 'transparent' : (isActive ? activeBorder : inactiveBorder)

  return {
    width: props.width ? toUnit(props.width, 'rpx') : 'auto',
    height: props.height ? toUnit(props.height, 'rpx') : 'auto',
    paddingTop: toUnit(pt, 'rpx'),
    paddingRight: toUnit(pr, 'rpx'),
    paddingBottom: toUnit(pb, 'rpx'),
    paddingLeft: toUnit(pl, 'rpx'),
    borderRadius: toUnit(props.radius, 'rpx'),
    marginRight: `${g}rpx`,
    marginBottom: `${g}rpx`,
    background: bg,
    borderColor: bd,
    borderWidth: '1px',
    borderStyle: 'solid',
    opacity: it[props.disabledKey] || props.disabled ? 0.5 : 1,
  }
}

function getTextStyle(it) {
  const isActive = !!it.selected
  const ac = props.activeColor || (props.variant === 'filled' ? '#fff' : props.primaryColor)
  return {
    fontSize: toUnit(props.size, 'rpx'),
    color: isActive ? ac : props.color,
    lineHeight: toUnit(props.size, 'rpx'),
    textAlign: 'center',
  }
}

function getMarkText(it) {
  // 优先使用 item 中的自定义角标文字
  if (it && it[props.markTextKey] !== undefined && it[props.markTextKey] !== null && it[props.markTextKey] !== '') {
    return String(it[props.markTextKey])
  }
  // 否则使用默认的 markChar
  return props.markChar
}

function toast(title) {
  uni.showToast({ title, icon: 'none' })
}

function emitAll(payload) {
  emit('change', payload)
  emit('input', payload.detail.value)
  emit('update:modelValue', payload.detail.value)
  emit('update:value', payload.detail.value)
}

function onTap(index) {
  if (props.disabled) return
  const list = normalizedList.value.slice()
  const it = list[index]
  if (!it || it[props.disabledKey]) return

  if (props.multiple) {
    let vals = Array.isArray(localValue.value) ? localValue.value.slice() : []
    const min = toNumber(props.multipleMin, 0)
    const max = toNumber(props.max, -1)
    const val = it[props.valueKey]
    const has = vals.includes(val)

    // 全选逻辑：存在 allKey=true 的项时，点击它会清空其它项；点击其它项会取消 all
    const allIndex = list.findIndex((x) => !!x[props.allKey])
    const allItem = allIndex !== -1 ? list[allIndex] : null

    if (allItem && it[props.allKey]) {
      // toggle all
      if (has) {
        // 取消 all：若 min>0 则不允许取消到小于 min
        if (vals.length <= min) {
          toast(`至少选择${min}个选项`)
          return
        }
        vals = vals.filter((x) => x !== val)
        it.selected = false
      } else {
        vals = [val]
        list.forEach((x, i) => (x.selected = i === index))
      }
    } else {
      // 普通项
      if (!has && max !== -1 && vals.length >= max) {
        toast(`最多只能选择${max}个选项`)
        return
      }
      if (has && vals.length <= min) {
        toast(`至少选择${min}个选项`)
        return
      }

      if (has) {
        vals = vals.filter((x) => x !== val)
        it.selected = false
      } else {
        vals.push(val)
        it.selected = true
      }

      // 取消 all
      if (allItem) {
        const allVal = allItem[props.valueKey]
        vals = vals.filter((x) => x !== allVal)
        allItem.selected = false
      }
    }

    // 同步其它 selected
    list.forEach((x) => (x.selected = vals.includes(x[props.valueKey])))

    localValue.value = vals
    normalizedList.value = list

    const entity = list.filter((x) => vals.includes(x[props.valueKey]))
    emitAll({ detail: { value: vals, item: entity } })
  } else {
    const min = toNumber(props.min, 1)
    const val = it[props.valueKey]
    const cur = localValue.value

    if (cur == val && min > 0) return

    let next = ''
    let nextIndex = -1
    let entity = {}
    list.forEach((x, i) => {
      if (i === index) {
        const willOff = cur == val && min <= 0
        x.selected = !willOff
        next = willOff ? '' : val
        nextIndex = willOff ? -1 : index
        entity = willOff ? {} : x
      } else {
        x.selected = false
      }
    })

    localValue.value = next
    normalizedList.value = list

    emitAll({ detail: { index: nextIndex, value: next, item: entity } })
  }
}

defineExpose({
  /** 手动刷新（items 异步变化后可调用） */
  refresh: () => nextTick(() => init()),
})
</script>

<style>
.z-tag-select {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
}

.z-tag-select--wrap {
  flex-wrap: wrap;
}

.z-tag-select--nowrap {
  flex-wrap: nowrap;
}

.z-tag-select__item {
  position: relative;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  overflow: visible; /* 改为 visible，让角标可以完整显示 */
}

.z-tag-select__text {
  /* #ifdef APP-NVUE */
  lines: 1;
  /* #endif */
  /* #ifndef APP-NVUE */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* #endif */
  flex: 1;
  font-weight: normal;
}

.z-tag-select__mark {
  position: absolute;
  z-index: 1;
}


.z-tag-select__mark-text {
  position: absolute !important;
  line-height: 1 !important;
  z-index: 2;
  pointer-events: none;
}



.is-item-disabled {
  /* #ifdef H5 */
  cursor: not-allowed;
  /* #endif */
}

.is-disabled {
  opacity: 0.6;
}
</style>
