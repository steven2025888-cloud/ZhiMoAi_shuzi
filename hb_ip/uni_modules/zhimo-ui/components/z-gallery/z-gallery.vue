<template>
  <view v-if="show" class="zg" :style="{ zIndex: String(zIndex) }" :catchtouchmove="lockScroll" @touchmove.stop.prevent>
    <view class="zg__mask" :style="{ background: maskColor }" @tap="onMaskTap" />

    <!-- 图片轮播 -->
    <swiper
      class="zg__swiper"
      :current="index"
      :circular="loop"
      :indicator-dots="false"
      :autoplay="false"
      @change="onChange"
      @animationfinish="onFinish"
    >
      <swiper-item v-for="(it, i) in normItems" :key="it.__key">
        <view class="zg__slide" @tap="toggleUI">
          <movable-area class="zg__mv-area">
            <movable-view
              class="zg__mv-view"
              :scale="enableZoom"
              :scale-min="zoomMin"
              :scale-max="zoomMax"
              :inertia="true"
              :out-of-bounds="true"
              :direction="enableZoom ? 'all' : 'none'"
              :disabled="!enableZoom"
              :damping="40"
              @tap.stop
            >
              <image class="zg__img" :src="it.src" mode="aspectFit" @longpress="onLongPress(it, i)" />
            </movable-view>
          </movable-area>

          <view v-if="enableZoom && uiVisible && i === index" class="zg__hint">
            <z-icon name="mdi:gesture-pinch" :size="28" color="rgba(255,255,255,0.8)" />
            <text class="zg__hint-t">双指缩放 / 拖动查看</text>
          </view>
        </view>
      </swiper-item>
    </swiper>

    <!-- 顶部栏 - 独立于swiper，确保层级最高 -->
    <view class="zg__top" :class="{ 'is-hidden': !uiVisible }" @tap.stop>
      <view class="zg__top-left">
        <view class="zg__close-btn" @tap.stop="close">
          <z-icon name="mdi:close" :size="40" color="#fff" />
        </view>
        <text class="zg__title" v-if="title">{{ title }}</text>
      </view>

      <view class="zg__top-right">
        <slot name="top-actions" :index="index" :item="currentItem">
          <!-- 原生预览按钮 -->
          <view v-if="showNativePreview" class="zg__action-btn" @tap.stop="openNativePreview">
            <z-icon name="mdi:fullscreen" :size="36" color="#fff" />
          </view>
          <!-- 保存按钮 -->
          <view v-if="showSave" class="zg__action-btn" @tap.stop="saveCurrent">
            <z-icon name="mdi:download" :size="36" color="#fff" />
          </view>
          <!-- 删除按钮 -->
          <view v-if="showDelete" class="zg__action-btn is-danger" @tap.stop="emitDelete">
            <z-icon name="mdi:delete" :size="36" color="#fff" />
          </view>
        </slot>
      </view>
    </view>

    <!-- 底部栏 - 独立于swiper，确保层级最高 -->
    <view class="zg__bottom" :class="{ 'is-hidden': !uiVisible }" @tap.stop>
      <!-- 图片信息 -->
      <view class="zg__meta" v-if="showMeta && (currentItem?.title || currentItem?.desc)">
        <text class="zg__meta-title">{{ currentItem?.title || '' }}</text>
        <text class="zg__meta-desc" v-if="currentItem?.desc">{{ currentItem.desc }}</text>
      </view>

      <!-- 指示器和操作栏 -->
      <view class="zg__bar">
        <view class="zg__index" v-if="showIndex">
          <text class="zg__index-num">{{ index + 1 }}</text>
          <text class="zg__index-sep">/</text>
          <text class="zg__index-total">{{ normItems.length }}</text>
        </view>

        <view class="zg__dots" v-if="showDots && normItems.length > 1">
          <view v-for="i in normItems.length" :key="i" class="zg__dot" :class="{ 'is-on': i - 1 === index }" />
        </view>

        <view class="zg__actions">
          <slot name="actions" :index="index" :item="currentItem">
            <view v-if="showInfo" class="zg__info-btn" @tap.stop="showImageInfo">
              <z-icon name="mdi:information-outline" :size="32" color="#fff" />
              <text class="zg__info-text">信息</text>
            </view>
            <view v-if="ctaText" class="zg__cta-btn" @tap.stop="emitCta">
              <text class="zg__cta-text">{{ ctaText }}</text>
            </view>
          </slot>
        </view>
      </view>

      <!-- 缩略图条 -->
      <scroll-view v-if="showThumbs" class="zg__thumbs" scroll-x :show-scrollbar="false" @tap.stop>
        <view class="zg__thumbs-inner">
          <view
            v-for="(it, i) in normItems"
            :key="it.__key + '-t'"
            class="zg__thumb"
            :class="{ 'is-on': i === index }"
            @tap.stop="go(i)"
          >
            <image class="zg__thumb-img" :src="it.thumb || it.src" mode="aspectFill" />
          </view>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type ImgItem = string | { src: string; thumb?: string; title?: string; desc?: string; [k: string]: any }

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    images: ImgItem[]
    start?: number
    loop?: boolean
    closeOnMask?: boolean
    lockScroll?: boolean
    title?: string

    showIndex?: boolean
    showDots?: boolean
    showThumbs?: boolean
    showMeta?: boolean
    showSave?: boolean
    showDelete?: boolean
    showInfo?: boolean
    showNativePreview?: boolean
    ctaText?: string

    maskColor?: string
    zIndex?: number

    enableZoom?: boolean
    zoomMin?: number
    zoomMax?: number
  }>(),
  {
    modelValue: false,
    images: () => [],
    start: 0,
    loop: false,
    closeOnMask: true,
    lockScroll: true,
    title: '',

    showIndex: true,
    showDots: true,
    showThumbs: false,
    showMeta: true,
    showSave: true,
    showDelete: false,
    showInfo: true,
    showNativePreview: true,
    ctaText: '',

    maskColor: 'rgba(0,0,0,0.95)',
    zIndex: 999,

    enableZoom: true,
    zoomMin: 1,
    zoomMax: 4,
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: boolean): void
  (e: 'change', payload: { index: number; item: any }): void
  (e: 'close'): void
  (e: 'delete', payload: { index: number; item: any }): void
  (e: 'save', payload: { index: number; item: any; path?: string }): void
  (e: 'cta', payload: { index: number; item: any }): void
  (e: 'longpress', payload: { index: number; item: any }): void
}>()

const show = ref(!!props.modelValue)
watch(() => props.modelValue, (v) => (show.value = !!v), { immediate: true })
watch(show, (v) => emit('update:modelValue', v))

const uiVisible = ref(true)

const normItems = computed(() => {
  const arr = props.images || []
  return arr.map((it, idx) => {
    const item: any = typeof it === 'string' ? { src: it } : it
    return { ...item, __key: `${idx}-${item.src}` }
  })
})

const index = ref(0)
watch(
  () => props.start,
  (v) => (index.value = clamp(v ?? 0, 0, Math.max(0, normItems.value.length - 1))),
  { immediate: true }
)
watch(
  () => normItems.value.length,
  () => (index.value = clamp(index.value, 0, Math.max(0, normItems.value.length - 1)))
)

const currentItem = computed(() => normItems.value[index.value])

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n))
}

function close() {
  show.value = false
  emit('close')
}

function onMaskTap() {
  if (!props.closeOnMask) return
  close()
}

function toggleUI() {
  uiVisible.value = !uiVisible.value
}

function go(i: number) {
  index.value = clamp(i, 0, normItems.value.length - 1)
  emit('change', { index: index.value, item: currentItem.value })
}

function onChange(e: any) {
  const i = e?.detail?.current ?? 0
  index.value = clamp(i, 0, normItems.value.length - 1)
}
function onFinish() {
  emit('change', { index: index.value, item: currentItem.value })
}

function emitDelete() {
  emit('delete', { index: index.value, item: currentItem.value })
}
function emitCta() {
  emit('cta', { index: index.value, item: currentItem.value })
}

function onLongPress(item: any, i: number) {
  emit('longpress', { index: i, item })
}

// 显示图片信息
function showImageInfo() {
  const item = currentItem.value
  if (!item) return

  const title = item.title || '图片信息'
  const content = item.desc || `第 ${index.value + 1} 张图片`

  uni.showModal({
    title,
    content,
    showCancel: false,
    confirmText: '知道了'
  })
}

// 原生预览
function openNativePreview() {
  const urls = normItems.value.map(it => it.src)
  uni.previewImage({
    urls,
    current: index.value,
    indicator: 'number',
    loop: props.loop
  })
}

// 保存图片
async function saveCurrent() {
  const item: any = currentItem.value
  if (!item?.src) return
  const url: string = item.src

  if (url.startsWith('file://') || url.startsWith('wxfile://') || url.startsWith('_doc/') || url.startsWith('blob:')) {
    emit('save', { index: index.value, item, path: url })
    uni.showToast({ title: '已获取图片路径', icon: 'none' })
    return
  }

  // #ifdef H5
  // H5端：使用 a 标签下载或新窗口打开
  try {
    uni.showLoading({ title: '保存中…', mask: true })
    const response = await fetch(url)
    const blob = await response.blob()
    const blobUrl = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = `image_${Date.now()}.jpg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(blobUrl)
    uni.hideLoading()
    emit('save', { index: index.value, item, path: url })
    uni.showToast({ title: '已开始下载', icon: 'success' })
  } catch (e) {
    uni.hideLoading()
    // 如果 fetch 失败（跨域），尝试新窗口打开
    window.open(url, '_blank')
    emit('save', { index: index.value, item, path: url })
    uni.showToast({ title: '已在新窗口打开，请长按保存', icon: 'none' })
  }
  // #endif

  // #ifdef APP-PLUS || MP
  uni.showLoading({ title: '保存中…', mask: true })
  uni.downloadFile({
    url,
    success(res) {
      const p = (res as any).tempFilePath
      if (!p) {
        uni.hideLoading()
        uni.showToast({ title: '下载失败', icon: 'none' })
        return
      }
      uni.saveImageToPhotosAlbum({
        filePath: p,
        success() {
          uni.hideLoading()
          emit('save', { index: index.value, item, path: p })
          uni.showToast({ title: '已保存到相册', icon: 'success' })
        },
        fail() {
          uni.hideLoading()
          emit('save', { index: index.value, item, path: p })
          uni.showToast({ title: '请授权保存到相册', icon: 'none' })
        },
      })
    },
    fail() {
      uni.hideLoading()
      uni.showToast({ title: '下载失败', icon: 'none' })
    },
  })
  // #endif
}
</script>

<style scoped>
.zg {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
}

.zg__mask {
  position: absolute;
  inset: 0;
  z-index: 1;
}

/* 顶部栏 */
.zg__top {
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  padding: calc(20rpx + env(safe-area-inset-top)) 24rpx 20rpx 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  z-index: 10;
  background: linear-gradient(to bottom, rgba(0,0,0,0.6), rgba(0,0,0,0));
  transition: opacity 200ms ease;
}

.zg__top.is-hidden {
  opacity: 0;
  pointer-events: none;
}

.zg__top-left {
  display: flex;
  align-items: center;
  gap: 16rpx;
  min-width: 0;
}

.zg__close-btn {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  cursor: pointer;
}

.zg__close-btn:active {
  transform: scale(0.9);
  background: rgba(255,255,255,0.25);
}

.zg__title {
  font-size: 30rpx;
  color: #fff;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400rpx;
}

.zg__top-right {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.zg__action-btn {
  width: 72rpx;
  height: 72rpx;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  cursor: pointer;
}

.zg__action-btn:active {
  transform: scale(0.9);
  background: rgba(255,255,255,0.25);
}

.zg__action-btn.is-danger {
  background: rgba(239,68,68,0.3);
}

.zg__action-btn.is-danger:active {
  background: rgba(239,68,68,0.5);
}

/* 轮播 */
.zg__swiper {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 2;
}

.zg__slide {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zg__mv-area {
  width: 100%;
  height: 100%;
}

.zg__mv-view {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.zg__img {
  width: 100%;
  height: 100%;
}

.zg__hint {
  position: absolute;
  left: 50%;
  bottom: 200rpx;
  transform: translateX(-50%);
  padding: 16rpx 24rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.zg__hint-t {
  font-size: 24rpx;
  color: rgba(255,255,255,0.85);
}

/* 底部栏 */
.zg__bottom {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 20rpx 24rpx calc(24rpx + env(safe-area-inset-bottom)) 24rpx;
  z-index: 10;
  background: linear-gradient(to top, rgba(0,0,0,0.7), rgba(0,0,0,0));
  transition: opacity 200ms ease;
}

.zg__bottom.is-hidden {
  opacity: 0;
  pointer-events: none;
}

/* 图片信息 */
.zg__meta {
  padding: 0 8rpx 16rpx 8rpx;
}

.zg__meta-title {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.zg__meta-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 26rpx;
  color: rgba(255,255,255,0.7);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 指示器栏 */
.zg__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  position: relative;
  min-height: 60rpx;
}

.zg__index {
  display: flex;
  align-items: baseline;
  gap: 6rpx;
  padding: 8rpx 16rpx;
  background: rgba(255,255,255,0.1);
  border-radius: 999rpx;
  flex-shrink: 0;
}

.zg__index-num {
  font-size: 32rpx;
  font-weight: 700;
  color: #fff;
}

.zg__index-sep {
  font-size: 24rpx;
  color: rgba(255,255,255,0.5);
}

.zg__index-total {
  font-size: 24rpx;
  color: rgba(255,255,255,0.7);
}

/* 指示点 - 绝对定位居中 */
.zg__dots {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.zg__dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 999rpx;
  background: rgba(255,255,255,0.3);
  transition: all 0.2s ease;
}

.zg__dot.is-on {
  width: 28rpx;
  background: #fff;
}

/* 操作按钮 */
.zg__actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
  flex-shrink: 0;
  margin-left: auto;
}

.zg__info-btn {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 12rpx 20rpx;
  background: rgba(255,255,255,0.15);
  border-radius: 999rpx;
  transition: all 0.2s ease;
  cursor: pointer;
}

.zg__info-btn:active {
  transform: scale(0.95);
  background: rgba(255,255,255,0.25);
}

.zg__info-text {
  font-size: 26rpx;
  color: #fff;
}

.zg__cta-btn {
  padding: 14rpx 28rpx;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border-radius: 999rpx;
  box-shadow: 0 4rpx 16rpx rgba(99, 102, 241, 0.4);
  transition: all 0.2s ease;
  cursor: pointer;
}

.zg__cta-btn:active {
  transform: scale(0.95);
  opacity: 0.9;
}

.zg__cta-text {
  font-size: 26rpx;
  font-weight: 600;
  color: #fff;
}

/* 缩略图 */
.zg__thumbs {
  margin-top: 20rpx;
  width: 100%;
  position: relative;
  z-index: 10;
}

.zg__thumbs-inner {
  display: flex;
  gap: 12rpx;
  padding: 0 8rpx;
}

.zg__thumb {
  width: 100rpx;
  height: 100rpx;
  border-radius: 16rpx;
  overflow: hidden;
  border: 3rpx solid rgba(255,255,255,0.2);
  opacity: 0.6;
  transition: all 0.2s ease;
  flex-shrink: 0;
  cursor: pointer;
}

.zg__thumb.is-on {
  border-color: #6366f1;
  opacity: 1;
  transform: scale(1.05);
}

.zg__thumb-img {
  width: 100%;
  height: 100%;
}
</style>
