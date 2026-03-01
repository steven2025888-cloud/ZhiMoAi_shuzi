<template>
  <!-- 多行/换行模式：用 view + 每行一个 text，保证任何端都换行 -->
  <view v-if="isMultiline" class="z-text-multi">
    <view v-for="(line, idx) in splitLines" :key="idx" class="z-text-multi__row">
      <text
        class="z-text"
        :class="classListNoClamp"
        :selectable="selectable"
        :style="inlineStyle"
      >
        {{ line === "" ? " " : line }}
      </text>
    </view>
  </view>

  <!-- 单行模式：保持最轻量 -->
  <text
    v-else
    class="z-text"
    :class="classList"
    :selectable="selectable"
    :style="inlineStyle"
  >
    <slot>{{ text }}</slot>
  </text>
</template>

<script setup>
import { computed, useSlots } from "vue";

/**
 * z-text（Vue3）
 * - 字号/字重/颜色/对齐/多行省略/字体
 * - ✅ 修复：换行在不同端不生效的问题（改为多行时逐行渲染）
 * - ✅ 修复：字体不生效常见原因（配合 styles/fonts-local.css 相对路径）
 */
const props = defineProps({
  /** 文本内容（也可直接用 slot） */
  text: { type: String, default: "" },

  /** 预设样式：body / sub / title / caption */
  variant: { type: String, default: "body" },

  /** 字体：system / inter / roboto / mono */
  family: { type: String, default: "system" },

  /** 颜色（优先级最高） */
  color: { type: String, default: "" },

  /** 字号（rpx） */
  size: { type: [Number, String], default: "" },

  /** 字重（100-900 或 normal/bold） */
  weight: { type: [Number, String], default: "" },

  /** 行高（可传数字或带单位字符串） */
  lineHeight: { type: [Number, String], default: "" },

  /** 对齐：left/center/right */
  align: { type: String, default: "" },

  /** 最多显示几行（0/空 = 不限制；>=1 开启省略） */
  lines: { type: [Number, String], default: 0 },

  /** 是否可复制 */
  selectable: { type: Boolean, default: false },

  /** 强制按 \n 换行显示（推荐） */
  pre: { type: Boolean, default: false },
});

const slots = useSlots();

/** 只要 text/slot 含换行，就走多行渲染 */
const slotText = computed(() => {
  // slot 里不是纯文本时无法可靠取值，所以这里只用 props.text 判断更稳
  return "";
});

const rawText = computed(() => props.text || "");

/** 是否启用多行渲染 */
const isMultiline = computed(() => {
  if (props.pre) return true;
  return rawText.value.includes("\n");
});

/** 将文本按 \n 分割 */
const splitLines = computed(() => rawText.value.split(/\r?\n/));

const classListBase = computed(() => {
  const fam = (props.family || "system").toLowerCase();
  return [
    `z-text--${props.variant || "body"}`,
    fam === "inter" ? "z-text--inter" : "",
    fam === "roboto" ? "z-text--roboto" : "",
    fam === "mono" ? "z-text--mono" : "",
  ].filter(Boolean);
});

const classList = computed(() => {
  return [
    ...classListBase.value,
    Number(props.lines || 0) > 0 ? "z-text--clamp" : "",
  ].filter(Boolean);
});

/** 多行模式不做 clamp（否则每行都 clamp 没意义） */
const classListNoClamp = computed(() => classListBase.value);

function toRpx(v) {
  if (v === "" || v === null || v === undefined) return "";
  const s = String(v);
  return /[a-z%]/i.test(s) ? s : `${s}rpx`;
}

const inlineStyle = computed(() => {
  const style = {};
  if (props.color) style.color = props.color;
  if (props.size !== "") style.fontSize = toRpx(props.size);
  if (props.weight !== "") style.fontWeight = String(props.weight);
  if (props.lineHeight !== "") style.lineHeight = toRpx(props.lineHeight);
  if (props.align) style.textAlign = props.align;

  const ln = Number(props.lines || 0);
  if (ln > 0) style["-webkit-line-clamp"] = String(ln);

  return style;
});
</script>

<style scoped>
/* 字体文件已在 App.vue 中全局导入，这里不需要重复导入 */

/* 基础：整体字小一点 */
.z-text{
  font-family: var(--ui-font-sans);
  color: #111827;
  font-size: 26rpx;
  line-height: 1.55;
}

.z-text--body{ font-size: 26rpx; line-height: 1.55; }

.z-text--sub{
  font-size: 22rpx;
  line-height: 1.55;
  color: rgba(17,24,39,.72);
}

.z-text--caption{
  font-size: 20rpx;
  line-height: 1.55;
  color: rgba(17,24,39,.62);
}

.z-text--title{
  font-size: 34rpx;
  font-weight: 800;
  line-height: 1.25;
}

/* 字体切换（你已放入本地字体文件时才会明显变化） */
.z-text--inter{ font-family: "Inter", var(--ui-font-sans); }
.z-text--roboto{ font-family: "Roboto", var(--ui-font-sans); }
.z-text--mono{ font-family: var(--ui-font-mono); }

/* 多行省略（H5/小程序更稳；nvue 支持差异大） */
.z-text--clamp{
  /* #ifndef APP-NVUE */
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  /* #endif */
}

/* 多行渲染容器 */
.z-text-multi{ display: flex; flex-direction: column; }
.z-text-multi__row{ }
</style>
