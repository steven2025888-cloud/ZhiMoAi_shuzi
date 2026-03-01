<template>
  <view
    class="z-banner-curve"
    ref="rootRef"
    :style="wrapStyle"
    @tap="onTap"
  >
    <!-- #ifndef APP-NVUE -->
    <view class="z-banner-curve__inner" :style="innerStyleWeb">
      <slot />
    </view>
    <!-- #endif -->

    <!-- #ifdef APP-NVUE -->
    <view class="z-banner-curve__inner" :style="innerStyleNvue">
      <slot />
    </view>
    <!-- #endif -->
  </view>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

// #ifdef APP-NVUE
const dom = uni.requireNativePlugin("dom");
// #endif

const emit = defineEmits(["click"]);

const props = defineProps({
  /** 高度（rpx） */
  height: { type: [Number, String], default: 400 },

  /**
   * 弧度比率：
   * - H5/小程序：最小 1.2（越大弧度越小）
   * - nvue：最小 1.5
   */
  ratio: { type: [Number, String], default: 1.2 },

  /** 背景色/渐变 (CSS background) */
  background: { type: String, default: "" },

  /** 上下外边距（rpx） */
  marginTop: { type: [Number, String], default: 0 },
  marginBottom: { type: [Number, String], default: 0 },
});

const rootRef = ref(null);

// nvue: 容器实际宽度（px）
const bannerWidthPx = ref(375);

const wrapStyle = computed(() => ({
  height: `${props.height}rpx`,
  marginTop: `${props.marginTop}rpx`,
  marginBottom: `${props.marginBottom}rpx`,
}));

const ratioNum = computed(() => {
  const n = Number(props.ratio || 0);
  // #ifdef APP-NVUE
  return n < 1.5 ? 1.5 : n;
  // #endif
  // #ifndef APP-NVUE
  return n < 1.2 ? 1.2 : n;
  // #endif
});

// web: 用百分比做“超宽圆弧”
const widthPercent = computed(() => 100 * ratioNum.value);
const padPercent = computed(() => (widthPercent.value - 100) / 2);

const innerStyleWeb = computed(() => ({
  background: props.background,
  height: `${props.height}rpx`,
  width: `${widthPercent.value}%`,
  paddingLeft: `${padPercent.value}%`,
  paddingRight: `${padPercent.value}%`,
  left: `-${padPercent.value}%`,
}));

// nvue: 用 px 计算大圆弧
const widthPx = computed(() => {
  let w = Math.ceil(bannerWidthPx.value * ratioNum.value);
  // 保证偶数，避免某些机型边缘抖动
  w = w % 2 === 0 ? w : w + 1;
  return w;
});

const padPx = computed(() => (widthPx.value - bannerWidthPx.value) / 2);

const innerStyleNvue = computed(() => ({
  background: props.background,
  height: `${widthPx.value}px`,
  width: `${widthPx.value}px`,
  paddingLeft: `${padPx.value}px`,
  paddingRight: `${padPx.value}px`,
  left: `-${padPx.value}px`,
}));

function onTap() {
  emit("click", {});
}

// #ifdef APP-NVUE
function measure() {
  if (!rootRef.value) return;
  dom.getComponentRect(rootRef.value, (ret) => {
    const size = ret && ret.size;
    if (size && size.width) bannerWidthPx.value = size.width;
  });
}

onMounted(() => {
  setTimeout(() => measure(), 50);
});

watch(ratioNum, () => {
  setTimeout(() => measure(), 0);
});
// #endif
</script>

<style scoped>
.z-banner-curve{
  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  /* #endif */
  position: relative;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
}

.z-banner-curve__inner{
  position: absolute;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  top: 0;
  box-sizing: border-box;
  z-index: 1;
  border-radius: 0 0 50% 50%;
  /* #endif */

  /* #ifdef APP-NVUE */
  bottom: 0;
  border-bottom-right-radius: 10000px;
  border-bottom-left-radius: 10000px;
  justify-content: flex-end;
  /* #endif */
}
</style>
