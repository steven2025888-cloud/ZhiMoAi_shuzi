<template>
  <view class="ui-bg" :style="wrapStyle">
    <image
      v-if="image"
      class="ui-bg__img"
      :src="image"
      :mode="imgMode"
      :style="imgStyle"
    />
    <view v-if="overlay" class="ui-bg__overlay" :style="{ background: overlay }"></view>
    <slot />
  </view>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  /** 背景图片地址 */
  image: { type: String, default: "" },

  /** 容器背景（无图片时也可显示渐变/纯色） */
  background: { type: String, default: "transparent" },

  /** 层级（默认在底层） */
  zIndex: { type: [Number, String], default: -1 },

  /** 定位方式：fixed / absolute */
  position: { type: String, default: "fixed" },

  /** 图片显示方式：cover / contain / fill（会映射到 uni image mode） */
  fit: { type: String, default: "cover" },

  /** 图片透明度 */
  opacity: { type: [Number, String], default: 1 },

  /** 覆盖层（可做蒙版/渐变），例如：linear-gradient(...) */
  overlay: { type: String, default: "" },

  /** H5 生效：模糊（px），小程序/APP 会被忽略 */
  blur: { type: [Number, String], default: 0 },
});

const imgMode = computed(() => {
  const f = (props.fit || "").toLowerCase();
  if (f === "contain") return "aspectFit";
  if (f === "fill") return "scaleToFill";
  return "aspectFill"; // cover
});

const wrapStyle = computed(() => ({
  position: props.position === "absolute" ? "absolute" : "fixed",
  background: props.background,
  zIndex: props.zIndex,
}));

const imgStyle = computed(() => {
  // #ifndef APP-NVUE
  const blur = Number(props.blur || 0);
  return {
    opacity: String(props.opacity),
    filter: blur > 0 ? `blur(${blur}px)` : "none",
    transform: blur > 0 ? "scale(1.06)" : "none", // 模糊时略放大避免边缘露底
  };
  // #endif
  // #ifdef APP-NVUE
  return { opacity: String(props.opacity) };
  // #endif
});
</script>

<style scoped>
.ui-bg{
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  /* #ifndef APP-NVUE */
  width: 100%;
  height: 100%;
  /* #endif */
}

.ui-bg__img{
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  /* #ifndef APP-NVUE */
  width: 100%;
  height: 100%;
  display: block;
  /* #endif */
}

.ui-bg__overlay{
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
}
</style>
