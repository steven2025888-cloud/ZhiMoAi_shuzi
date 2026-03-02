<template>
  <view class="zcrop">
    <view class="zcrop-viewport">
      <view
        class="zcrop-stage"
        :style="stageStyle"
        @touchstart="onTouchStart"
        @touchmove.stop.prevent="onTouchMove"
        @touchend="onTouchEnd"
        @touchcancel="onTouchEnd"
      >
        <image
          v-if="src"
          class="zcrop-img"
          :src="src"
          mode="scaleToFill"
          :draggable="false"
          :style="imgStyle"
        />
        <view v-else class="zcrop-empty">
          <z-icon :name="emptyIcon" :size="56" color="#9CA3AF" />
          <text class="zcrop-empty__txt">{{ emptyText }}</text>
        </view>
      </view>

      <view class="zcrop-mask">
        <view class="zcrop-hole" :class="{ circle }" :style="holeStyle">
          <view v-if="grid" class="zcrop-grid">
            <view class="g v1"></view><view class="g v2"></view>
            <view class="g h1"></view><view class="g h2"></view>
          </view>
          <view class="zcrop-corners" v-if="corners">
            <view class="c tl"></view><view class="c tr"></view>
            <view class="c bl"></view><view class="c br"></view>
          </view>
        </view>
      </view>

      <view class="zcrop-top" v-if="topbar">
        <view class="zcrop-top__left">
          <slot name="left">
            <view class="hit" @tap="onPick">
              <z-button type="ghost" size="sm">{{ pickText }}</z-button>
            </view>
          </slot>
        </view>
        <view class="zcrop-top__mid">
          <text class="zcrop-title">{{ title }}</text>
        </view>
        <view class="zcrop-top__right">
          <slot name="right">
            <view class="hit" @tap="onReset">
              <z-button type="ghost" size="sm">{{ resetText }}</z-button>
            </view>
          </slot>
        </view>
      </view>

      <view class="zcrop-bar">
        <view class="zcrop-actions">
          <view class="hit act" @tap="onRotateLeft"><z-button type="gray" size="sm">{{ rotateLeftText }}</z-button></view>
          <view class="hit act" @tap="onRotateRight"><z-button type="gray" size="sm">{{ rotateRightText }}</z-button></view>
          <view class="hit act" @tap="onToggleGrid"><z-button type="ghost" size="sm">{{ grid ? gridOnText : gridOffText }}</z-button></view>
          <view class="hit act" @tap="onToggleCircle"><z-button type="ghost" size="sm">{{ circle ? rectText : circleText }}</z-button></view>
        </view>

        <view class="zcrop-presets" v-if="presets">
          <view class="preset" v-for="p in presetList" :key="p.key" :class="{ on: p.key === presetKey }" @tap="setPreset(p)">
            <text class="preset__txt">{{ p.label }}</text>
          </view>
        </view>

        <view class="zcrop-cta">
          <view class="hit" @tap="onExport">
            <z-button type="primary">{{ doneText }}</z-button>
          </view>
        </view>

        <view class="zcrop-safe" v-if="safeArea"></view>
      </view>

      <canvas
        class="zcrop-canvas"
        :canvas-id="canvasId"
        :id="canvasId"
        :style="{ width: canvasCssW + 'px', height: canvasCssH + 'px' }"
        :width="canvasPxW"
        :height="canvasPxH"
      ></canvas>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch, getCurrentInstance, defineExpose } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  title: { type: String, default: 'Image Cropper' },

  aspect: { type: Number, default: 1 },
  cropWidthRatio: { type: Number, default: 0.78 },
  minScale: { type: Number, default: 1 },
  maxScale: { type: Number, default: 4 },

  topbar: { type: Boolean, default: true },
  presets: { type: Boolean, default: true },
  corners: { type: Boolean, default: true },
  defaultGrid: { type: Boolean, default: true },
  defaultCircle: { type: Boolean, default: false },
  safeArea: { type: Boolean, default: true },

  outputSize: { type: Number, default: 900 },
  format: { type: String, default: 'jpg' },
  quality: { type: Number, default: 0.92 },
  background: { type: String, default: '#0B1220' },

  // 🔥 修复“第一次导出空白”：给导出过程加一个更稳的等待/重试策略
  exportDelay: { type: Number, default: 80 }, // ms：draw->导出的等待
  exportRetry: { type: Number, default: 1 },  // 次：检测到空白后重试次数（默认重试1次）

  pickerCount: { type: Number, default: 1 },
  resetMode: { type: String, default: 'clear' },

  pickText: { type: String, default: '选择图片' },
  resetText: { type: String, default: '重置' },
  doneText: { type: String, default: '裁剪完成' },
  rotateLeftText: { type: String, default: '左旋转' },
  rotateRightText: { type: String, default: '右旋转' },
  gridOnText: { type: String, default: '关网格' },
  gridOffText: { type: String, default: '开网格' },
  circleText: { type: String, default: '圆形' },
  rectText: { type: String, default: '矩形' },
  emptyText: { type: String, default: '请选择图片' },
  emptyIcon: { type: String, default: 'image' },

  toastOnError: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'change', 'ready', 'export', 'error', 'reset'])
const inst = getCurrentInstance()
const proxy = inst?.proxy

const src = computed({
  get: () => props.modelValue,
  set: (v) => { emit('update:modelValue', v); emit('change', v) }
})

const canvasId = `zcrop_${Math.random().toString(36).slice(2, 9)}`
const dpr = ref(1)
const canvasCssW = ref(2)
const canvasCssH = ref(2)
const canvasPxW = ref(2)
const canvasPxH = ref(2)

const grid = ref(!!props.defaultGrid)
const circle = ref(!!props.defaultCircle)

const presetList = computed(() => ([
  { key: '1:1', label: '1:1', aspect: 1 },
  { key: '4:3', label: '4:3', aspect: 4 / 3 },
  { key: '3:4', label: '3:4', aspect: 3 / 4 },
  { key: '16:9', label: '16:9', aspect: 16 / 9 }
]))
const presetKey = ref('1:1')
const curAspect = ref(props.aspect || 1)

watch(() => props.aspect, (v) => {
  curAspect.value = v || 1
  presetKey.value = ''
  nextTick(() => initLayout())
})

const viewport = ref({ w: 0, h: 0 })
const crop = ref({ w: 0, h: 0 })

const img = ref({ w: 0, h: 0 })
const base = ref({ w: 0, h: 0 })

const tx = ref(0)
const ty = ref(0)
const scale = ref(1)
const rotate = ref(0)

const touching = ref(false)
const start1 = ref({ x: 0, y: 0 })
const start2 = ref({ x: 0, y: 0 })
const startTx = ref(0)
const startTy = ref(0)
const startScale = ref(1)
const startDist = ref(0)

const stageStyle = computed(() => ({ width: viewport.value.w + 'px', height: viewport.value.h + 'px' }))
const holeStyle = computed(() => ({ width: crop.value.w + 'px', height: crop.value.h + 'px' }))

const imgStyle = computed(() => {
  const w = base.value.w * scale.value
  const h = base.value.h * scale.value
  return {
    width: w + 'px',
    height: h + 'px',
    transform: `translate(${tx.value}px, ${ty.value}px) rotate(${rotate.value}deg)`,
    transformOrigin: 'center center',
    left: '50%',
    top: '50%',
    position: 'absolute',
    marginLeft: (-w / 2) + 'px',
    marginTop: (-h / 2) + 'px'
  }
})

const _actionTs = ref(0)
function actOnce(fn) {
  const now = Date.now()
  if (now - _actionTs.value < 260) return
  _actionTs.value = now
  fn && fn()
}

function pcall(method, args, ctx) {
  return new Promise((resolve, reject) => {
    try {
      const opt = Object.assign({}, args || {}, {
        success: (res) => resolve(res),
        fail: (err) => reject(err)
      })
      if (ctx) method.call(ctx, opt)
      else method(opt)
    } catch (e) {
      reject(e)
    }
  })
}
function wait(ms) { return new Promise((r) => setTimeout(r, ms)) }

onMounted(async () => {
  // #ifdef H5
  dpr.value = window.devicePixelRatio || 1
  // #endif
  // #ifndef H5
  try {
    const sys = uni.getSystemInfoSync ? uni.getSystemInfoSync() : null
    dpr.value = sys?.pixelRatio ? Number(sys.pixelRatio) : 1
  } catch (e) { dpr.value = 1 }
  // #endif

  if (!Number.isFinite(dpr.value) || dpr.value <= 0) dpr.value = 1

  await nextTick()
  await initLayout()
  if (src.value) {
    await loadImageInfo(src.value)
    await nextTick()
    initTransform()
  }
})

watch(() => src.value, async (v) => {
  if (!v) return
  await loadImageInfo(v)
  await nextTick()
  await initLayout()
  initTransform()
})

async function initLayout() {
  const rect = await queryRect('.zcrop-viewport')
  viewport.value = { w: rect.width || 0, h: rect.height || 0 }

  const cw = clamp((rect.width || 0) * props.cropWidthRatio, 160, (rect.width || 0) - 24)
  const ch = clamp(cw / (curAspect.value || 1), 160, (rect.height || 0) - 24)
  crop.value = { w: cw, h: ch }

  emit('ready', { viewport: viewport.value, crop: crop.value })
}

function initTransform() {
  if (!img.value.w || !img.value.h) return
  const sCover = Math.max(crop.value.w / img.value.w, crop.value.h / img.value.h)
  base.value = { w: img.value.w * sCover, h: img.value.h * sCover }
  tx.value = 0
  ty.value = 0
  scale.value = Math.max(props.minScale, 1)
  rotate.value = 0
  constrain()
}

async function loadImageInfo(path) {
  try {
    const info = await pcall(uni.getImageInfo, { src: path })
    img.value = { w: info.width, h: info.height }
  } catch (e) {
    emitErr(e)
  }
}

/** gestures */
function onTouchStart(e) {
  if (!src.value) return
  const t = (e.touches && e.touches.length) ? e.touches : (e.changedTouches || [])
  if (!t.length) return
  touching.value = true
  startTx.value = tx.value
  startTy.value = ty.value
  startScale.value = scale.value
  start1.value = { x: t[0].clientX, y: t[0].clientY }
  if (t.length >= 2) {
    start2.value = { x: t[1].clientX, y: t[1].clientY }
    startDist.value = dist(start1.value, start2.value)
  } else {
    startDist.value = 0
  }
}

function onTouchMove(e) {
  if (!touching.value || !src.value) return
  const t = (e.touches && e.touches.length) ? e.touches : (e.changedTouches || [])
  if (!t.length) return

  if (t.length >= 2 && startDist.value > 0) {
    const p1 = { x: t[0].clientX, y: t[0].clientY }
    const p2 = { x: t[1].clientX, y: t[1].clientY }
    const d = dist(p1, p2)
    const factor = d / startDist.value
    const nextScale = clamp(startScale.value * factor, props.minScale, props.maxScale)

    const c0 = mid(start1.value, start2.value)
    const c1 = mid(p1, p2)
    const dx = c1.x - c0.x
    const dy = c1.y - c0.y

    scale.value = nextScale
    tx.value = startTx.value + dx
    ty.value = startTy.value + dy
  } else {
    const p = { x: t[0].clientX, y: t[0].clientY }
    tx.value = startTx.value + (p.x - start1.value.x)
    ty.value = startTy.value + (p.y - start1.value.y)
  }
  constrain()
}

function onTouchEnd() { touching.value = false; constrain() }

function dist(a, b) { const dx = a.x - b.x; const dy = a.y - b.y; return Math.sqrt(dx * dx + dy * dy) }
function mid(a, b) { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 } }
function clamp(n, min, max) { return Math.max(min, Math.min(max, n)) }

function constrain() {
  if (!base.value.w || !base.value.h) return
  const r = ((rotate.value % 360) + 360) % 360
  const swap = r === 90 || r === 270
  const halfW = (swap ? base.value.h : base.value.w) * scale.value / 2
  const halfH = (swap ? base.value.w : base.value.h) * scale.value / 2
  const limitX = Math.max(0, halfW - crop.value.w / 2)
  const limitY = Math.max(0, halfH - crop.value.h / 2)
  tx.value = clamp(tx.value, -limitX, limitX)
  ty.value = clamp(ty.value, -limitY, limitY)
}

/** actions */
function onReset() { actOnce(() => reset()) }
function onRotateLeft() { actOnce(() => rotateLeft()) }
function onRotateRight() { actOnce(() => rotateRight()) }
function onToggleGrid() { actOnce(() => { grid.value = !grid.value }) }
function onToggleCircle() { actOnce(() => { circle.value = !circle.value }) }
function onPick() { actOnce(() => pickImage()) }
function onExport() { actOnce(() => exportImage()) }

function reset() {
  if (!src.value) return
  if (props.resetMode === 'clear') {
    src.value = ''
    emit('reset', { mode: 'clear' })
    return
  }
  initTransform()
  emit('reset', { mode: 'transform' })
}
function rotateLeft() { if (!src.value) return; rotate.value = ((rotate.value - 90) % 360 + 360) % 360; constrain() }
function rotateRight() { if (!src.value) return; rotate.value = (rotate.value + 90) % 360; constrain() }

function setPreset(p) {
  presetKey.value = p.key
  curAspect.value = p.aspect
  nextTick(async () => { await initLayout(); initTransform() })
}

async function pickImage() {
  try {
    const res = await pcall(uni.chooseImage, { count: props.pickerCount })
    const path = res.tempFilePaths && res.tempFilePaths[0]
    if (path) src.value = path
  } catch (e) {}
}

// #ifdef H5
function findHtmlCanvas() {
  const host = document.getElementById(canvasId)
  if (!host) return null
  if (typeof host.getContext === 'function') return host
  const inner = host.querySelector && host.querySelector('canvas')
  if (inner && typeof inner.getContext === 'function') return inner
  const byAttr = document.querySelector && document.querySelector(`canvas[canvas-id="${canvasId}"]`)
  if (byAttr && typeof byAttr.getContext === 'function') return byAttr
  return null
}
function loadHtmlImage(srcPath) {
  return new Promise((resolve, reject) => {
    const im = new Image()
    im.onload = () => resolve(im)
    im.onerror = () => reject(new Error('image load failed'))
    im.src = srcPath
  })
}
// #endif

// #ifndef H5
async function getFileSize(path) {
  try {
    if (!uni.getFileInfo) return -1
    const info = await pcall(uni.getFileInfo, { filePath: path })
    return typeof info.size === 'number' ? info.size : -1
  } catch (e) { return -1 }
}
// #endif

function buildExportParams() {
  const outW = Math.max(200, Math.floor(props.outputSize))
  const outH = Math.max(200, Math.floor(outW * (crop.value.h / crop.value.w)))
  const pxW = Math.max(2, Math.floor(outW * dpr.value))
  const pxH = Math.max(2, Math.floor(outH * dpr.value))
  const ratio = outW / crop.value.w
  const drawW = base.value.w * scale.value * ratio
  const drawH = base.value.h * scale.value * ratio
  const offX = tx.value * ratio
  const offY = ty.value * ratio
  const rad = (rotate.value * Math.PI) / 180
  const isPng = props.format === 'png'
  return { outW, outH, pxW, pxH, ratio, drawW, drawH, offX, offY, rad, isPng }
}

async function exportImage() {
  if (!src.value || !viewport.value.w) return
  try {
    if (!base.value.w || !base.value.h) initTransform()

    uni.showLoading && uni.showLoading({ title: '裁剪中…' })

    const p = buildExportParams()
    canvasCssW.value = p.outW
    canvasCssH.value = p.outH
    canvasPxW.value = p.pxW
    canvasPxH.value = p.pxH
    await nextTick()
    await wait(props.exportDelay)

    // #ifdef H5
    const canvas = findHtmlCanvas()
    if (!canvas) throw new Error('HTMLCanvasElement not found')
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('2d context not available')

    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.scale(dpr.value, dpr.value)

    if (!p.isPng && props.background) {
      ctx.fillStyle = props.background
      ctx.fillRect(0, 0, p.outW, p.outH)
    } else {
      ctx.clearRect(0, 0, p.outW, p.outH)
    }

    const im = await loadHtmlImage(src.value)
    ctx.save()
    ctx.translate(p.outW / 2 + p.offX, p.outH / 2 + p.offY)
    ctx.rotate(p.rad)
    ctx.drawImage(im, -p.drawW / 2, -p.drawH / 2, p.drawW, p.drawH)
    ctx.restore()

    const blob = await new Promise((resolve) => {
      const type = p.isPng ? 'image/png' : 'image/jpeg'
      canvas.toBlob((b) => resolve(b), type, clamp(props.quality, 0.5, 1))
    })
    if (!blob) throw new Error('export blob failed')
    const url = URL.createObjectURL(blob)

    uni.hideLoading && uni.hideLoading()
    emit('export', { path: url, width: p.outW, height: p.outH, mime: p.isPng ? 'image/png' : 'image/jpeg', blobUrl: url, platform: 'h5' })
    return
    // #endif

    // #ifndef H5
    const ctx2 = uni.createCanvasContext(canvasId, proxy)

    async function drawOnce() {
      if (!p.isPng && props.background) {
        ctx2.setFillStyle(props.background)
        ctx2.fillRect(0, 0, p.outW, p.outH)
      } else {
        ctx2.clearRect(0, 0, p.outW, p.outH)
      }
      ctx2.save()
      ctx2.translate(p.outW / 2 + p.offX, p.outH / 2 + p.offY)
      ctx2.rotate(p.rad)
      ctx2.drawImage(src.value, -p.drawW / 2, -p.drawH / 2, p.drawW, p.drawH)
      ctx2.restore()
      await new Promise((resolve) => ctx2.draw(false, resolve))
      await wait(props.exportDelay)
    }

    async function exportOnce() {
      const res = await pcall(
        uni.canvasToTempFilePath,
        { canvasId, destWidth: p.pxW, destHeight: p.pxH, fileType: p.isPng ? 'png' : 'jpg', quality: clamp(props.quality, 0.5, 1) },
        proxy
      )
      return res.tempFilePath
    }

    // ✅ 预热 draw：某些机型第一次导出会白图（draw 已回调但纹理未就绪）
    await drawOnce()

    let outPath = await exportOnce()
    let size = await getFileSize(outPath)

    // ✅ 空白检测与重试：size 很小通常是白图/透明图
    let retries = Math.max(0, Math.floor(props.exportRetry))
    while (retries > 0 && size >= 0 && size < 1200) {
      retries -= 1
      await drawOnce()
      outPath = await exportOnce()
      size = await getFileSize(outPath)
    }

    uni.hideLoading && uni.hideLoading()
    emit('export', { path: outPath, width: p.outW, height: p.outH, platform: 'native', size })
    // #endif
  } catch (e) {
    uni.hideLoading && uni.hideLoading()
    emitErr(e)
  }
}

async function queryRect(sel) {
  return new Promise((resolve) => {
    uni.createSelectorQuery().in(proxy).select(sel).boundingClientRect((rect) => resolve(rect || { width: 0, height: 0 })).exec()
  })
}

function emitErr(e) {
  emit('error', e)
  if (props.toastOnError && uni.showToast) {
    uni.showToast({ title: e?.errMsg || e?.message || '操作失败', icon: 'none' })
  }
}

defineExpose({ reset, exportImage, pickImage, rotateLeft, rotateRight })
</script>

<style scoped>
.zcrop{ width: 100%; }
.zcrop-viewport{
  position: relative;
  width: 100%;
  height: 72vh;
  min-height: 720rpx;
  background: #0B1220;
  border-radius: 24rpx;
  overflow: hidden;
}
.zcrop-stage{ position:absolute; left:0; top:0; width:100%; height:100%; }
.hit{ display:inline-flex; }

.zcrop-empty{
  position:absolute; left:50%; top:50%;
  transform: translate(-50%, -50%);
  display:flex; flex-direction:column; align-items:center; gap: 12rpx;
}
.zcrop-empty__txt{ font-size: 26rpx; color: rgba(255,255,255,.72); }

.zcrop-mask{ position:absolute; inset:0; z-index:5; pointer-events:none; }
.zcrop-hole{
  position:absolute; left:50%; top:50%;
  transform: translate(-50%, -50%);
  border: 2rpx solid rgba(255,255,255,.92);
  box-shadow: 0 0 0 9999rpx rgba(0,0,0,.55);
  border-radius: 18rpx; overflow:hidden;
}
.zcrop-hole.circle{ border-radius: 9999rpx; }

.zcrop-grid{ position:absolute; inset:0; }
.zcrop-grid .g{ position:absolute; background: rgba(255,255,255,.38); }
.zcrop-grid .v1{ top:0; bottom:0; left: 33.333%; width: 1rpx; }
.zcrop-grid .v2{ top:0; bottom:0; left: 66.666%; width: 1rpx; }
.zcrop-grid .h1{ left:0; right:0; top: 33.333%; height: 1rpx; }
.zcrop-grid .h2{ left:0; right:0; top: 66.666%; height: 1rpx; }

.zcrop-corners{ position:absolute; inset:0; }
.zcrop-corners .c{ position:absolute; width:36rpx; height:36rpx; border-color: rgba(255,255,255,.95); }
.zcrop-corners .tl{ left:0; top:0; border-left:6rpx solid; border-top:6rpx solid; border-top-left-radius:12rpx; }
.zcrop-corners .tr{ right:0; top:0; border-right:6rpx solid; border-top:6rpx solid; border-top-right-radius:12rpx; }
.zcrop-corners .bl{ left:0; bottom:0; border-left:6rpx solid; border-bottom:6rpx solid; border-bottom-left-radius:12rpx; }
.zcrop-corners .br{ right:0; bottom:0; border-right:6rpx solid; border-bottom:6rpx solid; border-bottom-right-radius:12rpx; }

.zcrop-top{
  position:absolute; left:0; right:0; top:0;
  padding: 18rpx 18rpx 14rpx;
  display:flex; align-items:center; justify-content:space-between;
  z-index:10;
  background: linear-gradient(to bottom, rgba(0,0,0,.62), rgba(0,0,0,0));
}
.zcrop-top__left, .zcrop-top__right{ min-width: 180rpx; display:flex; align-items:center; }
.zcrop-top__mid{ flex:1; display:flex; justify-content:center; }
.zcrop-title{ color:#fff; font-size:28rpx; font-weight:800; }

.zcrop-bar{
  position:absolute; left:0; right:0; bottom:0;
  padding: 16rpx 16rpx 18rpx;
  z-index:10;
  background: linear-gradient(to top, rgba(0,0,0,.72), rgba(0,0,0,0));
}
.zcrop-actions{ display:flex; gap: 12rpx; flex-wrap: wrap; }
.zcrop-presets{ margin-top:14rpx; display:flex; gap:12rpx; }
.preset{ padding: 10rpx 14rpx; border-radius:9999rpx; background: rgba(255,255,255,.12); border:1rpx solid rgba(255,255,255,.12); }
.preset.on{ background: rgba(70,92,255,.22); border-color: rgba(70,92,255,.65); }
.preset__txt{ font-size:24rpx; color: rgba(255,255,255,.86); font-weight:700; }
.zcrop-cta{ margin-top:14rpx; }

.zcrop-safe{ height: env(safe-area-inset-bottom); }
.zcrop-canvas{ position:absolute; left:-99999px; top:-99999px; }
</style>
