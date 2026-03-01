<template>
  <view class="zdp-wrap" :style="{ background: bg, width: wrapWidth }">
    <!-- Header -->
    <view class="zdp-head">
      <view class="zdp-nav">
        <text class="zdp-btn" @tap="stepYear(-1)">«</text>
        <text class="zdp-btn" @tap="stepMonth(-1)">‹</text>
      </view>

      <view class="zdp-title" @tap="noop">
        <text class="zdp-title-main">{{ displayTitle }}</text>
        <text class="zdp-title-sub" v-if="subtitle">{{ subtitle }}</text>
      </view>

      <view class="zdp-nav">
        <text class="zdp-btn" @tap="stepMonth(1)">›</text>
        <text class="zdp-btn" @tap="stepYear(1)">»</text>
      </view>
    </view>

    <!-- Week header -->
    <view class="zdp-week" :style="{ borderBottomColor: lineColor, background: weekBg }">
      <view class="zdp-week-item" v-for="(w,i) in weekNames" :key="i" :style="weekItemStyleFull(i)">
        <text :style="{ color: weekItemStyle(i).color }">{{ w }}</text>
      </view>
    </view>

    <!-- Month body -->
    <swiper class="zdp-swiper" :vertical="vertical" :current="swiperIndex" @change="onSwiperChange" :duration="260">
      <swiper-item v-for="(m,idx) in months" :key="m.key">
        <view class="zdp-grid">
          <view class="zdp-cell" v-for="(d,di) in m.days" :key="m.key + '_' + di" :class="cellClass(d)" :style="cellBgStyle(d, di)">
            <view
              class="zdp-day"
              :class="dayClass(d)"
              :style="dayStyle(d)"
              @tap="onPick(d)"
            >
              <text class="zdp-day-num" :style="{ color: dayNumColor(d) }">{{ d.day }}</text>
              <!-- 有自定义文字时不显示农历和sub -->
              <text v-if="!(d.notes && d.notes.length) && showLunar && d.lunar" class="zdp-day-sub" :style="{ color: daySubColor(d) }">{{ d.lunar }}</text>
              <text v-else-if="!(d.notes && d.notes.length)" class="zdp-day-sub" :style="{ color: daySubColor(d) }">{{ d.sub }}</text>
              <view v-if="d.notes && d.notes.length" class="zdp-day-notes">
                <text v-for="(it,ii) in d.notes" :key="ii" class="zdp-day-note" :style="noteStyle(it, d)">{{ it.text }}</text>
              </view>
              <!-- 角标：支持圆点、emoji/文字 或 z-icon -->
              <view v-if="d.badge" class="zdp-badge" :class="{ 'zdp-badge--icon': d.badge.icon || d.badge.zicon }">
                <z-icon v-if="d.badge.zicon" :name="d.badge.zicon" :size="d.badge.size || 24" :color="d.badge.color || '#ff3b30'" />
                <text v-else-if="d.badge.icon" class="zdp-badge-icon" :style="{ color: d.badge.color || '#ff3b30' }">{{ d.badge.icon }}</text>
              </view>
            </view>
          </view>
        </view>
      </swiper-item>
    </swiper>

    <!-- Footer -->
    <view class="zdp-foot" v-if="confirmable || mode !== 'single'">
      <view class="zdp-foot-left">
        <text class="zdp-foot-tip">{{ tipText }}</text>
      </view>
      <view class="zdp-foot-right">
        <view class="zdp-action zdp-action-ghost" @tap="onClear">清空</view>
        <view class="zdp-action" :style="{ background: primary }" @tap="onConfirm">确定</view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, reactive, ref, watch, toRaw } from 'vue'
import { solar2lunar } from './lunar.js'
import ZIcon from '../z-icon/z-icon.vue'

const props = defineProps({
  modelValue: { type: [String, Array], default: '' }, // single: 'YYYY-MM-DD' | multiple/range: string[]
  mode: { type: String, default: 'single' }, // 'single' | 'multiple' | 'range'
  minDate: { type: String, default: '2010-01-01' },
  maxDate: { type: String, default: '2035-12-31' },
  maxDays: { type: [Number, String], default: -1 }, // multiple/range limit
  showLunar: { type: Boolean, default: false },
  weekStart: { type: Number, default: 0 }, // 0 Sunday, 1 Monday
  vertical: { type: Boolean, default: false },
  width: { type: [Number, String], default: 0 }, // rpx, 0=auto
  bg: { type: String, default: '#fff' },
  primary: { type: String, default: '#10b981' },
  text: { type: String, default: '#181818' },
  subText: { type: String, default: '#8a8a8a' },
  disabledText: { type: String, default: '#c7c7c7' },
  lineColor: { type: String, default: '#efefef' },
  confirmable: { type: Boolean, default: false }, // show footer & require confirm
  subtitle: { type: String, default: '' },
// Week header style
weekTextColor: { type: String, default: '#5a5a5a' },
weekendTextColor: { type: String, default: '#ff4d4f' },
weekColors: { type: Array, default: null }, // index 0=Sun..6=Sat
weekBg: { type: String, default: 'transparent' },

// Column background colors (按列设置背景，对应周几)
// { 0: '#e8f5e9', 6: '#e8f5e9' } 表示周日和周六列为浅绿色
// 注意：由于结构限制，周几标题和日期之间可能有间隙
columnBgColors: { type: Object, default: null },

// Day background colors by weekday (按周几设置日期背景色，不影响周几标题)
// { 6: 'rgba(34, 197, 94, 0.08)' } 表示周六的日期为浅绿色
dayBgColors: { type: Object, default: null },

// Notes under date cells. 支持：
// 1) notes map: { 'YYYY-MM-DD': '有座' | {text,color,badge:{icon,zicon,color,size}} | Array<...> }
// 2) noteFn: (dateStr, dayObj) => 同上
notes: { type: Object, default: () => ({}) },
noteFn: { type: Function, default: null },
noteColor: { type: String, default: '#ff7a00' },
showTodayNoteWhenLunar: { type: Boolean, default: true },

// Range style: 'gap' 浅色和首尾不连着 | 'connected' 浅色和首尾连着
rangeStyle: { type: String, default: 'gap' },

// Day cell style
cellRadius: { type: [Number, String], default: 18 }, // rpx
cellHeight: { type: [Number, String], default: 88 }, // rpx
noteFontSize: { type: [Number, String], default: 20 } // rpx
})

const emit = defineEmits(['update:modelValue', 'change', 'confirm', 'clear', 'panel-change', 'max-days-exceeded'])

function noop () {}

/** ---------- helpers ---------- */
function pad2(n){ return n<10 ? '0'+n : ''+n }
function toKey(y,m){ return y + '-' + pad2(m) }
function toDateStr(y,m,d){ return y + '-' + pad2(m) + '-' + pad2(d) }

function parseYMD(str){
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(str || '')
  if(!m) return null
  return { y: +m[1], m: +m[2], d: +m[3] }
}
function clampDateStr(str){
  // 简单夹逼：只对字符串比较安全（YYYY-MM-DD）
  if(str < props.minDate) return props.minDate
  if(str > props.maxDate) return props.maxDate
  return str
}
function daysInMonth(y,m){
  return new Date(y, m, 0).getDate()
}
function weekday(y,m,d){
  return new Date(y, m-1, d).getDay() // 0-6, Sunday=0
}
function addMonths(y,m,delta){
  let nm = m + delta
  let ny = y
  while(nm>12){ nm-=12; ny++ }
  while(nm<1){ nm+=12; ny-- }
  return { y: ny, m: nm }
}
function lunarText(y,m,d){
  try{
    const r = solar2lunar(y,m,d)
    return (r && (r.IDayCn || r.IMonthCn)) ? (d===1 ? r.IMonthCn : r.IDayCn) : ''
  }catch(e){
    return ''
  }
}


function hexToRgba(hex, a){
  const h = (hex || '').replace('#','').trim()
  const s = h.length === 3 ? h.split('').map(c=>c+c).join('') : h
  if(!/^([0-9a-fA-F]{6})$/.test(s)) return `rgba(22,119,255,${a})`
  const r = parseInt(s.slice(0,2), 16)
  const g = parseInt(s.slice(2,4), 16)
  const b = parseInt(s.slice(4,6), 16)
  return `rgba(${r},${g},${b},${a})`
}

const primaryLight = computed(() => hexToRgba(props.primary, 0.12))
const primaryLighter = computed(() => hexToRgba(props.primary, 0.08))


const noteFontSizePx = computed(() => (typeof props.noteFontSize === 'number' ? (props.noteFontSize + 'rpx') : (props.noteFontSize || '20rpx')))

function weekItemStyle(i){
  // i is header index 0..6, map to weekday 0=Sun..6=Sat based on weekStart
  const wd = (i + (props.weekStart === 1 ? 1 : 0)) % 7
  const custom = Array.isArray(props.weekColors) ? props.weekColors : null
  const c = custom && custom[wd] ? custom[wd] : ((wd === 0 || wd === 6) ? props.weekendTextColor : props.weekTextColor)
  return { color: c }
}

// 周几列的完整样式（包括背景）
function weekItemStyleFull(i){
  const wd = (i + (props.weekStart === 1 ? 1 : 0)) % 7
  const style = {}
  if(props.columnBgColors && props.columnBgColors[wd]){
    style.background = props.columnBgColors[wd]
  }
  return style
}

// 日期单元格的列背景
function cellBgStyle(d, di){
  // di 是在 42 个格子中的索引，计算出是周几
  const colIdx = di % 7
  const wd = (colIdx + (props.weekStart === 1 ? 1 : 0)) % 7
  const style = {}
  // columnBgColors 优先（会影响周几标题，但可能有间隙）
  if(props.columnBgColors && props.columnBgColors[wd]){
    style.background = props.columnBgColors[wd]
  }
  // dayBgColors 只影响日期，不影响周几标题
  if(props.dayBgColors && props.dayBgColors[wd]){
    style.background = props.dayBgColors[wd]
  }
  // connected 模式：首尾 cell 添加半边浅色背景，连接深色按钮和中间浅色
  const cellH = (typeof props.cellHeight === 'number' ? props.cellHeight + 'rpx' : (props.cellHeight || '88rpx'))
  if(props.mode === 'range' && props.rangeStyle === 'connected' && valueState.value.length >= 2){
    // 开始：右半边浅色背景
    if(isRangeStart(d.str)){
      style.background = `linear-gradient(to right, transparent 50%, ${primaryLight.value} 50%)`
      style.backgroundSize = `100% ${cellH}`
      style.backgroundPosition = 'center'
      style.backgroundRepeat = 'no-repeat'
    }
    // 结束：左半边浅色背景
    if(isRangeEnd(d.str)){
      style.background = `linear-gradient(to left, transparent 50%, ${primaryLight.value} 50%)`
      style.backgroundSize = `100% ${cellH}`
      style.backgroundPosition = 'center'
      style.backgroundRepeat = 'no-repeat'
    }
  }
  return style
}

// cell 的 class
function cellClass(d){
  const cls = []
  if(props.mode === 'range' && props.rangeStyle === 'connected' && valueState.value.length >= 2){
    if(inRangeMid(d.str)){
      cls.push('is-range-mid-cell')
    }
    if(isRangeStart(d.str)){
      cls.push('is-range-start-cell')
    }
    if(isRangeEnd(d.str)){
      cls.push('is-range-end-cell')
    }
  }
  return cls.join(' ')
}

function dayNoteColor(d){
  if(!d) return props.noteColor
  if(d.other) return props.disabledText
  if(d.disabled) return props.disabledText
  if(props.mode === 'range'){
    if(isRangeEdge(d.str)) return '#fff'
    if(inRangeMid(d.str)) return props.primary
  }else{
    if(inSelected(d.str)) return '#fff'
  }
  return props.noteColor
}

/** 动态计算 note 样式：超过2个字就缩小，使用 scale 突破 12px 限制 */
function noteStyle(it, d){
  const textLen = (it.text || '').length
  const color = it.color || dayNoteColor(d)

  // 基础字体大小
  let baseFontSize = typeof props.noteFontSize === 'number' ? props.noteFontSize : 20

  // 根据字数调整字体大小
  let fontSize = baseFontSize
  let scale = 1

  if(textLen > 2){
    // 超过2个字，每多一个字缩小 3rpx（更激进）
    fontSize = baseFontSize - (textLen - 2) * 3

    // 最小不低于 10rpx（通过 scale 实现）
    if(fontSize < 10){
      fontSize = 10
    }

    // 如果小于 24rpx (约12px)，使用 scale 突破限制
    if(fontSize < 24){
      scale = fontSize / 24
      fontSize = 24 // 保持在 24rpx，用 scale 缩小
    }
  }

  const style = {
    color,
    fontSize: fontSize + 'rpx',
    transformOrigin: 'center center'
  }

  // 只在需要缩放时添加 transform
  if(scale < 1){
    style.transform = `scale(${scale})`
  }

  return style
}


/** 外部注入：日期下方文字 / 角标（提前声明，避免 TDZ） */
const _labelFn = ref(null) // setNotes/setLabels
const _badgeFn = ref(null) // setBadges

function setNotes(fn){ _labelFn.value = fn; refreshMarks() }
function setLabels(fn){ setNotes(fn) } // 兼容旧名字
function setBadges(fn){ _badgeFn.value = fn; refreshMarks() }

/** ---------- state ---------- */
const todayStr = (() => {
  const t = new Date()
  return toDateStr(t.getFullYear(), t.getMonth()+1, t.getDate())
})()

const valueState = ref(normalizeValue(props.modelValue))

watch(() => props.modelValue, (v) => {
  valueState.value = normalizeValue(v)
  syncBaseToValue()
}, { deep: true })

function normalizeValue(v){
  const m = props.mode
  if(m === 'single'){
    const s = typeof v === 'string' ? v : ''
    return s ? [s] : []
  }
  if(Array.isArray(v)) return v.slice()
  return []
}

/** base month: current visible month */
const base = reactive({ y: 0, m: 0 })

const weekNames = computed(() => {
  const cn = ['日','一','二','三','四','五','六']
  if(props.weekStart === 1){
    return ['一','二','三','四','五','六','日']
  }
  return cn
})

const wrapWidth = computed(() => {
  if(!props.width || +props.width === 0) return '100%'
  return (typeof props.width === 'number' ? props.width + 'rpx' : props.width)
})

const months = ref([]) // [{key, y,m, days:[]}]
const swiperIndex = ref(1) // middle is current
function rebuildMonths(){
  const cur = { y: base.y, m: base.m }
  const prev = addMonths(cur.y, cur.m, -1)
  const next = addMonths(cur.y, cur.m, 1)
  months.value = [
    buildMonth(prev.y, prev.m),
    buildMonth(cur.y, cur.m),
    buildMonth(next.y, next.m),
  ]
  swiperIndex.value = 1
  applyMarks(months.value)
}

function syncBaseToValue(){
  const v = valueState.value
  const seed = (v && v.length) ? v[0] : todayStr
  const p = parseYMD(seed) || parseYMD(todayStr)
  base.y = p.y
  base.m = p.m
  rebuildMonths()
  emitPanel()
}

// 初始化：把 base/月数据与 v-model 对齐
syncBaseToValue()

function buildMonth(y,m){
  const key = toKey(y,m)
  const firstW = weekday(y,m,1)
  const offset = props.weekStart === 1 ? ((firstW+6)%7) : firstW
  const dim = daysInMonth(y,m)
  const cells = []
  // prev month filler
  const pm = addMonths(y,m,-1)
  const pdim = daysInMonth(pm.y, pm.m)
  for(let i=0;i<offset;i++){
    const d = pdim - offset + 1 + i
    const ds = toDateStr(pm.y, pm.m, d)
    cells.push(makeCell(pm.y, pm.m, d, ds, true))
  }
  // current month days
  for(let d=1; d<=dim; d++){
    const ds = toDateStr(y,m,d)
    cells.push(makeCell(y,m,d,ds,false))
  }
  // next month filler to complete 6 weeks(42)
  const need = 42 - cells.length
  const nm = addMonths(y,m,1)
  for(let d=1; d<=need; d++){
    const ds = toDateStr(nm.y, nm.m, d)
    cells.push(makeCell(nm.y, nm.m, d, ds, true))
  }
  return { key, y, m, days: cells }
}

function makeCell(y,m,d,ds,other){
  const disabled = ds < props.minDate || ds > props.maxDate
  return {
    y,m,day:d,
    str: ds,
    other,
    disabled,
    lunar: props.showLunar ? lunarText(y,m,d) : '',
    sub: (ds === todayStr) ? '今天' : '',
    badge: false, // 可由 setBadges 注入
    note: '' // 可由 notes/setLabels 注入
  }
}

const displayTitle = computed(() => `${base.y}年${pad2(base.m)}月`)

function emitPanel(){
  emit('panel-change', { year: base.y, month: base.m, ym: toKey(base.y, base.m) })
}

function stepMonth(delta){
  const n = addMonths(base.y, base.m, delta)
  base.y = n.y; base.m = n.m
  rebuildMonths()
  emitPanel()
}
function stepYear(delta){
  base.y += delta
  rebuildMonths()
  emitPanel()
}
function onSwiperChange(e){
  const cur = e.detail.current
  if(cur === swiperIndex.value) return
  if(cur === 0){
    stepMonth(-1)
  }else if(cur === 2){
    stepMonth(1)
  }
}

function inSelected(ds){
  const v = valueState.value
  const m = props.mode
  if(m === 'single') return v[0] === ds
  if(m === 'multiple') return v.includes(ds)
  if(m === 'range'){
    if(v.length < 2) return v[0] === ds
    const a = v[0], b = v[1]
    return ds >= a && ds <= b
  }
  return false
}
function isRangeEdge(ds){
  const v = valueState.value
  if(props.mode !== 'range' || v.length < 1) return false
  if(v[0] === ds) return true
  if(v.length >= 2 && v[1] === ds) return true
  return false
}

function inRangeMid(ds){
  const v = valueState.value
  if(props.mode !== 'range' || v.length < 2) return false
  const a = v[0], b = v[1]
  return ds > a && ds < b
}

function dayClass(d){
  const cls = []
  if(d.other) cls.push('is-other')
  if(d.disabled) cls.push('is-disabled')
  if(props.mode === 'range'){
    if(inSelected(d.str)) cls.push('is-range')
    if(inRangeMid(d.str)) cls.push('is-range-mid')
    if(isRangeEdge(d.str)) cls.push('is-range-edge')
    // connected 样式类
    if(props.rangeStyle === 'connected'){
      cls.push('is-range-connected')
      if(isRangeStart(d.str)) cls.push('is-range-start')
      if(isRangeEnd(d.str)) cls.push('is-range-end')
    }
  }else{
    if(inSelected(d.str)) cls.push('is-selected')
  }
  if(d.str === todayStr) cls.push('is-today')
  return cls.join(' ')
}

// 判断是否是区间开始
function isRangeStart(ds){
  const v = valueState.value
  if(props.mode !== 'range' || v.length < 1) return false
  return v[0] === ds
}

// 判断是否是区间结束
function isRangeEnd(ds){
  const v = valueState.value
  if(props.mode !== 'range' || v.length < 2) return false
  return v[1] === ds
}

function dayStyle(d){
  const radiusVal = (typeof props.cellRadius === 'number' ? props.cellRadius + 'rpx' : (props.cellRadius || '18rpx'))
  const baseStyle = {
    borderRadius: radiusVal,
    height: (typeof props.cellHeight === 'number' ? props.cellHeight + 'rpx' : (props.cellHeight || '88rpx')),
  }
  if(!d) return baseStyle
  if(d.disabled) return baseStyle
  // range: endpoints strong, middle light
  if(props.mode === 'range'){
    // connected 样式：浅色背景设置在 day 上，高度一致
    if(props.rangeStyle === 'connected' && valueState.value.length >= 2){
      if(isRangeStart(d.str)){
        return { ...baseStyle, background: props.primary, borderRadius: radiusVal }
      }
      if(isRangeEnd(d.str)){
        return { ...baseStyle, background: props.primary, borderRadius: radiusVal }
      }
      if(inRangeMid(d.str)){
        // 中间浅色背景设置在 day 上
        return { ...baseStyle, borderRadius: '0', background: primaryLight.value }
      }
    } else {
      // gap 样式（默认）
      if(isRangeEdge(d.str)) return { ...baseStyle, background: props.primary }
      if(inRangeMid(d.str)) return { ...baseStyle, background: primaryLight.value }
    }
    if(d.str === todayStr) return { ...baseStyle, background: primaryLighter.value }
    return baseStyle
  }
  // single/multiple
  if(inSelected(d.str)) return { ...baseStyle, background: props.primary }
  if(d.str === todayStr) return { ...baseStyle, background: primaryLighter.value }
  return baseStyle
}

function dayNumColor(d){
  if(!d) return props.text
  if(d.other) return props.disabledText
  if(d.disabled) return props.disabledText
  if(props.mode === 'range'){
    if(isRangeEdge(d.str)) return '#fff'
    if(inRangeMid(d.str)) return props.primary
  }else{
    if(inSelected(d.str)) return '#fff'
  }
  return props.text
}

function daySubColor(d){
  if(!d) return props.subText
  if(d.other) return props.disabledText
  if(d.disabled) return props.disabledText
  if(props.mode === 'range'){
    if(isRangeEdge(d.str)) return '#fff'
    if(inRangeMid(d.str)) return props.primary
  }else{
    if(inSelected(d.str)) return '#fff'
  }
  return props.subText
}

function tryEmitChange(){
  const out = getEmitValue()
  emit('update:modelValue', out)
  emit('change', out)
}

function getEmitValue(){
  const m = props.mode
  const v = valueState.value.slice()
  if(m === 'single') return v[0] || ''
  return v
}

function onPick(d){
  if(!d || d.disabled) return
  const ds = d.str
  const m = props.mode

  if(m === 'single'){
    valueState.value = [ds]
    tryEmitChange()
    // ✅ 组件本身不负责“消失/关闭”，交给外部弹窗
    if(!props.confirmable) emit('confirm', getEmitValue())
    return
  }

  if(m === 'multiple'){
    const list = valueState.value.slice()
    const idx = list.indexOf(ds)
    if(idx >= 0) list.splice(idx,1)
    else list.push(ds)
    list.sort()
    // maxDays
    const md = +props.maxDays
    if(md > 0 && list.length > md) return
    valueState.value = list
    tryEmitChange()
    return
  }

  if(m === 'range'){
    const list = valueState.value.slice()
    if(list.length === 0){
      valueState.value = [ds]
    }else if(list.length === 1){
      const a = list[0]
      const b = ds
      let range = (a <= b) ? [a,b] : [b,a]
      const md = +props.maxDays
      if(md > 0){
        const days = diffDays(range[0], range[1]) + 1
        if(days > md){
          // 超过最大天数，自动调整到最大值
          const startDate = parseYMD(range[0])
          const endDate = new Date(startDate.y, startDate.m - 1, startDate.d)
          endDate.setDate(endDate.getDate() + md - 1)
          const adjustedEnd = toDateStr(endDate.getFullYear(), endDate.getMonth() + 1, endDate.getDate())
          range = [range[0], adjustedEnd]
          // 触发提示事件
          emit('max-days-exceeded', { maxDays: md, requestedDays: days, adjusted: range })
          // 显示提示（可通过 uni.showToast）
          if(typeof uni !== 'undefined' && uni.showToast){
            uni.showToast({ title: `最多选择${md}天`, icon: 'none', duration: 1500 })
          }
        }
      }
      valueState.value = range
    }else{
      valueState.value = [ds]
    }
    tryEmitChange()
    return
  }
}

function diffDays(a,b){
  const pa = parseYMD(a), pb = parseYMD(b)
  if(!pa || !pb) return 0
  const da = new Date(pa.y, pa.m-1, pa.d).getTime()
  const db = new Date(pb.y, pb.m-1, pb.d).getTime()
  return Math.round((db-da)/86400000)
}

const tipText = computed(() => {
  const m = props.mode
  const v = valueState.value
  if(m === 'single') return v[0] ? `已选：${v[0]}` : '请选择日期'
  if(m === 'multiple') return v.length ? `已选 ${v.length} 天` : '可多选日期'
  if(m === 'range'){
    if(v.length === 0) return '请选择开始日期'
    if(v.length === 1) return `开始：${v[0]}`
    return `区间：${v[0]} ~ ${v[1]}`
  }
  return ''
})

function onClear(){
  valueState.value = []
  tryEmitChange()
  emit('clear')
}
function onConfirm(){
  emit('confirm', getEmitValue())
}

function normalizeNoteVal(v){
  // return Array<{text:string,color?:string}>
  if(v == null) return []
  // string/number
  if(typeof v === 'string' || typeof v === 'number'){
    const t = String(v)
    return t.length ? [{ text: t }] : []
  }
  // object {text,color}
  if(typeof v === 'object' && !Array.isArray(v)){
    const t = v.text != null ? String(v.text) : ''
    if(!t.length) return []
    const it = { text: t }
    if(v.color) it.color = String(v.color)
    if(v.badge !== undefined) it.badge = v.badge  // 支持 badge 属性
    return [it]
  }
  // array
  if(Array.isArray(v)){
    const out = []
    for(const item of v){
      out.push(...normalizeNoteVal(item))
    }
    return out
  }
  return []
}

function getNoteItems(ds, d){
  // 1) 外部 setNotes(fn) / setLabels(fn)
  if(_labelFn.value){
    const v = _labelFn.value(ds, d)
    const arr = normalizeNoteVal(v)
    if(arr.length) return arr
  }
  // 2) prop noteFn
  if(props.noteFn){
    const v = props.noteFn(ds, d)
    const arr = normalizeNoteVal(v)
    if(arr.length) return arr
  }
  // 3) notes map
  if(props.notes && Object.prototype.hasOwnProperty.call(props.notes, ds)){
    const v = props.notes[ds]
    const arr = normalizeNoteVal(v)
    if(arr.length) return arr
  }
  // 4) 今日兜底（仅 showLunar 时显示“今天”）
  if(props.showLunar && props.showTodayNoteWhenLunar && ds === todayStr){
    return [{ text: '今天' }]
  }
  return []
}

function applyMarks(list){
  if(!list || !list.length) return
  list.forEach(mm => {
    mm.days.forEach(d => {
      // sub：非农历时显示"今天"
      d.sub = (!props.showLunar && d.str === todayStr) ? '今天' : ''
      // note：外部注入 + map + 今日兜底
      d.notes = getNoteItems(d.str, d)
      d.note = d.notes && d.notes.length ? d.notes[0].text : ''

      // badge 优先级：1. notes 中的 badge  2. _badgeFn  3. false
      let badgeFromNotes = null
      if(d.notes && d.notes.length){
        for(const note of d.notes){
          if(note.badge){
            badgeFromNotes = note.badge
            break
          }
        }
      }

      if(badgeFromNotes){
        // 从 notes 中获取 badge
        if(typeof badgeFromNotes === 'object'){
          d.badge = { ...badgeFromNotes }
        } else {
          d.badge = { icon: '' }
        }
      } else if(_badgeFn.value){
        const badgeVal = _badgeFn.value(d.str)
        if(badgeVal){
          if(typeof badgeVal === 'object'){
            d.badge = { ...badgeVal }
          } else {
            d.badge = { icon: '' }
          }
        } else {
          d.badge = false
        }
      } else {
        d.badge = false
      }
    })
  })
}

function refreshMarks(){
  applyMarks(months.value)
}

defineExpose({ setNotes, setLabels, setBadges })

</script>

<style>
.zdp-wrap{
  border-radius: 18rpx;
  overflow: hidden;
}
.zdp-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 18rpx 16rpx 12rpx;
}
.zdp-nav{ display:flex; gap: 10rpx; }
.zdp-btn{
  width: 64rpx; height: 56rpx;
  display:flex; align-items:center; justify-content:center;
  border-radius: 14rpx;
  background: rgba(0,0,0,0.04);
  color:#333;
  font-size: 34rpx;
}
.zdp-title{ flex:1; text-align:center; }
.zdp-title-main{ font-size: 34rpx; font-weight: 600; color:#181818; }
.zdp-title-sub{ display:block; margin-top: 6rpx; font-size: 24rpx; color:#8a8a8a; }

.zdp-week{
  display:flex;
  padding: 8rpx 10rpx 10rpx;
  border-bottom-width: 1px;
  border-bottom-style: solid;
}
.zdp-week-item{
  width: 14.2857%;
  text-align:center;
  font-size: 26rpx;
  color:#666;
}

.zdp-swiper{ height: 620rpx; }
.zdp-grid{
  display:flex;
  flex-wrap:wrap;
  padding: 10rpx 10rpx 0;
}
.zdp-cell{ width: 14.2857%; padding: 10rpx 0; display:flex; justify-content:center; }
.zdp-day{
  width: 86rpx;
  height: 88rpx;
  border-radius: 18rpx;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  position:relative;
}
.zdp-day-num{ font-size: 30rpx; color:#181818; line-height: 34rpx; }
.zdp-day-sub{ font-size: 20rpx; color:#8a8a8a; margin-top: 2rpx; line-height: 20rpx; }
.zdp-day-notes{
  text-align: center;
  width: 100%;
  line-height: 18rpx;
  margin-top: 0;
}
.zdp-day-note{
  font-size: 20rpx;
  line-height: 20rpx;
  display: inline-block;
  transform: scale(0.85);
}

.zdp-day.is-disabled{ opacity: 0.35; }
.zdp-day.is-other{ visibility: hidden; }

.zdp-badge{
  position:absolute;
  right: -4rpx;
  top: -4rpx;
  width: 10rpx;
  height: 10rpx;
  border-radius: 999rpx;
  background: #ff3b30;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 有 icon 时扩大尺寸 */
.zdp-badge--icon{
  width: auto;
  height: auto;
  min-width: 24rpx;
  min-height: 24rpx;
  padding: 0;
  background: transparent;
  right: -8rpx;
  top: -8rpx;
}

.zdp-badge-icon{
  font-size: 24rpx;
  line-height: 1;
}

.zdp-foot{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 14rpx 16rpx 18rpx;
  border-top: 1px solid #f0f0f0;
}
.zdp-foot-tip{ font-size: 24rpx; color:#666; }
.zdp-foot-right{ display:flex; gap: 12rpx; }
.zdp-action{
  padding: 14rpx 22rpx;
  border-radius: 16rpx;
  background: transparent;
  color:#fff;
  font-size: 26rpx;
}
.zdp-action-ghost{
  background: rgba(0,0,0,0.05);
  color:#333;
}

/* connected 模式：让中间浅色背景连续 */
.zdp-cell.is-range-mid-cell .zdp-day{
  width: 100%;
  border-radius: 0;
}

</style>
