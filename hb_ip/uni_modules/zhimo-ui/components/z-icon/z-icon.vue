<template>
  <view class="z-icon" :class="{ 'is-spin': spin }" :style="wrapStyle" @click="onClick">
    <!-- 本地/网络图片模式 -->
    <image
      v-if="src"
      class="z-icon__img"
      :src="src"
      mode="aspectFit"
      :style="imgStyle"
    />

    <!-- H5：用 @iconify/vue 在线渲染 -->
    <!-- #ifdef H5 -->
    <Icon
      v-else-if="name"
      :icon="name"
      :style="iconStyle"
    />
    <!-- #endif -->

    <!-- APP-VUE：使用 renderjs 在线渲染 SVG -->
    <!-- #ifdef APP-VUE -->
    <view
      v-else-if="name"
      ref="iconRef"
      class="z-icon__svg"
      :iconName="name"
      :iconSize="sizeNum"
      :iconColor="color"
      :iconRotate="rotate"
      :change:iconName="bindIcon.bindName"
      :change:iconSize="bindIcon.bindSize"
      :change:iconColor="bindIcon.bindColor"
      :change:iconRotate="bindIcon.bindRotate"
      :style="svgWrapStyle"
    />
    <!-- #endif -->

    <!-- 小程序：退化为线上图片 -->
    <!-- #ifdef MP -->
    <image
      v-else-if="name"
      class="z-icon__img"
      :src="fallbackSrc"
      mode="aspectFit"
      :style="imgStyle"
    />
    <!-- #endif -->

    <slot v-if="!name && !src" />
  </view>
</template>

<!-- APP-VUE renderjs 模块 -->
<!-- #ifdef APP-VUE -->
<script module="bindIcon" lang="renderjs">
// 获取全局缓存
function getGlobalCache() {
  if (typeof window !== 'undefined') {
    window.__ZICON_CACHE__ = window.__ZICON_CACHE__ || {}
    return window.__ZICON_CACHE__
  }
  return {}
}

// 从 localStorage 获取缓存
function getStorageCache(name) {
  try {
    const key = `zicon_${name}`
    return localStorage.getItem(key)
  } catch (e) {
    return null
  }
}

// 保存到缓存
function saveToCache(name, svg) {
  const cache = getGlobalCache()
  cache[name] = svg

  // 同时保存到 localStorage
  try {
    const key = `zicon_${name}`
    localStorage.setItem(key, svg)
  } catch (e) {
    // 忽略存储错误
  }
}

// 获取图标 SVG
async function fetchIcon(name) {
  if (!name) return null

  // 1. 检查内存缓存
  const cache = getGlobalCache()
  if (cache[name]) {
    return cache[name]
  }

  // 2. 检查 localStorage 缓存
  const storageCached = getStorageCache(name)
  if (storageCached) {
    cache[name] = storageCached
    return storageCached
  }

  // 3. 从网络获取
  const parts = name.split(':')
  if (parts.length !== 2) return null
  const [prefix, iconName] = parts

  try {
    const url = `https://api.iconify.design/${prefix}/${iconName}.svg`
    const response = await fetch(url)
    if (!response.ok) return null

    const svgText = await response.text()
    saveToCache(name, svgText)
    return svgText
  } catch (e) {
    console.warn('Failed to fetch icon:', name, e)
    return null
  }
}

// 渲染 SVG 到容器
function renderSvg(el, svgText, size, color, rotate) {
  if (!el || !svgText) return

  let svg = svgText

  // 移除原有的 width/height 属性，使用 style 控制
  svg = svg.replace(/\s*width="[^"]*"/g, '')
  svg = svg.replace(/\s*height="[^"]*"/g, '')

  // 构建样式
  const sizeStr = size ? `${size}rpx` : '48rpx'
  let styleStr = `width:${sizeStr};height:${sizeStr};display:block;`

  if (rotate && Number(rotate) !== 0) {
    styleStr += `transform:rotate(${rotate}deg);`
  }

  // 设置颜色
  if (color) {
    svg = svg.replace(/currentColor/g, color)
    // 如果 SVG 没有 fill 属性，添加一个
    if (!svg.includes('fill=')) {
      svg = svg.replace(/<svg/, `<svg fill="${color}"`)
    } else {
      // 替换现有的 fill 属性（除了 fill="none"）
      svg = svg.replace(/fill="(?!none)[^"]*"/g, `fill="${color}"`)
    }
  }

  // 添加样式
  svg = svg.replace(/<svg/, `<svg style="${styleStr}"`)

  el.innerHTML = svg
}

export default {
  data() {
    return {
      currentName: '',
      currentSize: 48,
      currentColor: '',
      currentRotate: 0,
      svgCache: null,
      initialized: false
    }
  },
  methods: {
    async bindName(newVal, oldVal, ownerInstance, instance) {
      const name = newVal || oldVal
      if (name === this.currentName && this.svgCache) return

      this.currentName = name
      this.initialized = true
      await this.updateIcon(instance)
    },
    bindSize(newVal, oldVal, ownerInstance, instance) {
      this.currentSize = newVal || oldVal || 48
      if (this.svgCache && this.initialized) {
        this.renderCurrent(instance)
      }
    },
    bindColor(newVal, oldVal, ownerInstance, instance) {
      this.currentColor = newVal || oldVal || ''
      if (this.svgCache && this.initialized) {
        this.renderCurrent(instance)
      }
    },
    bindRotate(newVal, oldVal, ownerInstance, instance) {
      this.currentRotate = newVal || oldVal || 0
      if (this.svgCache && this.initialized) {
        this.renderCurrent(instance)
      }
    },
    async updateIcon(instance) {
      if (!this.currentName) return

      const svg = await fetchIcon(this.currentName)
      if (svg) {
        this.svgCache = svg
        this.renderCurrent(instance)
      }
    },
    renderCurrent(instance) {
      if (!this.svgCache) return
      const el = instance.$el
      if (el) {
        renderSvg(el, this.svgCache, this.currentSize, this.currentColor, this.currentRotate)
      }
    }
  }
}
</script>
<!-- #endif -->

<script setup>
import { computed } from "vue";

/**
 * z-icon（Vue3）
 * ✅ H5：使用 @iconify/vue（在线模式）
 * ✅ APP-VUE：使用 renderjs 在线渲染 SVG（立即显示，支持颜色）
 * ✅ 小程序：fallback 到 api.iconify.design 的线上图片
 */

// #ifdef H5
import { Icon } from "@iconify/vue";
// #endif

const props = defineProps({
  /** Iconify 图标名（例如：mdi:home） */
  name: { type: String, default: "" },

  /** 本地/网络图片路径 */
  src: { type: String, default: "" },

  /** 尺寸（number 默认 rpx；也可 '20px'/'40rpx'） */
  size: { type: [Number, String], default: 48 },

  /** 颜色 */
  color: { type: String, default: "" },

  /** 旋转角度（deg） */
  rotate: { type: [Number, String], default: 0 },

  /** 是否旋转动画 */
  spin: { type: Boolean, default: false },

  /** 非 H5 fallback 格式：png / svg */
  fallbackFormat: { type: String, default: "svg" },

  /** 非 H5 fallback 域名 */
  fallbackBaseUrl: { type: String, default: "https://api.iconify.design" },
});

const emit = defineEmits(["click"]);

function toSize(v) {
  if (v === "" || v === null || v === undefined) return "";
  const s = String(v);
  return /[a-z%]/i.test(s) ? s : `${s}rpx`;
}

const sizeVal = computed(() => toSize(props.size));
const sizeNum = computed(() => {
  const s = String(props.size).replace(/[^0-9.]/g, "");
  return Number(s) || 48;
});

const wrapStyle = computed(() => ({
  width: sizeVal.value,
  height: sizeVal.value,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
}));

const rotateDeg = computed(() => Number(props.rotate || 0));

const iconStyle = computed(() => ({
  width: sizeVal.value,
  height: sizeVal.value,
  color: props.color || "currentColor",
  transform: rotateDeg.value ? `rotate(${rotateDeg.value}deg)` : "none",
}));

const imgStyle = computed(() => ({
  width: sizeVal.value,
  height: sizeVal.value,
  transform: rotateDeg.value ? `rotate(${rotateDeg.value}deg)` : "none",
}));

const svgWrapStyle = computed(() => ({
  width: sizeVal.value,
  height: sizeVal.value,
}));

const fallbackSrc = computed(() => {
  if (!props.name) return "";
  const parts = props.name.split(":");
  if (parts.length !== 2) return "";
  const [prefix, iconName] = parts;

  const fmt = (props.fallbackFormat || "svg").toLowerCase() === "png" ? "png" : "svg";
  const s = String(props.size).replace(/[^0-9.]/g, "") || "48";

  let url = `${props.fallbackBaseUrl}/${prefix}/${iconName}.${fmt}?width=${s}&height=${s}`;

  if (props.color) {
    url += `&color=${encodeURIComponent(props.color)}`;
  }

  return url;
});

function onClick() {
  emit("click", { detail: { name: props.name, src: props.src } });
}
</script>

<style scoped>
.z-icon{
  /* #ifdef H5 */
  cursor: pointer;
  /* #endif */
}

.z-icon__img{
  display: block;
}

.z-icon__svg{
  display: flex;
  align-items: center;
  justify-content: center;
}

.z-icon.is-spin{
  /* #ifndef APP-NVUE */
  animation: zIconSpin 1.2s linear infinite;
  /* #endif */
}

/* #ifndef APP-NVUE */
@keyframes zIconSpin{
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
/* #endif */
</style>
