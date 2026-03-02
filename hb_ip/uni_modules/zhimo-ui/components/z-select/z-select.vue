<template>
  <view v-if="visible" class="zsel-root" :style="{ zIndex: zIndex, ...sheetVars }">
    <view class="zsel-mask" :class="{ 'is-show': visible }" @tap.stop="onMaskTap"></view>

    <view class="zsel-sheet" :class="{ 'is-show': visible }" :style="sheetStyle" @touchmove.stop.prevent>
      <view class="zsel-header" :style="headerStyle">
        <slot name="header">
          <text class="zsel-title">{{ title }}</text>
          <text v-if="desc" class="zsel-desc-title">{{ desc }}</text>
        </slot>
        <view v-if="showClose" class="zsel-close" @tap.stop="close">
          <text class="zsel-close-text">×</text>
        </view>
      </view>

      <scroll-view class="zsel-body" :scroll-y="true" :show-scrollbar="false" :style="{ maxHeight: maxHeight }">
        <view class="zsel-list" :class="{ 'is-grid': layout === 'grid' }" :style="gridStyle">
          <view
            v-for="(opt, idx) in normalizedOptions"
            :key="opt._key"
            class="zsel-item"
            :class="{
              'is-disabled': opt.disabled,
              'is-active': isSelected(opt),
              'is-grid-item': layout === 'grid'
            }"
            @tap.stop="onItemTap(opt, idx)"
          >
            <template v-if="layout === 'grid'">
              <image v-if="opt.icon" class="zsel-grid-icon" :src="opt.icon" mode="aspectFill" />
              <text class="zsel-grid-label">{{ opt.label }}</text>
              <text v-if="opt.desc" class="zsel-grid-desc">{{ opt.desc }}</text>
              <view v-if="mode !== 'list'" class="zsel-grid-mark">
                <view v-if="multiple" class="zsel-checkbox" :style="checkboxStyle(opt)">
                  <text v-if="isSelected(opt)" class="zsel-check">✓</text>
                </view>
                <view v-else class="zsel-radio" :style="radioStyle(opt)">
                  <view v-if="isSelected(opt)" class="zsel-radio-dot"></view>
                </view>
              </view>
            </template>

            <template v-else>
              <view class="zsel-item-left">
                <image v-if="opt.icon" class="zsel-icon" :src="opt.icon" mode="aspectFill" />
                <view class="zsel-texts">
                  <text class="zsel-label">{{ opt.label }}</text>
                  <text v-if="opt.desc" class="zsel-desc">{{ opt.desc }}</text>
                </view>
              </view>

              <view class="zsel-item-right">
                <template v-if="mode === 'list'">
                  <text class="zsel-arrow">›</text>
                </template>
                <template v-else>
                  <view v-if="multiple" class="zsel-checkbox" :style="checkboxStyle(opt)">
                    <text v-if="isSelected(opt)" class="zsel-check">✓</text>
                  </view>
                  <view v-else class="zsel-radio" :style="radioStyle(opt)">
                    <view v-if="isSelected(opt)" class="zsel-radio-dot"></view>
                  </view>
                </template>
              </view>
            </template>
          </view>
        </view>

        <view v-if="normalizedOptions.length === 0" class="zsel-empty">
          <text class="zsel-empty-text">{{ emptyText }}</text>
        </view>
      </scroll-view>

      <view v-if="showFooter && mode === 'select'" class="zsel-footer">
        <view class="zsel-footer-row">
          <view class="zsel-btn zsel-btn-ghost" :style="cancelBtnStyle" @tap.stop="close">
            <text class="zsel-btn-text zsel-btn-text-ghost" :style="{ color: cancelColor }">{{ cancelText }}</text>
          </view>
          <view class="zsel-btn zsel-btn-primary" :style="primaryBtnStyle" @tap.stop="confirm">
            <text class="zsel-btn-text" :style="{ color: confirmColor }">{{ confirmText }}</text>
          </view>
        </view>
        <view class="zsel-safe" />
      </view>

      <view v-else class="zsel-safe" />
    </view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  /** 弹层显示 */
  visible: { type: Boolean, default: false },

  /** 标题（可用 header 插槽覆盖） */
  title: { type: String, default: "请选择" },
  /** 标题描述（可选） */
  desc: { type: String, default: "" },

  /** 选项：支持 string[] / number[] / object[] */
  options: { type: Array, default: () => [] },

  /** 行为模式：select=底部确认；list=点了直接回传并关闭 */
  mode: { type: String, default: "select" }, // 'select' | 'list'

  /** 布局：list=列表；grid=快捷菜单（图标网格） */
  layout: { type: String, default: "list" }, // 'list' | 'grid'
  /** grid 列数（layout=grid 生效） */
  columns: { type: Number, default: 4 },

  /** 是否多选（仅 mode=select 生效） */
  multiple: { type: Boolean, default: false },

  /** v-model 选中的值：单选 string/number；多选 array */
  modelValue: { type: [String, Number, Array, Object], default: null },

  /** 字段映射 */
  labelKey: { type: String, default: "label" },
  valueKey: { type: String, default: "value" },
  disabledKey: { type: String, default: "disabled" },
  checkedKey: { type: String, default: "checked" },
  iconKey: { type: String, default: "icon" },
  descKey: { type: String, default: "desc" },

  /** 层级样式 */
  zIndex: { type: Number, default: 999 },
  radius: { type: Number, default: 24 },
  maxHeight: { type: String, default: "64vh" },

  /** 颜色（默认浅色系） */
  background: { type: String, default: "#FFFFFF" },
  headerBackground: { type: String, default: "transparent" },
  textColor: { type: String, default: "#1C1C1C" },
  subTextColor: { type: String, default: "#7A7A7A" },
  itemBackground: { type: String, default: "#F6F7F9" },
  itemActiveBackground: { type: String, default: "#EEF4FF" },
  borderColor: { type: String, default: "#E7E7E7" },
  maskOpacity: { type: Number, default: 0.35 },

  /** 勾选颜色 */
  activeColor: { type: String, default: "#5B8CFF" },

  /** 底部按钮 */
  showFooter: { type: Boolean, default: true },
  confirmBackground: { type: String, default: "#5B8CFF" },
  confirmColor: { type: String, default: "#FFFFFF" },
  confirmText: { type: String, default: "确认" },

  cancelBackground: { type: String, default: "#F2F3F5" },
  cancelColor: { type: String, default: "#1C1C1C" },
  cancelText: { type: String, default: "取消" },

  /** 是否显示右上角关闭 */
  showClose: { type: Boolean, default: true },

  /** 点击遮罩是否关闭 */
  closeOnMask: { type: Boolean, default: true },

  /** 空列表提示 */
  emptyText: { type: String, default: "暂无可选项" }
});

const emit = defineEmits([
  "update:visible",
  "update:modelValue",
  "close",
  "confirm",
  "item-click"
]);

const internal = ref(normalizeInitialValue(props.modelValue));

watch(
  () => props.modelValue,
  (v) => {
    internal.value = normalizeInitialValue(v);
  }
);

watch(
  () => props.visible,
  (v) => {
    if (!v) return;

    // 打开时：如果没传 v-model，但 options 有 checked，补默认值
    const preset = pickCheckedFromOptions();
    const noValue =
      props.modelValue == null ||
      (Array.isArray(props.modelValue) && props.modelValue.length === 0);

    if (preset != null && noValue) {
      internal.value = normalizeInitialValue(preset);
      emit("update:modelValue", internal.value);
    }
  }
);

const normalizedOptions = computed(() => {
  const list = Array.isArray(props.options) ? props.options : [];
  return list.map((o, idx) => {
    if (typeof o === "string" || typeof o === "number") {
      return {
        _key: "s_" + idx + "_" + String(o),
        label: String(o),
        value: o,
        disabled: false,
        checked: false,
        icon: "",
        desc: ""
      };
    }
    const label = safeGet(o, props.labelKey, "");
    const value = safeGet(o, props.valueKey, label);
    return {
      _key: "o_" + idx + "_" + String(value),
      raw: o,
      label: String(label),
      value: value,
      disabled: !!safeGet(o, props.disabledKey, false),
      checked: !!safeGet(o, props.checkedKey, false),
      icon: safeGet(o, props.iconKey, ""),
      desc: safeGet(o, props.descKey, "")
    };
  });
});

const sheetVars = computed(() => ({
  "--zsel-mask-bg": "rgba(0,0,0," + props.maskOpacity + ")",
  "--zsel-bg": props.background,
  "--zsel-text": props.textColor,
  "--zsel-subtext": props.subTextColor,
  "--zsel-item-bg": props.itemBackground,
  "--zsel-item-active-bg": props.itemActiveBackground,
  "--zsel-border": props.borderColor
}));

const sheetStyle = computed(() => ({
  borderTopLeftRadius: props.radius + "rpx",
  borderTopRightRadius: props.radius + "rpx",
  background: props.background
}));

const headerStyle = computed(() => ({
  background: props.headerBackground
}));

const gridStyle = computed(() => {
  if (props.layout !== "grid") return {};
  const c = props.columns > 0 ? props.columns : 4;
  return { gridTemplateColumns: "repeat(" + c + ", 1fr)" };
});

const primaryBtnStyle = computed(() => ({
  background: props.confirmBackground
}));

const cancelBtnStyle = computed(() => ({
  background: props.cancelBackground
}));

function normalizeInitialValue(v) {
  if (props.multiple) {
    if (Array.isArray(v)) return v.slice();
    if (v == null) return [];
    return [v];
  }
  if (Array.isArray(v)) return v.length ? v[0] : null;
  return v == null ? null : v;
}

function safeGet(obj, key, def) {
  try {
    if (!obj || typeof obj !== "object") return def;
    const v = obj[key];
    return v === undefined ? def : v;
  } catch (e) {
    return def;
  }
}

function pickCheckedFromOptions() {
  const list = normalizedOptions.value;
  const checked = list
    .filter((x) => x.checked && !x.disabled)
    .map((x) => x.value);
  if (props.multiple) return checked;
  return checked.length ? checked[0] : null;
}

function isSelected(opt) {
  const v = internal.value;
  if (props.multiple) {
    return Array.isArray(v) && v.some((x) => looselyEqual(x, opt.value));
  }
  return looselyEqual(v, opt.value);
}

function looselyEqual(a, b) {
  return String(a) === String(b);
}

function onItemTap(opt, idx) {
  if (opt.disabled) return;

  if (props.mode === "list") {
    emit("item-click", {
      value: opt.value,
      label: opt.label,
      index: idx,
      option: opt.raw != null ? opt.raw : opt
    });
    emit("update:visible", false);
    emit("close");
    return;
  }

  if (props.multiple) {
    const cur = Array.isArray(internal.value) ? internal.value.slice() : [];
    const pos = cur.findIndex((x) => looselyEqual(x, opt.value));
    if (pos >= 0) cur.splice(pos, 1);
    else cur.push(opt.value);
    internal.value = cur;
    emit("update:modelValue", cur);
  } else {
    internal.value = opt.value;
    emit("update:modelValue", opt.value);
  }
}

function confirm() {
  emit("confirm", internal.value);
  emit("update:visible", false);
  emit("close");
}

function close() {
  emit("update:visible", false);
  emit("close");
}

function onMaskTap() {
  if (props.closeOnMask) close();
}

function checkboxStyle(opt) {
  const on = isSelected(opt);
  return {
    borderColor: on ? props.activeColor : props.borderColor,
    background: on ? props.activeColor : "transparent"
  };
}
function radioStyle(opt) {
  const on = isSelected(opt);
  return {
    borderColor: on ? props.activeColor : props.borderColor
  };
}
</script>

<style>
.zsel-root {
  position: fixed;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
}

.zsel-mask {
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  bottom: 0;
  background: var(--zsel-mask-bg, rgba(0, 0, 0, 0.35));
  opacity: 0;
  transition: opacity 180ms ease;
}
.zsel-mask.is-show {
  opacity: 1;
}

.zsel-sheet {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translateY(100%);
  transition: transform 220ms ease;
  box-shadow: 0 -12rpx 40rpx rgba(0, 0, 0, 0.18);
  overflow: hidden;
  background: var(--zsel-bg, #fff);
}
.zsel-sheet.is-show {
  transform: translateY(0);
}

.zsel-header {
  position: relative;
  padding: 22rpx 28rpx 16rpx;
}
.zsel-title {
  display: block;
  text-align: center;
  font-size: 30rpx;
  color: var(--zsel-text, #1c1c1c);
  font-weight: 650;
}
.zsel-desc-title {
  display: block;
  text-align: center;
  font-size: 24rpx;
  color: var(--zsel-subtext, #7a7a7a);
  margin-top: 6rpx;
}

.zsel-close {
  position: absolute;
  right: 12rpx;
  top: 6rpx;
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.zsel-close-text {
  font-size: 44rpx;
  color: rgba(0, 0, 0, 0.35);
  line-height: 1;
}

.zsel-body {
  padding: 10rpx 16rpx 14rpx;
  box-sizing: border-box;
}

.zsel-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}
.zsel-list.is-grid {
  display: grid;
  gap: 14rpx;
  align-items: stretch;
}

.zsel-item {
  padding: 20rpx 18rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--zsel-item-bg, #f6f7f9);
  border: 2rpx solid transparent;
  box-sizing: border-box;
}
.zsel-item.is-active {
  background: var(--zsel-item-active-bg, #eef4ff);
  border-color: rgba(91, 140, 255, 0.35);
}
.zsel-item.is-disabled {
  opacity: 0.45;
}
.zsel-item-left {
  display: flex;
  align-items: center;
  gap: 14rpx;
}
.zsel-icon {
  width: 40rpx;
  height: 40rpx;
  border-radius: 12rpx;
}
.zsel-texts {
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.zsel-label {
  font-size: 28rpx;
  color: var(--zsel-text, #1c1c1c);
  line-height: 1.2;
}
.zsel-desc {
  font-size: 24rpx;
  color: var(--zsel-subtext, #7a7a7a);
  line-height: 1.2;
}

.zsel-item-right {
  display: flex;
  align-items: center;
  gap: 12rpx;
}
.zsel-arrow {
  font-size: 38rpx;
  color: rgba(0, 0, 0, 0.35);
  margin-left: 8rpx;
}

.zsel-checkbox {
  width: 40rpx;
  height: 40rpx;
  border-radius: 12rpx;
  border: 2rpx solid var(--zsel-border, #e7e7e7);
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: center;
}
.zsel-check {
  color: #fff;
  font-size: 26rpx;
  line-height: 1;
}

.zsel-radio {
  position: relative;
  width: 40rpx;
  height: 40rpx;
  border-radius: 999rpx;
  border: 2rpx solid var(--zsel-border, #e7e7e7);
  box-sizing: border-box;
}
.zsel-radio-dot {
  position: absolute;
  width: 18rpx;
  height: 18rpx;
  border-radius: 999rpx;
  background: #5b8cff;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.zsel-empty {
  padding: 28rpx 16rpx 20rpx;
  text-align: center;
}
.zsel-empty-text {
  font-size: 26rpx;
  color: var(--zsel-subtext, #7a7a7a);
}

.zsel-footer {
  padding: 14rpx 16rpx 10rpx;
  border-top: 2rpx solid rgba(0, 0, 0, 0.04);
}
.zsel-footer-row {
  display: flex;
  gap: 14rpx;
}
.zsel-btn {
  flex: 1;
  height: 86rpx;
  border-radius: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}
.zsel-btn-ghost {
  background: #f2f3f5;
}
.zsel-btn-primary {
  background: #5b8cff;
}
.zsel-btn-text {
  font-size: 28rpx;
  font-weight: 650;
}
.zsel-btn-text-ghost {
  font-weight: 600;
}

.zsel-safe {
  height: env(safe-area-inset-bottom);
}

/* grid layout */
.zsel-item.is-grid-item {
  flex-direction: column;
  justify-content: center;
  padding: 18rpx 12rpx;
  min-height: 160rpx;
}
.zsel-grid-icon {
  width: 56rpx;
  height: 56rpx;
  border-radius: 16rpx;
  margin-bottom: 10rpx;
}
.zsel-grid-label {
  font-size: 26rpx;
  color: var(--zsel-text, #1c1c1c);
  font-weight: 600;
  text-align: center;
  line-height: 1.2;
}
.zsel-grid-desc {
  font-size: 22rpx;
  color: var(--zsel-subtext, #7a7a7a);
  margin-top: 6rpx;
  text-align: center;
  line-height: 1.2;
}
.zsel-grid-mark {
  margin-top: 10rpx;
}
</style>
