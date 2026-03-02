<template>
  <view class="zsl" :class="{ 'is-disabled': disabled }">
    <view v-if="showValue" class="zsl-values">
      <text class="zsl-value">{{ displayStart }}</text>
      <text v-if="range" class="zsl-sep">—</text>
      <text v-if="range" class="zsl-value">{{ displayEnd }}</text>
    </view>

    <view
      ref="trackRef"
      class="zsl-track"
      :style="trackStyle"
      @touchstart.stop.prevent="onTouchStart"
      @touchmove.stop.prevent="onTouchMove"
      @touchend.stop.prevent="onTouchEnd"
      @touchcancel.stop.prevent="onTouchEnd"
      @mousedown.stop.prevent="onMouseDown"
    >
      <view class="zsl-rail" :style="railStyle" />
      <view class="zsl-fill" :style="fillStyle" />

      <!-- thumbs -->
      <view
        class="zsl-thumb"
        :class="{ 'is-active': activeThumb === 'start' }"
        :style="thumbStartStyle"
        @touchstart.stop.prevent="(e) => onThumbStart(e, 'start')"
        @touchmove.stop.prevent="onTouchMove"
        @touchend.stop.prevent="onTouchEnd"
        @touchcancel.stop.prevent="onTouchEnd"
        @mousedown.stop.prevent="(e) => onThumbMouseDown(e, 'start')"
      />
      <view
        v-if="range"
        class="zsl-thumb"
        :class="{ 'is-active': activeThumb === 'end' }"
        :style="thumbEndStyle"
        @touchstart.stop.prevent="(e) => onThumbStart(e, 'end')"
        @touchmove.stop.prevent="onTouchMove"
        @touchend.stop.prevent="onTouchEnd"
        @touchcancel.stop.prevent="onTouchEnd"
        @mousedown.stop.prevent="(e) => onThumbMouseDown(e, 'end')"
      />
    </view>

    <view v-if="dragging" class="zsl-mask" @touchmove.stop.prevent="onTouchMove" @touchend.stop.prevent="onTouchEnd" @touchcancel.stop.prevent="onTouchEnd" />

    <view v-if="marks && marks.length" class="zsl-marks" :style="{ width: cssWidth(width) }">
      <view
        v-for="(m, i) in marks"
        :key="i"
        class="zsl-mark"
        :style="{ left: percentFor(m.value) + '%' }"
      >
        <view class="zsl-dot" />
        <text class="zsl-label">{{ m.label }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch, getCurrentInstance } from "vue";

type Mark = { value: number; label?: string };

const props = defineProps({
  modelValue: { type: [Number, Array] as any, default: 0 }, // number | [number, number]
  range: { type: Boolean, default: false },

  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },

  width: { type: [Number, String], default: 260 }, // px or any css unit string
  height: { type: [Number, String], default: 4 }, // rail height
  radius: { type: [Number, String], default: 999 },

  railColor: { type: String, default: "#E6E8EC" },
  fillColor: { type: String, default: "#4D7CFE" },

  thumbSize: { type: [Number, String], default: 22 },
  thumbColor: { type: String, default: "#FFFFFF" },
  thumbBorder: { type: String, default: "1px solid rgba(0,0,0,0.08)" },
  thumbShadow: { type: String, default: "0 2px 8px rgba(0,0,0,0.12)" },

  disabled: { type: Boolean, default: false },
  showValue: { type: Boolean, default: false },
  formatter: { type: Function as any, default: null }, // (v:number)=>string

  marks: { type: Array as any, default: () => [] as Mark[] },
});

const emit = defineEmits<{
  (e: "update:modelValue", v: number | [number, number]): void;
  (e: "changing", payload: { value: number | [number, number] }): void;
  (e: "change", payload: { value: number | [number, number] }): void;
}>();

const trackRef = ref<any>(null);

// internal values
const startVal = ref<number>(props.min);
const endVal = ref<number>(props.max);
const activeThumb = ref<"start" | "end" | null>(null);
const dragging = ref(false);
const dragOffsetX = ref(0);

const rect = ref<{ left: number; width: number } | null>(null);
let removeMouseMove: null | (() => void) = null;
let removeMouseUp: null | (() => void) = null;

function clamp(n: number) {
  return Math.min(props.max, Math.max(props.min, n));
}
function snap(n: number) {
  const step = Math.max(1e-9, Number(props.step || 1));
  const v = Math.round((n - props.min) / step) * step + props.min;
  // fix float noise
  return Number(v.toFixed(10));
}
function normalizeRange(a: number, b: number) {
  const s = Math.min(a, b);
  const e = Math.max(a, b);
  return [s, e] as [number, number];
}

function readModel() {
  if (props.range) {
    const arr = Array.isArray(props.modelValue) ? props.modelValue : [props.min, props.max];
    const s = snap(clamp(Number(arr[0] ?? props.min)));
    const e = snap(clamp(Number(arr[1] ?? props.max)));
    const [ns, ne] = normalizeRange(s, e);
    startVal.value = ns;
    endVal.value = ne;
  } else {
    const v = snap(clamp(Number(Array.isArray(props.modelValue) ? props.modelValue[0] : props.modelValue)));
    startVal.value = v;
  }
}

watch(
  () => props.modelValue,
  () => readModel(),
  { immediate: true, deep: true }
);

watch(
  () => [props.min, props.max, props.step, props.range],
  () => {
    readModel();
    nextTick(measure);
  }
);

onMounted(() => {
  nextTick(measure);
});

onBeforeUnmount(() => {
  cleanupMouse();
});

function cssWidth(v: any) {
  if (typeof v === "number") return `${v}px`;
  return String(v || "260px");
}
function cssSize(v: any) {
  if (typeof v === "number") return `${v}px`;
  return String(v);
}

const trackStyle = computed(() => ({
  width: cssWidth(props.width),
  height: cssSize(Math.max(Number(props.thumbSize), Number(props.height)) || 22),
}));

const railStyle = computed(() => ({
  background: props.railColor,
  height: cssSize(props.height),
  borderRadius: cssSize(props.radius),
}));

function percentFor(v: number) {
  const min = props.min;
  const max = props.max;
  const dv = Math.max(1e-9, max - min);
  return ((clamp(v) - min) / dv) * 100;
}

const startPct = computed(() => percentFor(startVal.value));
const endPct = computed(() => (props.range ? percentFor(endVal.value) : startPct.value));

const fillStyle = computed(() => {
  const left = props.range ? Math.min(startPct.value, endPct.value) : 0;
  const right = props.range ? Math.max(startPct.value, endPct.value) : startPct.value;
  return {
    left: `${left}%`,
    width: `${Math.max(0, right - left)}%`,
    background: props.fillColor,
    height: cssSize(props.height),
    borderRadius: cssSize(props.radius),
  };
});

const thumbBase = computed(() => ({
  width: cssSize(props.thumbSize),
  height: cssSize(props.thumbSize),
  background: props.thumbColor,
  border: props.thumbBorder,
  boxShadow: props.thumbShadow,
}));

const thumbStartStyle = computed(() => ({
  ...thumbBase.value,
  left: `${startPct.value}%`,
}));

const thumbEndStyle = computed(() => ({
  ...thumbBase.value,
  left: `${endPct.value}%`,
}));

const displayStart = computed(() => formatValue(startVal.value));
const displayEnd = computed(() => formatValue(endVal.value));

function formatValue(v: number) {
  if (typeof props.formatter === "function") return String(props.formatter(v));
  return String(v);
}

function measure() {
  // use selector query for better cross-platform behavior
  try {
    const q = uni.createSelectorQuery().in(getCurrentInstanceProxy());
    q.select(".zsl-track")
      .boundingClientRect((r: any) => {
        if (!r) return;
        rect.value = { left: r.left, width: r.width };
      })
      .exec();
  } catch {
    // fallback for H5
    const el = trackRef.value?.$el || trackRef.value;
    if (el && el.getBoundingClientRect) {
      const r = el.getBoundingClientRect();
      rect.value = { left: r.left, width: r.width };
    }
  }
}

function getCurrentInstanceProxy() {
  // @ts-ignore
  return (getCurrentInstance() as any)?.proxy;
}

// --- value calc

function thumbCenterX(which: "start" | "end") {
  if (!rect.value) return 0;
  const pct = which === "end" ? endPct.value : startPct.value;
  return rect.value.left + (rect.value.width * pct) / 100;
}

function beginDrag(which: "start" | "end", pointerX: number, fromThumb: boolean) {
  activeThumb.value = which;
  dragging.value = true;
  // If user grabbed the thumb edge, keep that offset so it doesn't "jump"
  dragOffsetX.value = fromThumb ? (pointerX - thumbCenterX(which)) : 0;
}

function valueFromClientX(clientX: number) {
  if (!rect.value) return startVal.value;
  const x = Math.min(rect.value.width, Math.max(0, clientX - rect.value.left));
  const ratio = rect.value.width <= 0 ? 0 : x / rect.value.width;
  const raw = props.min + ratio * (props.max - props.min);
  return snap(clamp(raw));
}

function pickThumbByValue(v: number) {
  if (!props.range) return "start" as const;
  const ds = Math.abs(v - startVal.value);
  const de = Math.abs(v - endVal.value);
  if (ds < de) return "start" as const;
  if (de < ds) return "end" as const;
  // tie -> pick the nearer side based on position
  return v >= (startVal.value + endVal.value) / 2 ? "end" : "start";
}

function emitChanging() {
  const val = props.range ? ([startVal.value, endVal.value] as [number, number]) : startVal.value;
  emit("update:modelValue", val);
  emit("changing", { value: val });
}
function emitChange() {
  const val = props.range ? ([startVal.value, endVal.value] as [number, number]) : startVal.value;
  emit("update:modelValue", val);
  emit("change", { value: val });
}

function applyValue(v: number, which: "start" | "end", final: boolean) {
  if (!props.range) {
    startVal.value = v;
  } else {
    if (which === "start") startVal.value = Math.min(v, endVal.value);
    else endVal.value = Math.max(v, startVal.value);
  }
  if (final) emitChange();
  else emitChanging();
}

// --- touch
function getPointX(e: any) {
  const t = e?.touches?.[0] || e?.changedTouches?.[0];
  if (t && typeof t.clientX === "number") return t.clientX;
  if (typeof e?.clientX === "number") return e.clientX;
  return 0;
}
function onThumbStart(e: any, which: "start" | "end") {
  if (props.disabled) return;
  if (!rect.value) measure();
  const x = getPointX(e);
  beginDrag(which, x, true);
}
function onTouchStart(e: any) {
  if (props.disabled) return;
  if (!rect.value) measure();
  const x = getPointX(e);
  const v = valueFromClientX(x);
  beginDrag(pickThumbByValue(v), x, false);
  applyValue(v, activeThumb.value!, false);
}
function onTouchMove(e: any) {
  if (props.disabled || !dragging.value) return;
  const x = getPointX(e) - (dragOffsetX.value || 0);
  const v = valueFromClientX(x);
  applyValue(v, activeThumb.value || "start", false);
}
function onTouchEnd(e: any) {
  if (props.disabled || !dragging.value) return;
  const x = getPointX(e) - (dragOffsetX.value || 0);
  const v = valueFromClientX(x);
  applyValue(v, activeThumb.value || "start", true);
  dragging.value = false;
  activeThumb.value = null;
  dragOffsetX.value = 0;
}

// --- mouse (H5 desktop)
function onThumbMouseDown(e: any, which: "start" | "end") {
  if (props.disabled) return;
  if (!rect.value) measure();
  beginDrag(which, e.clientX, true);
  bindMouse();
}
function onMouseDown(e: any) {
  if (props.disabled) return;
  if (!rect.value) measure();
  const v = valueFromClientX(e.clientX);
  beginDrag(pickThumbByValue(v), e.clientX, false);
  applyValue(v, activeThumb.value!, false);
  bindMouse();
}
function bindMouse() {
  cleanupMouse();
  const mm = (ev: MouseEvent) => {
    if (!dragging.value) return;
    const v = valueFromClientX(ev.clientX - (dragOffsetX.value || 0));
    applyValue(v, activeThumb.value || "start", false);
  };
  const mu = (ev: MouseEvent) => {
    if (!dragging.value) return;
    const v = valueFromClientX(ev.clientX - (dragOffsetX.value || 0));
    applyValue(v, activeThumb.value || "start", true);
    dragging.value = false;
    activeThumb.value = null;
    dragOffsetX.value = 0;
    cleanupMouse();
  };
  if (typeof window === "undefined") return;
  window.addEventListener("mousemove", mm);
  window.addEventListener("mouseup", mu);
  removeMouseMove = () => window.removeEventListener("mousemove", mm);
  removeMouseUp = () => window.removeEventListener("mouseup", mu);
}
function cleanupMouse() {
  removeMouseMove?.(); removeMouseMove = null;
  removeMouseUp?.(); removeMouseUp = null;
}
</script>

<style scoped>
.zsl { display:flex; flex-direction: column; gap: 10px; }
.zsl.is-disabled { opacity: .55; }
.zsl-values { display:flex; align-items:center; gap: 8px; font-size: 14px; color: #111827; }
.zsl-sep { opacity: .6; }
.zsl-track { position: relative; display:flex; align-items:center; user-select:none; }
.zsl-rail, .zsl-fill { position:absolute; left:0; top:50%; transform: translateY(-50%); width:100%; }
.zsl-fill { width:0; }
.zsl-thumb {
  position:absolute;
  top:50%;
  transform: translate(-50%, -50%);
  border-radius: 999px;
}
.zsl-thumb.is-active { transform: translate(-50%, -50%) scale(1.06); }
.zsl-mask { position: fixed; left:0; right:0; top:0; bottom:0; z-index: 9999; background: transparent; }
.zsl-marks { position: relative; height: 34px; }
.zsl-mark { position:absolute; top: 4px; transform: translateX(-50%); display:flex; flex-direction: column; align-items:center; gap: 4px; }
.zsl-dot { width:6px; height:6px; border-radius: 999px; background: rgba(17,24,39,.35); }
.zsl-label { font-size: 11px; color: rgba(17,24,39,.65); }
</style>
