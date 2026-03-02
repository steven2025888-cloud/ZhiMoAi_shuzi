<template>
  <view class="zsig" :style="wrapStyle">
    <view v-if="showToolbar" class="zsig__toolbar">
      <view class="zsig__group">
        <view class="zsig__pill" :class="{ 'is-active': !disabled }">
          <view class="zsig__dot" :style="{ background: currentColor }" />
          <text class="zsig__pillText">{{ disabled ? '只读' : '书写' }}</text>
        </view>

        <view class="zsig__colors">
          <view
            v-for="c in colorPresets"
            :key="c"
            class="zsig__color"
            :class="{ 'is-active': c === currentColor }"
            :style="{ background: c }"
            @tap="setColor(c)"
          />
        </view>
      </view>

      <view class="zsig__group">
        <view class="zsig__seg">
          <view class="zsig__segBtn" :class="{ 'is-active': penSize === 'thin' }" @tap="setPenSize('thin')">
            <text class="zsig__segText">细</text>
          </view>
          <view class="zsig__segBtn" :class="{ 'is-active': penSize === 'normal' }" @tap="setPenSize('normal')">
            <text class="zsig__segText">中</text>
          </view>
          <view class="zsig__segBtn" :class="{ 'is-active': penSize === 'bold' }" @tap="setPenSize('bold')">
            <text class="zsig__segText">粗</text>
          </view>
        </view>

        <view class="zsig__actions">
          <view class="zsig__btn" :class="{ 'is-disabled': !canUndo }" @tap="undo">
            <text class="zsig__btnText">撤销</text>
          </view>
          <view class="zsig__btn" :class="{ 'is-disabled': !canRedo }" @tap="redo">
            <text class="zsig__btnText">重做</text>
          </view>
          <view class="zsig__btn" :class="{ 'is-disabled': isEmpty }" @tap="clear">
            <text class="zsig__btnText">清空</text>
          </view>
          <view class="zsig__btn zsig__btn--primary" :class="{ 'is-disabled': isEmpty }" @tap="saveImage">
            <text class="zsig__btnText zsig__btnText--primary">保存图片</text>
          </view>
          <view class="zsig__btn zsig__btn--ghost" :class="{ 'is-disabled': isEmpty }" @tap="saveBase64">
            <text class="zsig__btnText">Base64</text>
          </view>
        </view>
      </view>
    </view>

    <view class="zsig__board" :class="{ 'is-disabled': disabled, 'is-borderless': !bordered }">
      <canvas
        class="zsig__canvas"
        :canvas-id="canvasId"
        :id="canvasId"
        :disable-scroll="!allowPageScrollWhileDrawing"
        @touchstart="onTouchStart"
        @touchmove="onTouchMove"
        @touchend="onTouchEnd"
        @touchcancel="onTouchEnd"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
        :style="canvasStyle"
      />

      <view v-if="showGuide && isEmpty" class="zsig__guide">
        <text class="zsig__guideText" :style="{ color: guideColor }">{{ guideText }}</text>
      </view>

      <view v-if="disabled && !isEmpty && showDisabledHint" class="zsig__readonlyTag">
        <text class="zsig__readonlyTagText">只读</text>
      </view>
    </view>

    <view v-if="showTips" class="zsig__tips">
      <text class="zsig__tipsText">{{ tipsText }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type Point = { x: number; y: number; t: number }
type StrokePoint = { x: number; y: number; t: number; w: number }
type Stroke = { color: string; points: StrokePoint[] }

const props = withDefaults(
  defineProps<{
    /** 画板宽度（支持 rpx/px/% 等，建议 rpx） */
    width?: string | number
    /** 画板高度（支持 rpx/px 等，建议 rpx） */
    height?: string | number
    /** 画板背景色 */
    background?: string
    /** 是否显示边框 */
    bordered?: boolean
    /** 圆角（rpx） */
    radius?: number
    /** 是否显示工具栏 */
    showToolbar?: boolean
    /** 是否只读 */
    disabled?: boolean
    /** 引导文案 */
    guideText?: string
    /** 引导文字颜色 */
    guideColor?: string
    /** 无内容时是否显示引导 */
    showGuide?: boolean
    /** 只读时右上角提示 */
    showDisabledHint?: boolean
    /** 底部提示 */
    showTips?: boolean
    tipsText?: string
    /** 默认笔色 */
    color?: string
    /** 颜色预设 */
    colors?: string[]
    /** 最小线宽 */
    minWidth?: number
    /** 最大线宽 */
    maxWidth?: number
    /** 固定线宽（设置后忽略 min/max 计算，单位 px） */
    strokeWidth?: number
    /** 是否开启可变线宽（速度影响线宽）。默认 false：线条更稳定、更像真实签名笔 */
    variableWidth?: boolean
    /** 笔触平滑（速度影响线宽） */
    smooth?: boolean
    /** 绘制时是否允许页面滚动（默认 false） */
    allowPageScrollWhileDrawing?: boolean
    /** 导出图片类型 */
    fileType?: 'png' | 'jpg'
    /** jpg 导出质量 */
    quality?: number
    /** 保存图片时：App 端是否自动写入相册 */
    autoSaveToAlbum?: boolean
    /** 保存图片时：H5 端是否自动触发下载 */
    autoDownloadH5?: boolean
    /** H5 下载文件名（默认 signature.png） */
    downloadFileName?: string
    /** 是否显示保存成功/失败提示 */
    showSaveToast?: boolean
  }>(),
  {
    width: '690rpx',
    height: '360rpx',
    background: '#FFFFFF',
    bordered: true,
    radius: 28,
    showToolbar: false,
    disabled: false,
    guideText: '在此签名',
    guideColor: '#C7C7CC',
    showGuide: true,
    showDisabledHint: true,
    showTips: false,
    tipsText: '提示：写不下可横向书写，点击“保存”导出图片',
    color: '#111111',
    colors: () => ['#111111', '#0A84FF', '#34C759', '#FF9F0A', '#FF3B30'],
    minWidth: 2,
    maxWidth: 8,
    strokeWidth: 0,
    variableWidth: false,
    smooth: true,
    allowPageScrollWhileDrawing: false,
    fileType: 'png',
    quality: 0.92,
    autoSaveToAlbum: true,
    autoDownloadH5: true,
    downloadFileName: 'signature.png',
    showSaveToast: true
  }
)

const emit = defineEmits<{
  (e: 'change', v: { isEmpty: boolean; strokes: number }): void
  (e: 'save', v: { tempFilePath: string; type: 'image' }): void
  (e: 'saveBase64', v: { base64: string; dataUrl: string; tempFilePath?: string; type: 'base64' }): void
  (e: 'start'): void
  (e: 'end'): void
}>()

const ins = getCurrentInstance()
const canvasId = `zsig_${Math.random().toString(16).slice(2)}`
const ctx = ref<UniApp.CanvasContext | null>(null)

const boardW = ref(0)
const boardH = ref(0)
const boardLeft = ref(0)
const boardTop = ref(0)

const strokes = ref<Stroke[]>([])
const redoStack = ref<Stroke[]>([])

const drawing = ref(false)
const lastPoint = ref<Point | null>(null)
const lastWidth = ref<number>(props.maxWidth)
const lastVelocity = ref<number>(0)

// 当前笔画已渲染到的点数量（用于合并绘制，减少断笔）
let renderedCount = 0
let lastDrawAt = 0

const currentColor = ref(props.color)
watch(
  () => props.color,
  (v) => (currentColor.value = v || '#111111')
)

const colorPresets = computed(() => (props.colors?.length ? props.colors : ['#111111']))

const isEmpty = computed(() => strokes.value.length === 0)
const canUndo = computed(() => strokes.value.length > 0)
const canRedo = computed(() => redoStack.value.length > 0)

const penSize = ref<'thin' | 'normal' | 'bold'>('normal')
watch(
  () => [props.minWidth, props.maxWidth],
  () => {
    // 仅重置基准，不改用户选项
    lastWidth.value = clamp(props.maxWidth, 1, 60)
  }
)

const wrapStyle = computed(() => {
  const r = `${props.radius}rpx`
  return {
    '--zsig-radius': r,
    '--zsig-bg': props.background
  } as Record<string, string>
})

const canvasStyle = computed(() => {
  // canvas 只负责占位；真实像素尺寸通过 boundingClientRect 获取
  const w = typeof props.width === 'number' ? `${props.width}px` : props.width
  const h = typeof props.height === 'number' ? `${props.height}px` : props.height
  return `width:${w};height:${h};`
})

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n))
}

function dist(a: Point, b: Point) {
  const dx = a.x - b.x
  const dy = a.y - b.y
  return Math.sqrt(dx * dx + dy * dy)
}

function getTouchPoint(e: any): Point | null {
  const t = e?.touches?.[0] || e?.changedTouches?.[0]
  if (!t) return null

  let x: number | undefined
  let y: number | undefined

  // uni-app 不同平台的坐标系统不同：
  // - App/小程序：t.x 和 t.y 可能已经是相对于组件的坐标
  // - H5：需要使用 clientX/clientY 并减去canvas偏移

  // 优先尝试 x/y（App/小程序）
  if (t.x != null && t.y != null) {
    // App端：直接使用，不减去偏移（已经是相对坐标）
    x = t.x
    y = t.y
  }
  // H5 或其他情况
  else if (t.clientX != null && t.clientY != null) {
    // H5: 需要减去canvas偏移
    x = t.clientX - boardLeft.value
    y = t.clientY - boardTop.value
  }
  else if (t.pageX != null && t.pageY != null) {
    // 备用：减去canvas偏移
    x = t.pageX - boardLeft.value
    y = t.pageY - boardTop.value
  }

  if (x == null || y == null) return null
  return { x, y, t: Date.now() }
}

function getMousePoint(e: MouseEvent): Point | null {
  // @ts-ignore: uni h5 canvas mouse event has offsetX/offsetY
  let x = (e as any).offsetX ?? (e as any).x
  // @ts-ignore
  let y = (e as any).offsetY ?? (e as any).y
  
  // 如果 offsetX/offsetY 不可用，使用 clientX/clientY 并减去 canvas 偏移
  if (x == null || y == null) {
    const clientX = (e as any).clientX
    const clientY = (e as any).clientY
    if (clientX != null && clientY != null) {
      x = clientX - boardLeft.value
      y = clientY - boardTop.value
    }
  }
  
  if (x == null || y == null) return null
  return { x, y, t: Date.now() }
}

function ensureContext() {
  if (ctx.value) return ctx.value
  const proxy = ins?.proxy as any
  ctx.value = uni.createCanvasContext(canvasId, proxy)
  return ctx.value
}

async function measureBoard() {
  await nextTick()
  return new Promise<void>((resolve) => {
    const proxy = ins?.proxy as any
    uni
      .createSelectorQuery()
      .in(proxy)
      .select('.zsig__canvas')
      .boundingClientRect((rect: any) => {
        boardW.value = Math.max(0, Math.floor(rect?.width || 0))
        boardH.value = Math.max(0, Math.floor(rect?.height || 0))
        boardLeft.value = rect?.left || 0
        boardTop.value = rect?.top || 0
        console.log('[z-signature] measureBoard', {
          width: boardW.value,
          height: boardH.value,
          left: boardLeft.value,
          top: boardTop.value,
          rect
        })
        resolve()
      })
      .exec()
  })
}

function resetCanvasBackground() {
  const c = ensureContext()
  c.setFillStyle(props.background)
  c.fillRect(0, 0, boardW.value, boardH.value)
  c.draw(false)
}

function redrawAll() {
  const c = ensureContext()
  c.clearRect(0, 0, boardW.value, boardH.value)
  c.setFillStyle(props.background)
  c.fillRect(0, 0, boardW.value, boardH.value)

  for (const s of strokes.value) {
    drawStroke(c, s, false)
  }
  c.draw(false)
}

function drawStroke(c: UniApp.CanvasContext, stroke: Stroke, doDraw = true) {
  const pts = stroke.points
  if (!pts.length) return

  c.setStrokeStyle(stroke.color)
  c.setLineCap('round')
  c.setLineJoin('round')

  // 单点：画一个小点
  if (pts.length === 1) {
    const p = pts[0]
    c.setLineWidth(p.w)
    c.beginPath()
    c.moveTo(p.x, p.y)
    c.lineTo(p.x + 0.01, p.y + 0.01)
    c.stroke()
    if (doDraw) c.draw(true)
    return
  }

  // 固定线宽：一次性绘制整条路径（更连续、更稳定）
  const isVariable = !!props.variableWidth && props.smooth
  if (!isVariable) {
    const w = pts[0].w
    c.setLineWidth(w)
    c.beginPath()
    c.moveTo(pts[0].x, pts[0].y)

    for (let i = 1; i < pts.length - 1; i++) {
      const p1 = pts[i]
      const p2 = pts[i + 1]
      const midX = (p1.x + p2.x) / 2
      const midY = (p1.y + p2.y) / 2
      c.quadraticCurveTo(p1.x, p1.y, midX, midY)
    }
    const last = pts[pts.length - 1]
    c.lineTo(last.x, last.y)
    c.stroke()
    if (doDraw) c.draw(true)
    return
  }

  // 可变线宽：分段绘制（避免一次 path 中无法改变 lineWidth）
  for (let i = 1; i < pts.length; i++) {
    const p0 = pts[i - 1]
    const p1 = pts[i]
    c.setLineWidth(p1.w)
    c.beginPath()
    c.moveTo(p0.x, p0.y)
    c.lineTo(p1.x, p1.y)
    c.stroke()
  }
  if (doDraw) c.draw(true)
}

function startStroke(p: Point) {
  if (props.disabled) return
  console.log('[z-signature] startStroke', { point: p, color: currentColor.value })
  drawing.value = true
  redoStack.value = []
  lastPoint.value = p
  lastVelocity.value = 0

  const fixed = resolveFixedWidth()
  lastWidth.value = fixed
  renderedCount = 1
  lastDrawAt = Date.now()

  strokes.value.push({
    color: currentColor.value,
    points: [{ x: p.x, y: p.y, t: p.t, w: fixed }]
  })
  console.log('[z-signature] stroke added, total strokes:', strokes.value.length)
  emit('start')
}

function resolveFixedWidth() {
  const sw = Number(props.strokeWidth || 0)
  if (sw > 0) return clamp(sw, 0.5, 60)
  return clamp(resolveBaseWidth(), props.minWidth, props.maxWidth)
}

function resolveBaseWidth() {
  const maxW = clamp(props.maxWidth, 1, 60)
  if (penSize.value === 'thin') return Math.max(props.minWidth, maxW * 0.55)
  if (penSize.value === 'bold') return Math.max(props.minWidth, maxW * 1.25)
  return maxW
}

function drawPendingSegments(force = false) {
  const c = ensureContext()
  const s = strokes.value[strokes.value.length - 1]
  if (!s) return
  const pts = s.points
  if (pts.length < 2) return

  const now = Date.now()
  // 合并绘制：在部分机型上频繁 draw(true) 会导致"断笔"
  if (!force && now - lastDrawAt < 14) return

  console.log('[z-signature] drawPendingSegments', {
    force,
    pointsCount: pts.length,
    renderedCount,
    color: s.color,
    firstPoint: pts[0],
    lastPoint: pts[pts.length - 1]
  })

  const variable = !!props.variableWidth && props.smooth

  c.setStrokeStyle(s.color)
  c.setLineCap('round')
  c.setLineJoin('round')

  const start = Math.max(1, renderedCount - 1)
  const end = pts.length - 1
  if (end < start) return

  for (let i = start; i <= end; i++) {
    // 宽度：固定更稳定；可变时用相邻点平均，减少突变
    if (!variable) {
      c.setLineWidth(pts[0].w)
    } else {
      const w = (pts[i - 1].w + pts[i].w) / 2
      c.setLineWidth(w)
    }

    if (i === 1) {
      const p0 = pts[0]
      const p1 = pts[1]
      c.beginPath()
      c.moveTo(p0.x, p0.y)
      c.lineTo(p1.x, p1.y)
      c.stroke()
      continue
    }

    const p0 = pts[i - 2]
    const p1 = pts[i - 1]
    const p2 = pts[i]

    const m1x = (p0.x + p1.x) / 2
    const m1y = (p0.y + p1.y) / 2
    const m2x = (p1.x + p2.x) / 2
    const m2y = (p1.y + p2.y) / 2

    c.beginPath()
    c.moveTo(m1x, m1y)
    c.quadraticCurveTo(p1.x, p1.y, m2x, m2y)
    c.stroke()
  }

  c.draw(true)
  console.log('[z-signature] draw called')
  renderedCount = pts.length
  lastDrawAt = now
}

function updateStroke(p: Point) {
  if (!drawing.value || props.disabled) return
  const lp = lastPoint.value
  if (!lp) return

  const d = dist(p, lp)
  console.log('[z-signature] updateStroke', { point: p, lastPoint: lp, distance: d })
  if (d < 0.1) return // 过滤抖动（过大会"断笔"）

  const variable = !!props.variableWidth && props.smooth
  let w = lastWidth.value

  if (variable) {
    const dt = Math.max(1, p.t - lp.t)
    const v = d / dt // px/ms

    const baseMax = clamp(resolveBaseWidth(), 1, 60)
    const minW = clamp(props.minWidth, 0.5, baseMax)

    // 速度越快线越细：降低系数 + 更慢的宽度变化，避免"忽粗忽细"
    const filteredV = lastVelocity.value * 0.75 + v * 0.25
    lastVelocity.value = filteredV

    const targetW = clamp(baseMax - filteredV * 10, minW, baseMax)
    w = lastWidth.value * 0.8 + targetW * 0.2
    lastWidth.value = w
  } else {
    // 固定线宽：签名更稳、更一致
    w = resolveFixedWidth()
    lastWidth.value = w
  }

  lastPoint.value = p

  const s = strokes.value[strokes.value.length - 1]
  s.points.push({ x: p.x, y: p.y, t: p.t, w })

  drawPendingSegments(false)
}

function endStroke() {
  if (!drawing.value) return
  // 确保把最后积攒的段落一次画完
  drawPendingSegments(true)

  drawing.value = false
  lastPoint.value = null
  emit('end')
  emit('change', { isEmpty: isEmpty.value, strokes: strokes.value.length })
}

function setColor(c: string) {
  if (props.disabled) return
  currentColor.value = c
}
function setPenSize(v: 'thin' | 'normal' | 'bold') {
  if (props.disabled) return
  penSize.value = v
}

function clear() {
  if (props.disabled) return
  if (strokes.value.length === 0) return
  strokes.value = []
  redoStack.value = []
  renderedCount = 0
  lastDrawAt = 0
  renderedCount = 0
  lastDrawAt = 0
  redrawAll()
  emit('change', { isEmpty: true, strokes: 0 })
}

function undo() {
  if (props.disabled) return
  if (!canUndo.value) return
  const s = strokes.value.pop()
  if (s) redoStack.value.push(s)
  renderedCount = 0
  lastDrawAt = 0
  redrawAll()
  emit('change', { isEmpty: isEmpty.value, strokes: strokes.value.length })
}

function redo() {
  if (props.disabled) return
  if (!canRedo.value) return
  const s = redoStack.value.pop()
  if (s) strokes.value.push(s)
  renderedCount = 0
  lastDrawAt = 0
  redrawAll()
  emit('change', { isEmpty: isEmpty.value, strokes: strokes.value.length })
}


async function canvasToTempFilePathAsync(): Promise<string> {
  const proxy = ins?.proxy as any
  return new Promise((resolve, reject) => {
    // 兼容：确保已绘制背景（flush）
    ensureContext().draw(true, () => {
      uni.canvasToTempFilePath(
        {
          canvasId,
          fileType: props.fileType,
          quality: props.fileType === 'jpg' ? props.quality : undefined,
          success(res) {
            resolve(res.tempFilePath)
          },
          fail(err) {
            reject(err)
          }
        },
        proxy
      )
    })
  })
}

async function filePathToBase64(filePath: string): Promise<{ base64: string; dataUrl: string }> {
  // App / 小程序：优先用 FileSystemManager 读取
  const fsm = (uni as any).getFileSystemManager?.()
  if (fsm?.readFile) {
    return new Promise((resolve, reject) => {
      fsm.readFile({
        filePath,
        encoding: 'base64',
        success(r: any) {
          const base64 = (r?.data || '') as string
          const dataUrl = `data:image/${props.fileType};base64,${base64}`
          resolve({ base64, dataUrl })
        },
        fail(e: any) {
          reject(e)
        }
      })
    })
  }

  // H5 兜底：fetch -> Blob -> FileReader
  return new Promise((resolve, reject) => {
    try {
      fetch(filePath)
        .then((res) => res.blob())
        .then((blob) => {
          const reader = new FileReader()
          reader.onload = () => {
            const dataUrl = String(reader.result || '')
            const base64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : ''
            resolve({ base64, dataUrl })
          }
          reader.onerror = () => reject(new Error('FileReader failed'))
          reader.readAsDataURL(blob)
        })
        .catch(reject)
    } catch (e) {
      reject(e)
    }
  })
}

async function save(type: 'image' | 'base64' | 'both' = 'image') {
  if (isEmpty.value) return

  try {
    const tempFilePath = await canvasToTempFilePathAsync()

    if (type === 'image' || type === 'both') {
      emit('save', { tempFilePath, type: 'image' })
    }

    if (type === 'base64' || type === 'both') {
      const { base64, dataUrl } = await filePathToBase64(tempFilePath)
      emit('saveBase64', { base64, dataUrl, tempFilePath, type: 'base64' })
    }

    return tempFilePath
  } catch (e) {
    // 静默失败：交给外部处理
    // console.warn('[z-signature] save failed', e)
  }
}

/** H5 下载 */
// #ifdef H5
function dataURLToBlob(dataUrl: string) {
  const parts = dataUrl.split(',')
  const header = parts[0] || ''
  const data = parts[1] || ''
  const mime = (header.match(/:(.*?);/) || [])[1] || 'image/png'
  const bin = atob(data)
  const len = bin.length
  const u8 = new Uint8Array(len)
  for (let i = 0; i < len; i++) u8[i] = bin.charCodeAt(i)
  return new Blob([u8], { type: mime })
}

function triggerDownload(href: string, filename: string) {
  const a = document.createElement('a')
  a.href = href
  a.download = filename
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

async function downloadH5(src: string, filename: string) {
  const safeName = filename && filename.length ? filename : 'signature.png'
  const ua = navigator.userAgent || ''
  const isIOS = /iP(hone|ad|od)/i.test(ua)

  try {
    // iOS Safari 对 data: / download 支持很弱，走“打开图片页”兜底
    if (src.startsWith('data:image')) {
      if (isIOS) {
        const win = window.open('', '_blank')
        if (win) {
          win.document.title = safeName
          win.document.body.style.margin = '0'
          win.document.body.innerHTML = `<img src="${src}" style="display:block;max-width:100%;height:auto;margin:0 auto;" />`
        } else {
          window.location.href = src
        }
        return
      }
      const blob = dataURLToBlob(src)
      const url = URL.createObjectURL(blob)
      triggerDownload(url, safeName)
      setTimeout(() => URL.revokeObjectURL(url), 1500)
      return
    }

    // 先尝试直接下载（如果是 http(s)/blob: 一般可以）
    triggerDownload(src, safeName)

    // 再尝试 fetch->blob（部分浏览器/跨域场景更稳）
    const res = await fetch(src)
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    triggerDownload(url, safeName)
    setTimeout(() => URL.revokeObjectURL(url), 1500)
  } catch (e) {
    // 下载被限制时的兜底：打开图片页面（用户可长按/右键保存）
    try { window.open(src, '_blank') } catch (_) {}
    if (props.showSaveToast) {
      uni.showModal({
        title: '下载受限',
        content: '当前浏览器限制了自动下载。我已尝试为你打开图片页面，你可以长按（手机）或右键（电脑）保存图片。',
        showCancel: false
      })
    }
  }
}
// #endif

async function postProcessImage(tempFilePath: string) {
  if (!tempFilePath) return

  // App：写入系统相册
// #ifdef APP-PLUS
  if (props.autoSaveToAlbum) {
    try {
      await new Promise<void>((resolve, reject) => {
        uni.saveImageToPhotosAlbum({
          filePath: tempFilePath,
          success: () => resolve(),
          fail: (err) => reject(err)
        })
      })
      if (props.showSaveToast) uni.showToast({ title: '已保存到相册', icon: 'success' })
    } catch (e: any) {
      // 兜底：某些 App/机型上 uni.saveImageToPhotosAlbum 可能失败，尝试 plus.gallery.save
      try {
        const plusAny = (globalThis as any).plus
        if (plusAny && plusAny.gallery && typeof plusAny.gallery.save === 'function') {
          await new Promise<void>((resolve, reject) => {
            plusAny.gallery.save(
              tempFilePath,
              () => resolve(),
              (err: any) => reject(err)
            )
          })
          if (props.showSaveToast) uni.showToast({ title: '已保存到相册', icon: 'success' })
          return
        }
      } catch (_) {}

      if (props.showSaveToast) {
        uni.showModal({
          title: '保存失败',
          content: '请在系统设置中允许访问相册/照片权限后重试。',
          showCancel: false
        })
      }
    }
  }
// #endif

  // H5：触发下载
// #ifdef H5
  if (props.autoDownloadH5) {
    try {
      await downloadH5(tempFilePath, props.downloadFileName || 'signature.png')
      // 注：部分手机浏览器（尤其 iOS）无法强制弹下载，这里不强提示“已下载”
      if (props.showSaveToast) uni.showToast({ title: '已生成图片', icon: 'success' })
    } catch (e) {
      if (props.showSaveToast) uni.showToast({ title: '已生成图片', icon: 'none' })
    }
  }
// #endif
}

async function saveImage() {
  const tempFilePath = await save('image')
  if (!tempFilePath) return
  await postProcessImage(tempFilePath)
  return tempFilePath
}
function saveBase64() {
  return save('base64')
}
async function saveBoth() {
  const tempFilePath = await save('both')
  if (!tempFilePath) return
  await postProcessImage(tempFilePath)
  return tempFilePath
}

/** 对外暴露（可选） */
defineExpose({
  clear,
  undo,
  redo,
  save,
  saveImage,
  saveBase64,
  saveBoth,
  isEmpty: () => isEmpty.value,
  getStrokes: () => strokes.value
})


/** Touch handlers */
function onTouchStart(e: any) {
  // 阻止事件冒泡和默认行为（仅在方法存在时调用，兼容App端）
  if (typeof e?.stopPropagation === 'function') e.stopPropagation()
  if (typeof e?.preventDefault === 'function') e.preventDefault()

  if (props.disabled) return
  const p = getTouchPoint(e)
  console.log('[z-signature] touchStart', {
    raw: e?.touches?.[0],
    point: p,
    boardPos: { left: boardLeft.value, top: boardTop.value },
    boardSize: { w: boardW.value, h: boardH.value }
  })
  if (!p) return
  startStroke(p)
}
function onTouchMove(e: any) {
  // 阻止事件冒泡和默认行为（仅在方法存在时调用，兼容App端）
  if (typeof e?.stopPropagation === 'function') e.stopPropagation()
  if (typeof e?.preventDefault === 'function') e.preventDefault()

  if (props.disabled) return
  const p = getTouchPoint(e)
  if (!p) return
  updateStroke(p)
}
function onTouchEnd(e: any) {
  // 阻止事件冒泡（仅在方法存在时调用，兼容App端）
  if (typeof e?.stopPropagation === 'function') e.stopPropagation()

  console.log('[z-signature] touchEnd')
  endStroke()
}

/** Mouse handlers (H5) */
let mouseDown = false
function onMouseDown(e: any) {
  if (props.disabled) return
  
  // 确保 canvas 位置已经测量
  if (boardW.value === 0 || boardH.value === 0) {
    measureBoard().then(() => {
      mouseDown = true
      const p = getMousePoint(e)
      if (p) startStroke(p)
    })
    return
  }
  
  mouseDown = true
  const p = getMousePoint(e)
  if (!p) return
  startStroke(p)
}
function onMouseMove(e: any) {
  if (!mouseDown || props.disabled) return
  const p = getMousePoint(e)
  if (!p) return
  updateStroke(p)
}
function onMouseUp() {
  if (!mouseDown) return
  mouseDown = false
  endStroke()
}

/** init */
onMounted(async () => {
  await measureBoard()
  ensureContext()
  resetCanvasBackground()
})

watch(
  () => [props.width, props.height, props.background],
  async () => {
    await measureBoard()
    redrawAll()
  }
)

onBeforeUnmount(() => {
  ctx.value = null
})
</script>

<style scoped lang="scss">
.zsig {
  width: 100%;
}

.zsig__toolbar {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  margin-bottom: 14rpx;
}

.zsig__group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.zsig__pill {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 10rpx 14rpx;
  border-radius: 999rpx;
  background: rgba(142, 142, 147, 0.12);
}

.zsig__dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 999rpx;
}

.zsig__pillText {
  font-size: 24rpx;
  color: #1c1c1e;
  letter-spacing: 0.2rpx;
}

.zsig__colors {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 8rpx 10rpx;
  border-radius: 999rpx;
  background: rgba(142, 142, 147, 0.12);
}

.zsig__color {
  width: 22rpx;
  height: 22rpx;
  border-radius: 999rpx;
  border: 2rpx solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 4rpx 10rpx rgba(0, 0, 0, 0.08);
  transform: scale(1);
  transition: transform 0.12s ease;
}
.zsig__color.is-active {
  transform: scale(1.18);
  border-color: rgba(255, 255, 255, 1);
}

.zsig__seg {
  display: flex;
  background: rgba(142, 142, 147, 0.12);
  border-radius: 999rpx;
  padding: 6rpx;
}

.zsig__segBtn {
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
}
.zsig__segBtn.is-active {
  background: #ffffff;
  box-shadow: 0 10rpx 20rpx rgba(0, 0, 0, 0.06);
}
.zsig__segText {
  font-size: 24rpx;
  color: #1c1c1e;
}

.zsig__actions {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.zsig__btn {
  padding: 10rpx 16rpx;
  border-radius: 14rpx;
  background: rgba(142, 142, 147, 0.12);
}
.zsig__btn--primary {
  background: #0a84ff;
}

.zsig__btn--ghost{
  background: rgba(142, 142, 147, 0.10);
  border: 2rpx solid rgba(60, 60, 67, 0.18);
}
.zsig__btn.is-disabled {
  opacity: 0.45;
}

.zsig__btnText {
  font-size: 24rpx;
  color: #1c1c1e;
}
.zsig__btnText--primary {
  color: #ffffff;
  font-weight: 600;
}

.zsig__board {
  position: relative;
  border-radius: var(--zsig-radius);
  background: var(--zsig-bg);
  overflow: hidden;
  box-shadow: 0 16rpx 34rpx rgba(0, 0, 0, 0.06);
  border: 2rpx solid rgba(60, 60, 67, 0.12);
}

.zsig__board.is-borderless{
  border-color: transparent;
  box-shadow: none;
}

.zsig__board.is-disabled {
  opacity: 0.9;
}

.zsig__canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.zsig__guide {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}
.zsig__guideText {
  font-size: 28rpx;
  letter-spacing: 0.4rpx;
}

.zsig__readonlyTag {
  position: absolute;
  right: 16rpx;
  top: 16rpx;
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: rgba(0, 0, 0, 0.06);
}
.zsig__readonlyTagText {
  font-size: 22rpx;
  color: rgba(60, 60, 67, 0.72);
}

.zsig__tips {
  margin-top: 12rpx;
  padding: 10rpx 14rpx;
  border-radius: 16rpx;
  background: rgba(142, 142, 147, 0.12);
}
.zsig__tipsText {
  font-size: 24rpx;
  color: rgba(60, 60, 67, 0.82);
}
</style>
