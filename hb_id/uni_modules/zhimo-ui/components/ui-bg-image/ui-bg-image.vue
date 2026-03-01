<template>
  <view class="ui-bg" :style="wrapStyle">
    <image
      v-if="image"
      class="ui-bg__img"
      :src="image"
      :mode="imgMode"
      :style="imgStyle"
    />
    <view v-if="overlay" class="ui-bg__overlay" :style="overlayStyle"></view>
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

  /** 定位方式：fixed / absolute */
  position: { type: String, default: "fixed" },

  /** 层级（默认在底层） */
  zIndex: { type: [Number, String], default: -1 },

  /** 图片显示方式：cover / contain / fill（会映射到 uni image mode） */
  fit: { type: String, default: "cover" },

  /** 图片透明度 */
  opacity: { type: [Number, String], default: 1 },

  /** 覆盖层（可做蒙版/渐变），例如：linear-gradient(...) */
  overlay: { type: String, default: "" },

  /** 覆盖层透明度（overlay 存在时生效） */
  overlayOpacity: { type: [Number, String], default: 1 },

  /** H5 生效：模糊（px），小程序/APP 会被忽略 */
  blur: { type: [Number, String], default: 0 },

  /** 圆角（rpx），默认 0；如果你只想做卡片背景可用 */
  radius: { type: [Number, String], default: 0 },

  /** 内边距（rpx），可快速给 slot 内容留空隙 */
  padding: { type: [Number, String], default: 0 },

  /** 是否撑满全屏（true=0,0,0,0；false=不设置四边，方便你自己布局） */
  full: { type: Boolean, default: true },

  /** H5 生效：mix-blend-mode，例如 multiply / screen / overlay 等 */
  blendMode: { type: String, default: "" },
});

const imgMode = computed(() => {
  const f = (props.fit || "").toLowerCase();
  if (f === "contain") return "aspectFit";
  if (f === "fill") return "scaleToFill";
  return "aspectFill"; // cover
});

const wrapStyle = computed(() => {
  const style = {
    position: props.position === "absolute" ? "absolute" : "fixed",
    background: props.background,
    zIndex: props.zIndex,
    borderRadius: `${props.radius}rpx`,
    padding: `${props.padding}rpx`,
    overflow: props.radius && Number(props.radius) > 0 ? "hidden" : "visible",
  };
  if (props.full) {
    style.left = 0;
    style.top = 0;
    style.right = 0;
    style.bottom = 0;
    // #ifndef APP-NVUE
    style.width = "100%";
    style.height = "100%";
    // #endif
  }
  return style;
});

const imgStyle = computed(() => {
  // #ifndef APP-NVUE
  const blur = Number(props.blur || 0);
  const style = {
    opacity: String(props.opacity),
    filter: blur > 0 ? `blur(${blur}px)` : "none",
    transform: blur > 0 ? "scale(1.06)" : "none",
  };
  if (props.blendMode) style.mixBlendMode = props.blendMode;
  return style;
  // #endif
  // #ifdef APP-NVUE
  return { opacity: String(props.opacity) };
  // #endif
});

const overlayStyle = computed(() => ({
  background: props.overlay,
  opacity: String(props.overlayOpacity),
}));
</script>

<style scoped>
.ui-bg{
  box-sizing: border-box;
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
