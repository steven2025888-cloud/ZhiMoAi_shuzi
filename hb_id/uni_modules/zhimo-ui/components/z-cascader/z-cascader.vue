<template>
  <view class="z-cascader">
    <!-- Breadcrumb / Tabs -->
    <scroll-view
      scroll-x
      class="z-cascader__crumbs"
      :show-scrollbar="false"
      scroll-with-animation
      :scroll-into-view="scrollIntoId"
    >
      <view class="z-cascader__crumbs-inner">
        <view
          v-for="(c, i) in crumbs"
          :key="i"
          class="z-cascader__crumb"
          :id="`zcc_${i}`"
          @tap.stop="setActive(i)"
        >
          <text
            class="z-cascader__crumb-text"
            :class="{ 'is-active': i === activeLevel }"
          >
            {{ c }}
          </text>
          <text v-if="i !== crumbs.length - 1" class="z-cascader__sep">›</text>
        </view>
      </view>
    </scroll-view>

    <view v-if="showDivider" class="z-cascader__divider" />

    <!-- Options list -->
    <view class="z-cascader__panel">
      <view v-if="loading" class="z-cascader__loading">
        <view class="z-cascader__spinner" />
        <text class="z-cascader__loading-text">{{ loadingText }}</text>
      </view>

      <scroll-view v-else scroll-y class="z-cascader__list" :show-scrollbar="false">
        <view
          v-for="(item, idx) in currentOptions"
          :key="getValue(item) ?? idx"
          class="z-cascader__item"
          :class="{ 'is-selected': isSelected(item) }"
          @tap.stop="pick(item)"
        >
          <text class="z-cascader__item-text">{{ getLabel(item) }}</text>

          <view class="z-cascader__right">
            <text v-if="isSelected(item)" class="z-cascader__check">✓</text>
            <text v-else-if="hasNext(item)" class="z-cascader__arrow">›</text>
          </view>
        </view>

        <view v-if="!currentOptions.length" class="z-cascader__empty">
          <text class="z-cascader__empty-text">{{ emptyText }}</text>
        </view>
      </scroll-view>
    </view>

    <view v-if="showFooter" class="z-cascader__footer">
      <button class="z-cascader__btn" @tap="reset">{{ resetText }}</button>
      <button class="z-cascader__btn is-primary" @tap="emitComplete" :disabled="!canComplete">
        {{ confirmText }}
      </button>
    </view>
  </view>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";

/**
 * z-cascader (Vue3 / uni-app)
 * - 支持嵌套 options
 * - 支持 lazy 分级加载 (load)
 * - 支持 v-model (modelValue: string[] | number[])
 */
const props = defineProps({
  modelValue: { type: Array, default: () => [] },

  // nested options for level 0
  options: { type: Array, default: () => [] },

  // key mapping
  labelKey: { type: String, default: "label" },
  valueKey: { type: String, default: "value" },
  childrenKey: { type: String, default: "children" },

  // behaviour
  maxDepth: { type: Number, default: 3 }, // 期望层级深度（不限制也可以，但能让 UI/complete 行为更明确）
  lazy: { type: Boolean, default: false }, // 是否逐级加载
  load: { type: Function, default: null }, // (node, level) => Promise<option[]>

  // text
  placeholder: { type: String, default: "请选择" },
  loadingText: { type: String, default: "加载中…" },
  emptyText: { type: String, default: "暂无数据" },
  resetText: { type: String, default: "重置" },
  confirmText: { type: String, default: "确定" },

  // UI
  showDivider: { type: Boolean, default: true },
  showFooter: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "complete"]);

const activeLevel = ref(0);
const levelsOptions = ref([]); // option[][]
const selectedNodes = ref([]); // any[]
const loading = ref(false);
const scrollIntoId = ref("zcc_0");

const getLabel = (node) => (node && node[props.labelKey]) ?? "";
const getValue = (node) => (node && node[props.valueKey]) ?? null;
const getChildren = (node) => (node && node[props.childrenKey]) ?? null;

const currentOptions = computed(() => levelsOptions.value[activeLevel.value] ?? []);

const values = computed(() => selectedNodes.value.map(getValue).filter((v) => v != null));
const labels = computed(() => selectedNodes.value.map(getLabel).filter((v) => v));

const crumbs = computed(() => {
  // 规则：已选用 label，否则用 placeholder；再额外补一个 placeholder（代表下一层）直到 maxDepth 或 无限制
  const base = [];
  const selected = selectedNodes.value;

  for (let i = 0; i < Math.max(selected.length, 1); i++) {
    const node = selected[i];
    base.push(node ? getLabel(node) : props.placeholder);
  }

  // 如果当前层已选，并且还没到 maxDepth，并且有下一层可选，补一个“请选择”
  const at = activeLevel.value;
  const curSel = selected[at];
  const canGoNext = curSel && hasNext(curSel);
  const needNextCrumb =
    canGoNext && (props.maxDepth <= 0 || base.length < props.maxDepth);

  if (needNextCrumb) base.push(props.placeholder);

  // 如果没有任何选择，至少显示一个 placeholder
  if (!base.length) base.push(props.placeholder);

  return base;
});

const canComplete = computed(() => values.value.length > 0);

function hasNext(node) {
  // 如果嵌套 children 存在，认为可进入下一层
  const children = getChildren(node);
  if (Array.isArray(children) && children.length) return true;

  // lazy 模式：允许点击后触发 load
  if (props.lazy && typeof props.load === "function") return true;

  return false;
}

function isSelected(node) {
  const sel = selectedNodes.value[activeLevel.value];
  return sel && getValue(sel) === getValue(node);
}

function setActive(level) {
  activeLevel.value = Math.max(0, Math.min(level, levelsOptions.value.length - 1));
  nextTick(() => (scrollIntoId.value = `zcc_${activeLevel.value}`));
}

function reset() {
  activeLevel.value = 0;
  selectedNodes.value = [];
  levelsOptions.value = [props.options || []];
  emit("update:modelValue", []);
  emit("change", { values: [], labels: [], nodes: [], level: 0 });
  nextTick(() => (scrollIntoId.value = "zcc_0"));
}

async function ensureLevelOptions(parentNode, level) {
  // 1) nested children
  const children = getChildren(parentNode);
  if (Array.isArray(children)) return children;

  // 2) lazy load
  if (props.lazy && typeof props.load === "function") {
    loading.value = true;
    try {
      const res = await props.load(parentNode, level);
      // 写回 children，避免重复请求
      if (parentNode && typeof parentNode === "object") {
        parentNode[props.childrenKey] = Array.isArray(res) ? res : [];
      }
      return Array.isArray(res) ? res : [];
    } finally {
      loading.value = false;
    }
  }

  return [];
}

async function pick(node) {
  const level = activeLevel.value;

  // 选中当前层
  selectedNodes.value = selectedNodes.value.slice(0, level);
  selectedNodes.value[level] = node;

  // 更新 v-model
  emit("update:modelValue", values.value);

  // 通知 change
  emit("change", {
    values: values.value,
    labels: labels.value,
    nodes: selectedNodes.value.slice(),
    level,
  });

  // 尝试进入下一层
  const nextLevel = level + 1;
  const reachedMax = props.maxDepth > 0 && nextLevel >= props.maxDepth;

  if (!reachedMax && hasNext(node)) {
    const nextOptions = await ensureLevelOptions(node, nextLevel);
    levelsOptions.value = levelsOptions.value.slice(0, nextLevel);
    levelsOptions.value[nextLevel] = nextOptions || [];

    activeLevel.value = nextLevel;

    await nextTick();
    scrollIntoId.value = `zcc_${activeLevel.value}`;

    // 如果下一层为空（lazy 返回空 / children 为空），也算完成
    if (!levelsOptions.value[nextLevel]?.length) emitComplete();
    return;
  }

  // 没有下一层：完成
  emitComplete();
}

function emitComplete() {
  if (!values.value.length) return;
  emit("complete", {
    values: values.value,
    labels: labels.value,
    nodes: selectedNodes.value.slice(),
  });
}

async function applyModelValue(newVal) {
  // 根据 v-model 反推选中路径
  if (!Array.isArray(newVal) || newVal.length === 0) {
    reset();
    return;
  }

  // 初始化第一层
  const lv0 = props.options || [];
  levelsOptions.value = [lv0];
  selectedNodes.value = [];
  activeLevel.value = 0;

  let curOptions = lv0;
  for (let level = 0; level < newVal.length; level++) {
    const val = newVal[level];
    const found = (curOptions || []).find((o) => getValue(o) === val);
    if (!found) break;

    selectedNodes.value[level] = found;

    // 下一层
    const nextLevel = level + 1;
    if (props.maxDepth > 0 && nextLevel >= props.maxDepth) break;

    if (hasNext(found)) {
      const nextOptions = await ensureLevelOptions(found, nextLevel);
      levelsOptions.value[nextLevel] = nextOptions || [];
      curOptions = nextOptions || [];
    } else {
      break;
    }
  }

  // active 指向最后一层可选项
  activeLevel.value = Math.min(newVal.length - 1, levelsOptions.value.length - 1);
  await nextTick();
  scrollIntoId.value = `zcc_${activeLevel.value}`;
}

watch(
  () => props.options,
  () => {
    // options 变化：尽量复用 modelValue 重建
    applyModelValue(props.modelValue);
  },
  { deep: true }
);

watch(
  () => props.modelValue,
  (v) => {
    applyModelValue(v);
  },
  { deep: true }
);

onMounted(() => {
  applyModelValue(props.modelValue);
});

defineExpose({
  reset,
  getValues: () => values.value,
  getLabels: () => labels.value,
});
</script>

<style scoped>
.z-cascader {
  border-radius: 16rpx;
  overflow: hidden;
  background: #ffffff;
  border: 1rpx solid rgba(0, 0, 0, 0.06);
}

.z-cascader__crumbs {
  white-space: nowrap;
  padding: 20rpx 20rpx 10rpx;
}

.z-cascader__crumbs-inner {
  display: inline-flex;
  align-items: center;
}

.z-cascader__crumb {
  display: inline-flex;
  align-items: center;
  padding: 8rpx 10rpx;
  border-radius: 12rpx;
}

.z-cascader__crumb-text {
  font-size: 28rpx;
  color: rgba(0, 0, 0, 0.72);
}

.z-cascader__crumb-text.is-active {
  color: rgba(0, 0, 0, 0.92);
  font-weight: 700;
}

.z-cascader__sep {
  margin: 0 8rpx;
  font-size: 26rpx;
  color: rgba(0, 0, 0, 0.35);
}

.z-cascader__divider {
  height: 1rpx;
  background: rgba(0, 0, 0, 0.06);
}

.z-cascader__panel {
  height: 560rpx;
}

.z-cascader__list {
  height: 560rpx;
}

.z-cascader__item {
  padding: 26rpx 22rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.z-cascader__item + .z-cascader__item {
  border-top: 1rpx solid rgba(0, 0, 0, 0.04);
}

.z-cascader__item-text {
  font-size: 28rpx;
  color: rgba(0, 0, 0, 0.86);
}

.z-cascader__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 60rpx;
}

.z-cascader__check {
  font-size: 30rpx;
  color: #2b7cff;
  font-weight: 700;
}

.z-cascader__arrow {
  font-size: 30rpx;
  color: rgba(0, 0, 0, 0.28);
}

.z-cascader__item.is-selected .z-cascader__item-text {
  color: #2b7cff;
  font-weight: 600;
}

.z-cascader__empty {
  padding: 40rpx 24rpx;
}

.z-cascader__empty-text {
  font-size: 26rpx;
  color: rgba(0, 0, 0, 0.45);
}

.z-cascader__loading {
  height: 560rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: row;
  gap: 14rpx;
}

.z-cascader__loading-text {
  font-size: 26rpx;
  color: rgba(0, 0, 0, 0.55);
}

.z-cascader__spinner {
  width: 28rpx;
  height: 28rpx;
  border-radius: 999rpx;
  border: 4rpx solid rgba(0, 0, 0, 0.12);
  border-top-color: rgba(0, 0, 0, 0.42);
  animation: zspin 0.9s linear infinite;
}

@keyframes zspin {
  to {
    transform: rotate(360deg);
  }
}

.z-cascader__footer {
  display: flex;
  gap: 18rpx;
  padding: 18rpx 20rpx 22rpx;
  border-top: 1rpx solid rgba(0, 0, 0, 0.06);
  background: #fff;
}

.z-cascader__btn {
  flex: 1;
  font-size: 28rpx;
  padding: 18rpx 0;
  border-radius: 14rpx;
  border: 1rpx solid rgba(0, 0, 0, 0.10);
  background: #fff;
  color: rgba(0, 0, 0, 0.78);
}

.z-cascader__btn.is-primary[disabled] {
  opacity: 0.5;
}

.z-cascader__btn.is-primary {
  background: #2b7cff;
  border-color: #2b7cff;
  color: #fff;
}
</style>