<template>
  <view
    class="z-footer"
    :class="[fixedVal ? 'z-footer--fixed' : '']"
    :style="wrapStyle"
  >
    <view v-if="linkList.length" class="z-footer__links">
      <navigator
        v-for="(item, idx) in linkList"
        :key="idx"
        class="z-footer__link"
        hover-class="z-footer__link--hover"
        hover-stop-propagation
        :open-type="item.openType || 'navigate'"
        :url="item.url"
        :delta="item.delta"
      >
        <text
          class="z-footer__link-text"
          :style="linkTextStyle(item, idx)"
        >{{ item.text }}</text>
      </navigator>
    </view>

    <view
      class="z-footer__text"
      :class="[{ 'z-footer__safearea': safeArea } , { 'z-footer__safe-nvue': isSafeNvue }]"
    >
      <text :style="textStyle">{{ text }}</text>
    </view>
  </view>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";

// #ifdef APP-NVUE
const dom = uni.requireNativePlugin("dom");
// #endif

/**
 * z-footer（Vue3）
 * - links：链接列表（兼容旧字段 navigate）
 * - text：底部文本
 * - textColor / textSize：文本样式
 * - background：背景
 * - dividerColor：分隔线颜色（nvue 边框/非 nvue 伪元素）
 * - fixed：固定到底部（兼容旧字段 isFixed）
 * - bottom：底部偏移（rpx）
 * - safeArea：是否适配安全区
 */
const props = defineProps({
  // 新：更大众
  links: { type: Array, default: () => [] },

  // 兼容：旧字段
  navigate: { type: Array, default: undefined },

  text: { type: String, default: "" },

  textColor: { type: String, default: "#B2B2B2" },
  textSize: { type: [Number, String], default: 24 },

  background: { type: String, default: "transparent" },

  dividerColor: { type: String, default: "#B2B2B2" },

  // 新：更大众
  fixed: { type: Boolean, default: false },
  // 兼容：旧字段
  isFixed: { type: Boolean, default: undefined },

  bottom: { type: [Number, String], default: 0 },

  safeArea: { type: Boolean, default: true },

  /** 链接默认颜色（不传就用 #465CFF） */
  linkColor: { type: String, default: "#465CFF" },
});

const linkList = computed(() => {
  // 优先 links，其次兼容 navigate
  const v = props.links && props.links.length ? props.links : (props.navigate || []);
  return Array.isArray(v) ? v : [];
});

const fixedVal = computed(() => (props.isFixed !== undefined ? props.isFixed : props.fixed));

const wrapStyle = computed(() => ({
  background: props.background,
  bottom: `${props.bottom}rpx`,
  "--z-divider": props.dividerColor,
}));

const textStyle = computed(() => ({
  color: props.textColor,
  fontSize: `${props.textSize}rpx`,
}));

function linkTextStyle(item, idx) {
  const size = item.size || 28;
  const color = item.color || props.linkColor;
  const isLast = idx === linkList.value.length - 1;
  return {
    color,
    fontSize: `${size}rpx`,
    lineHeight: `${size}rpx`,
    // nvue 需要 border-right-color
    borderColor: props.dividerColor,
    // 非 nvue 用伪元素分隔，这里只控制最后一项去边
    ...(isLast ? { borderRightWidth: 0 } : {}),
  };
}

/**
 * ✅ 修复：部分端 iPhone 安全区适配
 * - APP-NVUE / MP-TOUTIAO：用系统信息判断 safeAreaInsets.bottom
 */
const isSafeNvue = ref(false);

function detectSafeBottom() {
  if (!props.safeArea) return false;
  const res = uni.getSystemInfoSync();
  if (res && res.safeAreaInsets && res.safeAreaInsets.bottom > 0) return true;

  // 兜底：型号判断（只用于少数端）
  const model = (res.model || "").replace(/\s/g, "").toLowerCase();
  const newModel = model.split("<")[0];
  const models = ["iphonex", "iphonexr", "iphonexsmax"];
  for (let i = 11; i < 20; i++) {
    models.push(`iphone${i}`, `iphone${i}mini`, `iphone${i}pro`, `iphone${i}promax`);
  }
  return models.includes(model) || models.includes(newModel);
}

onMounted(() => {
  // #ifdef APP-NVUE || MP-TOUTIAO
  isSafeNvue.value = detectSafeBottom();
  // #endif
});
</script>

<style scoped>
.z-footer{
  flex: 1;
  /* #ifndef APP-NVUE */
  width: 100%;
  box-sizing: border-box;
  word-break: break-all;
  /* #endif */
  overflow: hidden;
  padding: 32rpx;
}

.z-footer--fixed{
  position: fixed;
  z-index: 99;
  left: 0;
  right: 0;
  /* #ifndef APP-NVUE */
  left: constant(safe-area-inset-left);
  left: env(safe-area-inset-left);
  right: constant(safe-area-inset-right);
  right: env(safe-area-inset-right);
  /* #endif */
}

.z-footer__links{
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.z-footer__link{
  position: relative;
  line-height: 1;
}

.z-footer__link-text{
  padding: 0 18rpx;
  /* #ifdef APP-NVUE */
  border-right-width: 0.5px;
  border-right-style: solid;
  /* #endif */
  font-weight: 400;
}

/* 非 nvue：用伪元素做分隔线 */
 /* #ifndef APP-NVUE */
.z-footer__link::before{
  content: " ";
  position: absolute;
  right: 0;
  top: 4rpx;
  width: 1px;
  bottom: 4rpx;
  border-right: 1px solid var(--z-divider, #B2B2B2);
  transform-origin: 100% 0;
  transform: scaleX(0.5);
}
.z-footer__link:last-child::before{
  border-right: 0 !important;
}
 /* #endif */

.z-footer__link--hover{ opacity: 0.5; }

.z-footer__text{
  flex: 1;
  /* #ifdef APP-NVUE */
  flex-direction: row;
  justify-content: center;
  flex-wrap: wrap;
  /* #endif */
  line-height: 1;
  text-align: center;
  padding-top: 8rpx;
  font-weight: 400;
}

/* #ifndef APP-NVUE || MP-TOUTIAO */
.z-footer__safearea{
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}
/* #endif */

/* #ifdef APP-NVUE || MP-TOUTIAO */
.z-footer__safe-nvue{
  padding-bottom: 34px;
}
/* #endif */
</style>
