<template>
  <view v-if="mounted" class="z-as-root" :style="{ zIndex: String(zIndex) }" @touchmove.stop.prevent="noop">
    <!-- mask -->
    <view
      class="z-as-mask"
      :class="{ 'is-show': showing }"
      :style="maskStyle"
      @tap="onMaskTap"
    ></view>

    <!-- panel -->
    <view
      class="z-as-panel"
      :class="panelClass"
      :style="panelStyle"
      @tap.stop
    >
      <view v-if="showHandle" class="z-as-handle" />

      <view v-if="hasHeader" class="z-as-header">
        <slot name="header">
          <text v-if="title" class="z-as-title">{{ title }}</text>
          <text v-if="message" class="z-as-message">{{ message }}</text>
        </slot>
      </view>

      <view class="z-as-list">
        <template v-for="(it, idx) in normalizedItems" :key="idx">
          <view
            class="z-as-item"
            :class="itemClass(it, idx)"
            :style="itemStyle(it)"
            @tap="onItemTap(it, idx)"
          >
            <slot name="item" :item="it" :index="idx">
              <view class="z-as-item__left">
                <text v-if="it.icon" class="z-as-icon">{{ it.icon }}</text>
              </view>

              <view class="z-as-item__body">
                <view class="z-as-item__row">
                  <text class="z-as-item__label" :style="{ color: itemLabelColor(it) }">{{ it.label }}</text>
                  <text v-if="it.tag" class="z-as-tag" :class="{ 'is-danger': it.danger }">{{ it.tag }}</text>
                </view>
                <text v-if="it.desc" class="z-as-item__desc">{{ it.desc }}</text>
              </view>

              <view class="z-as-item__right">
                <text v-if="it.loading" class="z-as-loading">…</text>
              </view>
            </slot>
          </view>
        </template>
      </view>

      <view v-if="showCancel" class="z-as-footer" :class="{ 'has-safe': safeArea }">
        <slot name="footer">
          <view class="z-as-gap" />
          <view class="z-as-cancel" @tap="onCancelTap">
            <slot name="cancel">
              <text class="z-as-cancel__text">{{ cancelText }}</text>
            </slot>
          </view>
        </slot>
      </view>

      <view v-else :class="{ 'has-safe': safeArea }" class="z-as-safe-space" />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";

type RawItem = string | Record<string, any>;

type ActionItem = {
  label: string;
  value?: any;
  color?: string;
  disabled?: boolean;
  danger?: boolean;
  icon?: string;   // emoji/text icon for demo; can be blank
  desc?: string;
  tag?: string;
  loading?: boolean;
};

const props = withDefaults(defineProps<{
  modelValue: boolean;
  items?: RawItem[];
  // header
  title?: string;
  message?: string;

  // behavior
  closeOnMask?: boolean;
  closeOnSelect?: boolean;

  // ui
  cancelText?: string;
  showCancel?: boolean;
  round?: boolean;
  theme?: "light" | "dark";
  showHandle?: boolean;

  zIndex?: number;
  safeArea?: boolean;

  // style knobs
  maskOpacity?: number; // 0-1
  panelBg?: string;     // override panel bg
  itemHeight?: number;  // rpx
  maxHeight?: string;   // e.g. "70vh"
}>(), {
  modelValue: false,
  items: () => [],
  title: "",
  message: "",
  closeOnMask: true,
  closeOnSelect: true,
  cancelText: "取消",
  showCancel: true,
  round: true,
  theme: "light",
  showHandle: true,
  zIndex: 2000,
  safeArea: true,
  maskOpacity: 0.55,
  panelBg: "",
  itemHeight: 104,
  maxHeight: "70vh"
});

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "select", payload: { index: number; item: ActionItem }): void;
  (e: "cancel"): void;
  (e: "open"): void;
  (e: "close"): void;
}>();

const mounted = ref(false);
const showing = ref(false);
const ANIM_MS = 240;

const hasHeader = computed(() => !!props.title || !!props.message);

const normalizedItems = computed<ActionItem[]>(() => {
  const list = props.items || [];
  return list.map((x: RawItem) => {
    if (typeof x === "string") {
      return { label: x } as ActionItem;
    }
    // normalize keys to our naming
    const label = (x.label ?? x.text ?? x.name ?? "").toString();
    return {
      label,
      value: x.value ?? x.id ?? x.key,
      color: x.color,
      disabled: !!x.disabled,
      danger: !!x.danger,
      icon: x.icon,
      desc: x.desc ?? x.subText ?? x.subtitle,
      tag: x.tag,
      loading: !!x.loading
    } as ActionItem;
  });
});

const maskStyle = computed(() => {
  const opacity = Math.max(0, Math.min(1, Number(props.maskOpacity)));
  return {
    backgroundColor: `rgba(0,0,0,${opacity})`
  };
});

const panelClass = computed(() => ({
  "is-show": showing.value,
  "is-round": props.round,
  "is-dark": props.theme === "dark"
}));

const panelStyle = computed(() => {
  const bg = props.panelBg || (props.theme === "dark" ? "#121212" : "#ffffff");
  return {
    backgroundColor: bg,
    maxHeight: props.maxHeight
  };
});

function itemLabelColor(it: ActionItem) {
  if (it.disabled) return props.theme === "dark" ? "#666" : "#A0A0A0";
  if (it.color) return it.color;
  if (it.danger) return "#E5484D";
  return props.theme === "dark" ? "#EDEDED" : "#1A1A1A";
}

function itemClass(it: ActionItem, idx: number) {
  return {
    "is-disabled": it.disabled,
    "is-danger": it.danger,
    "is-first": idx === 0
  };
}

function itemStyle(_it: ActionItem) {
  return {
    height: `${Number(props.itemHeight)}rpx`
  };
}

function open() {
  if (mounted.value) return;
  mounted.value = true;
  nextTick(() => {
    // microtask + next frame to make transition reliable
    setTimeout(() => {
      showing.value = true;
      emit("open");
    }, 16);
  });
}

function close() {
  if (!mounted.value) return;
  showing.value = false;
  emit("close");
  setTimeout(() => {
    mounted.value = false;
  }, ANIM_MS);
}

function setVisible(v: boolean) {
  emit("update:modelValue", v);
}

function onMaskTap() {
  if (!props.closeOnMask) return;
  emit("cancel");
  setVisible(false);
}

function onCancelTap() {
  emit("cancel");
  setVisible(false);
}

function onItemTap(it: ActionItem, idx: number) {
  if (it.disabled || it.loading) return;
  emit("select", { index: idx, item: it });
  if (props.closeOnSelect) setVisible(false);
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) open();
    else close();
  },
  { immediate: true }
);

function noop() {}

defineExpose({ open: () => setVisible(true), close: () => setVisible(false) });
</script>

<style scoped>
.z-as-root {
  position: fixed;
  inset: 0;
}

.z-as-mask {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 240ms ease;
}

.z-as-mask.is-show {
  opacity: 1;
}

.z-as-panel {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  transform: translate3d(0, 110%, 0);
  transition: transform 240ms ease;
  padding-bottom: 0;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.z-as-panel.is-show {
  transform: translate3d(0, 0, 0);
}

.z-as-panel.is-round {
  border-top-left-radius: 24rpx;
  border-top-right-radius: 24rpx;
}

.z-as-handle {
  width: 76rpx;
  height: 8rpx;
  background: rgba(0,0,0,0.12);
  border-radius: 99rpx;
  margin: 16rpx auto 8rpx;
}

.z-as-panel.is-dark .z-as-handle {
  background: rgba(255,255,255,0.16);
}

.z-as-header {
  padding: 18rpx 28rpx 8rpx;
}

.z-as-title {
  display: block;
  font-size: 30rpx;
  line-height: 40rpx;
  font-weight: 600;
  color: #111;
  text-align: center;
}

.z-as-panel.is-dark .z-as-title {
  color: #F2F2F2;
}

.z-as-message {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  line-height: 34rpx;
  color: rgba(0,0,0,0.55);
  text-align: center;
}

.z-as-panel.is-dark .z-as-message {
  color: rgba(255,255,255,0.65);
}

.z-as-list {
  display: flex;
  flex-direction: column;
}

.z-as-item {
  display: flex;
  align-items: center;
  padding: 0 24rpx;
  position: relative;
}

.z-as-item::after {
  content: "";
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 0;
  height: 1px;
  transform: scaleY(0.5);
  background: rgba(0,0,0,0.08);
}

.z-as-panel.is-dark .z-as-item::after {
  background: rgba(255,255,255,0.10);
}

.z-as-item:active {
  background: rgba(0,0,0,0.04);
}

.z-as-panel.is-dark .z-as-item:active {
  background: rgba(255,255,255,0.06);
}

.z-as-item.is-disabled {
  opacity: 0.55;
}

.z-as-item__left {
  width: 44rpx;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 12rpx;
}

.z-as-icon {
  font-size: 30rpx;
  line-height: 30rpx;
}

.z-as-item__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.z-as-item__row {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.z-as-item__label {
  font-size: 30rpx;
  line-height: 38rpx;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.z-as-tag {
  font-size: 20rpx;
  line-height: 26rpx;
  padding: 4rpx 10rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,0.06);
  color: rgba(0,0,0,0.65);
  flex-shrink: 0;
}

.z-as-panel.is-dark .z-as-tag {
  background: rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.70);
}

.z-as-tag.is-danger {
  background: rgba(229,72,77,0.14);
  color: #E5484D;
}

.z-as-item__desc {
  margin-top: 6rpx;
  font-size: 22rpx;
  line-height: 30rpx;
  color: rgba(0,0,0,0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.z-as-panel.is-dark .z-as-item__desc {
  color: rgba(255,255,255,0.55);
}

.z-as-item__right {
  width: 44rpx;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin-left: 12rpx;
}

.z-as-loading {
  font-size: 28rpx;
  color: rgba(0,0,0,0.45);
}

.z-as-panel.is-dark .z-as-loading {
  color: rgba(255,255,255,0.55);
}

.z-as-footer {
  padding: 0 16rpx 0;
}

.z-as-gap {
  height: 14rpx;
  background: transparent;
}

.z-as-cancel {
  height: 104rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18rpx;
  background: rgba(0,0,0,0.04);
  margin-bottom: 16rpx;
}

.z-as-panel.is-dark .z-as-cancel {
  background: rgba(255,255,255,0.08);
}

.z-as-cancel:active {
  opacity: 0.86;
}

.z-as-cancel__text {
  font-size: 30rpx;
  font-weight: 600;
  color: rgba(0,0,0,0.75);
}

.z-as-panel.is-dark .z-as-cancel__text {
  color: rgba(255,255,255,0.85);
}

.has-safe {
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

.z-as-safe-space {
  height: 0;
}
</style>