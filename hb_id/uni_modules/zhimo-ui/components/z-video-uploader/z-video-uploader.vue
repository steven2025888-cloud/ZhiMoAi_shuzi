<template>
  <view class="zvu-wrap">
    <view class="zvu-grid">
      <view
        v-for="(it, idx) in items"
        :key="it.uid"
        class="zvu-card"
        :style="cardStyle"
        @tap="preview(it)"
      >
        <video
          class="zvu-video"
          :style="videoStyle"
          :src="previewSrc(it)"
          :controls="true"
          :show-center-play-btn="true"
        />

        <view v-if="!readonly" class="zvu-bar" @tap.stop>
          <view class="zvu-left" @tap.stop="handleRetry(idx)">
            <text class="zvu-state">{{ stateText(it) }}</text>
            <text v-if="it.progress > 0 && it.progress < 100" class="zvu-state">{{ it.progress }}%</text>
          </view>

          <view class="zvu-right">
            <view class="zvu-btn" @tap.stop="removeAt(idx)">
              <text class="zvu-btn-txt">×</text>
            </view>
          </view>

          <progress
            v-if="it.progress > 0 && it.progress < 100"
            class="zvu-progress"
            :percent="it.progress"
            :stroke-width="3"
            border-radius="6"
            backgroundColor="rgba(0,0,0,.10)"
            :activeColor="progressColorResolved"
          />
        </view>
      </view>

      <view
        v-if="showAdd"
        class="zvu-card zvu-add"
        :style="[cardStyle, addStyle]"
        @tap.stop="pickVideo"
      >
        <slot name="add">
          <view class="zvu-plus" :style="{ color: addIconColor, fontSize: addIconSize + 'rpx' }">＋</view>
          <text class="zvu-tip">{{ addText }}</text>
        </slot>
      </view>
    </view>

    <view v-if="!readonly && showFooter" class="zvu-footer">
      <view class="zvu-actions">
        <view class="zvu-action" @tap="pickVideo">
          <text class="zvu-action-txt">选择视频</text>
        </view>
        <view class="zvu-action zvu-primary" :class="{ 'zvu-disabled': !canStart }" @tap="start">
          <text class="zvu-action-txt">开始上传</text>
        </view>
      </view>

      <view class="zvu-hint" v-if="hint">
        <text class="zvu-hint-txt">{{ hint }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, reactive, toRaw, watch } from "vue";

defineOptions({ name: "z-video-uploader" });

/**
 * z-video-uploader (Vue3 / uni-app)
 * - 多选（优先 chooseMedia，自动回退 chooseVideo）
 * - 自动/手动上传
 * - 上传进度 / 失败重试 / 删除（上传中可 abort）
 * - 两种上传方式：
 *   1) action + uni.uploadFile
 *   2) uploadRequest 自定义 Promise<string>
 *
 * v-model 仅返回「已上传成功」的 url 列表（string[]）
 */

type UploadStatus = "ready" | "uploading" | "done" | "fail";

export type UploadItem = {
  uid: string;
  localPath: string; // temp path
  remoteUrl: string; // url after uploaded
  status: UploadStatus;
  progress: number; // 0-100
  size?: number;
  duration?: number;
};

type UploadCtx = {
  index: number;
  uid: string;
  item: UploadItem;
  /** 给自定义上传用：更新进度（0-100） */
  setProgress: (p: number) => void;
};

const props = withDefaults(
  defineProps<{
    /** 已上传成功的 url 列表（用于初始化/外部控制） */
    modelValue?: string[];

    /** 上传接口地址（不传则必须传 uploadRequest） */
    action?: string;
    /** 表单字段名 */
    name?: string;
    /** 请求头 */
    headers?: Record<string, any>;
    /** 额外表单字段 */
    data?: Record<string, any>;

    /** 最大数量 */
    maxCount?: number;
    /** 选完是否立刻上传 */
    autoUpload?: boolean;
    /** 只读浏览模式：不显示添加/删除/上传 */
    readonly?: boolean;

    /** 单卡片宽高（rpx） */
    width?: number;
    height?: number;
    radius?: number;

    /** add 卡片 */
    addText?: string;
    addIconColor?: string;
    addIconSize?: number;

    /** 卡片背景/边框 */
    background?: string;
    border?: boolean;
    borderColor?: string;
    borderStyle?: "solid" | "dashed" | "dotted";

    /** 进度条颜色 */
    progressColor?: string;

    /** 选择视频参数 */
    sourceType?: ("album" | "camera")[];
    compressed?: boolean;
    maxDuration?: number;
    camera?: "front" | "back";

    /** 校验 */
    maxSizeMB?: number;
    /** 允许的扩展名（不带点：mp4/mov/...）。注意：某些平台 tempFilePath 可能没有扩展名，此时不会拦截。 */
    extensions?: string[];

    /** 删除确认 */
    confirmRemove?: boolean;

    /** 自定义上传（返回 Promise<string>，string 为最终 url） */
    uploadRequest?: (filePath: string, ctx: UploadCtx) => Promise<string>;

    /** 从 uni.uploadFile 响应中提取 url */
    parseResponse?: (resp: UniApp.UploadFileSuccessCallbackResult) => string;

    /** 是否显示底部按钮条（手动上传更方便） */
    showFooter?: boolean;
  }>(),
  {
    modelValue: () => [],
    action: "",
    name: "file",
    headers: () => ({}),
    data: () => ({}),
    maxCount: 1,
    autoUpload: false,
    readonly: false,

    width: 640,
    height: 320,
    radius: 16,

    addText: "添加视频",
    addIconColor: "#555",
    addIconSize: 84,

    background: "#f4f4f5",
    border: true,
    borderColor: "#d0d0d0",
    borderStyle: "dashed",

    progressColor: "",
    sourceType: () => ["album", "camera"],
    compressed: true,
    maxDuration: 60,
    camera: "back",

    maxSizeMB: 20,
    extensions: () => [],

    confirmRemove: false,

    uploadRequest: undefined,
    parseResponse: undefined,

    showFooter: true,
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", v: string[]): void;
  (e: "change", items: UploadItem[]): void;
  (e: "success", payload: { index: number; url: string; raw?: any }): void;
  (e: "error", payload: { index: number; error: any }): void;
  (e: "progress", payload: { index: number; progress: number }): void;
  (e: "complete", payload: { status: "ready" | "uploading" | "done" | "fail"; urls: string[]; action: string }): void;
  (e: "remove", payload: { index: number }): void;
  (e: "retry", payload: { index: number }): void;
}>();

function uid() {
  return `${Date.now().toString(36)}_${Math.random().toString(16).slice(2)}`;
}

const state = reactive({
  items: [] as UploadItem[],
});

const items = computed(() => state.items);

const taskByUid = new Map<string, any>(); // UniApp.UploadTask

// ---- 外部 v-model 同步（修复：不要把本地待上传项清空）----
let inited = false;
let innerEmitting = false;

function buildDoneItems(urls: string[]) {
  const list = (urls || []).filter(Boolean);
  return list.map((u) => ({
    uid: uid(),
    localPath: "",
    remoteUrl: u,
    status: "done" as const,
    progress: 100,
  }));
}

watch(
  () => props.modelValue,
  (vals) => {
    const nextUrls = (vals || []).filter(Boolean);

    if (!inited) {
      state.items = buildDoneItems(nextUrls);
      inited = true;
      return;
    }

    if (innerEmitting) return;

    // 外部更新：替换已完成部分，保留本地未完成（尽量不破坏用户刚选的视频）
    const pending = state.items.filter((it) => it.status !== "done");
    const done = buildDoneItems(nextUrls);

    const merged = [...done, ...pending].slice(0, Number(props.maxCount));
    state.items = merged;
  },
  { immediate: true }
);

// ---- UI computed ----
const showAdd = computed(() => !props.readonly && state.items.length < Number(props.maxCount));
const canStart = computed(() => !props.readonly && getOverallStatus() !== "uploading" && hasPending());

const hint = computed(() => {
  if (props.readonly) return "";
  const total = Number(props.maxCount);
  const left = Math.max(0, total - state.items.length);
  const ext = props.extensions.length ? `支持：${props.extensions.join(", ")}` : "格式不限";
  return `最多 ${total} 个，剩余 ${left} 个可添加，${ext}`;
});

const cardStyle = computed(() => ({
  width: `${Number(props.width)}rpx`,
  height: `${Number(props.height)}rpx`,
  borderRadius: `${Number(props.radius)}rpx`,
  background: props.background,
}));

const addStyle = computed(() => ({
  borderWidth: props.border ? "1px" : "0",
  borderStyle: props.borderStyle,
  borderColor: props.borderColor,
}));

const videoStyle = computed(() => ({
  width: `${Number(props.width)}rpx`,
  height: `${Number(props.height) - (props.readonly ? 0 : 52)}rpx`,
  borderRadius: `${Number(props.radius)}rpx`,
}));

const progressColorResolved = computed(() => props.progressColor || "#3b82f6");

// ---- helpers ----
function previewSrc(it: UploadItem) {
  return it.remoteUrl || it.localPath || "";
}

function stateText(it: UploadItem) {
  if (it.status === "done") return "已完成";
  if (it.status === "fail") return "失败，点此重试";
  if (it.status === "uploading") return "上传中";
  return "等待上传";
}

function getOverallStatus(): "ready" | "uploading" | "done" | "fail" {
  if (state.items.length === 0) return "ready";
  const s = state.items.map((x) => x.status);
  if (s.includes("uploading")) return "uploading";
  if (s.includes("fail")) return "fail";
  if (s.every((x) => x === "done")) return "done";
  return "ready";
}

function hasPending() {
  return state.items.some((it) => it.status === "ready" || it.status === "fail");
}

function syncVModel() {
  // 只向外输出已上传成功的 remoteUrl
  const urls = state.items
    .filter((it) => it.status === "done" && !!it.remoteUrl)
    .map((it) => it.remoteUrl);

  innerEmitting = true;
  emit("update:modelValue", urls);
  emit("change", toRaw(state.items));
  emit("complete", { status: getOverallStatus(), urls, action: props.action || "" });

  // 下一轮再允许外部 watch 生效
  nextTick(() => {
    innerEmitting = false;
  });
}

function toast(msg: string) {
  msg && uni.showToast({ title: msg, icon: "none" });
}

function getExtFromPath(filePath: string) {
  // 只从文件名部分取扩展名，且允许带 ?/# 的路径
  const base = (filePath || "").split(/[\\/]/).pop() || "";
  const m = base.match(/\.([a-z0-9]+)(?:\?|#|$)/i);
  return (m?.[1] || "").toLowerCase();
}

function validateFile(filePath: string, size?: number) {
  // 扩展名校验：注意有的平台 tempFilePath 可能没有扩展名，此时不拦截
  if (props.extensions.length) {
    const ext = getExtFromPath(filePath);
    if (ext) {
      const allowed = props.extensions.map((x) => String(x).toLowerCase().replace(/^\./, ""));
      if (!allowed.includes(ext)) {
        toast(`仅支持：${props.extensions.join(", ")}`);
        return false;
      }
    }
  }

  // 大小校验（部分平台可能没有 size）
  if (typeof size === "number") {
    const maxBytes = Number(props.maxSizeMB) * 1024 * 1024;
    if (maxBytes > 0 && size > maxBytes) {
      toast(`单个视频不能超过 ${props.maxSizeMB}MB`);
      return false;
    }
  }
  return true;
}

function appendPicked(filePath: string, size?: number, duration?: number) {
  if (!filePath) return;
  if (!validateFile(filePath, size)) return;

  const item: UploadItem = {
    uid: uid(),
    localPath: filePath,
    remoteUrl: "",
    status: props.autoUpload ? "uploading" : "ready",
    progress: props.autoUpload ? 0 : 0,
    size,
    duration,
  };

  state.items.push(item);
  // 限制最大数量（防止 chooseMedia 一次选多了）
  state.items = state.items.slice(0, Number(props.maxCount));
  syncVModel();

  if (props.autoUpload) {
    const idx = state.items.findIndex((x) => x.uid === item.uid);
    if (idx >= 0) uploadOne(idx).catch(() => {});
  }
}

// ---- pick video (multi) ----
function pickVideo() {
  if (props.readonly) return;

  const left = Number(props.maxCount) - state.items.length;
  if (left <= 0) {
    toast("已达到最大数量");
    return;
  }

  // 优先 chooseMedia（支持 count）
  const anyUni: any = uni as any;
  if (typeof anyUni.chooseMedia === "function") {
    anyUni.chooseMedia({
      count: left,
      mediaType: ["video"],
      sourceType: props.sourceType,
      maxDuration: props.maxDuration,
      camera: props.camera,
      success: (res: any) => {
        const files: any[] = res?.tempFiles || [];
        files.forEach((f) => {
          const path = f?.tempFilePath || f?.path || "";
          appendPicked(path, f?.size, f?.duration);
        });
      },
      fail: () => {},
    });
    return;
  }

  // 回退 chooseVideo（一次一个）
  uni.chooseVideo({
    sourceType: props.sourceType as any,
    compressed: props.compressed,
    maxDuration: props.maxDuration,
    camera: props.camera,
    success: (e) => {
      appendPicked((e as any).tempFilePath, (e as any).size, (e as any).duration);
    },
  });
}

function handleRetry(index: number) {
  const it = state.items[index];
  if (!it || props.readonly) return;
  if (it.status !== "fail") return;
  emit("retry", { index });
  uploadOne(index).catch(() => {});
}

async function start() {
  if (props.readonly) return;
  if (!canStart.value) return;

  const missing = !props.uploadRequest && !props.action;
  if (missing) {
    toast("请传入 action 或 uploadRequest");
    return;
  }

  for (let i = 0; i < state.items.length; i++) {
    const it = state.items[i];
    if (it.status === "done") continue;
    await uploadOne(i).catch(() => {});
  }
}

function setProgress(p: number, index: number) {
  const it = state.items[index];
  if (!it) return;
  const prog = Math.max(0, Math.min(100, Math.round(p)));
  it.progress = prog;
  emit("progress", { index, progress: prog });
}

function setResult(url: string, index: number) {
  const it = state.items[index];
  if (!it || !url) return;
  it.remoteUrl = url;
  it.status = "done";
  it.progress = 100;
  emit("success", { index, url });
  syncVModel();
}

async function uploadOne(index: number) {
  const it = state.items[index];
  if (!it) return;

  if (it.status === "uploading") return;
  if (!it.localPath && it.remoteUrl) return;

  it.status = "uploading";
  it.progress = 0;
  syncVModel();

  try {
    let url = "";

    if (props.uploadRequest) {
      url = await props.uploadRequest(it.localPath, {
        index,
        uid: it.uid,
        item: it,
        setProgress: (p) => setProgress(p, index),
      });
    } else {
      url = await uploadViaUni(it, index, it.localPath);
    }

    if (!url) throw new Error("上传成功但未返回 url");

    setResult(url, index);
  } catch (err) {
    it.status = "fail";
    it.progress = 0;
    emit("error", { index, error: err });
    syncVModel();
  }
}

function uploadViaUni(it: UploadItem, index: number, filePath: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const task = uni.uploadFile({
      url: props.action,
      name: props.name,
      header: props.headers,
      formData: props.data,
      filePath,
      success: (resp) => {
        taskByUid.delete(it.uid);

        try {
          const parser =
            props.parseResponse ||
            ((r: UniApp.UploadFileSuccessCallbackResult) => {
              const raw = (r.data || "") as any;
              const obj = typeof raw === "string" ? JSON.parse(String(raw).replace(/\ufeff/g, "")) : raw;
              return obj?.url || obj?.data?.url || obj?.result?.url || "";
            });

          if (resp.statusCode >= 200 && resp.statusCode < 300) {
            resolve(parser(resp));
          } else {
            reject(resp);
          }
        } catch (e) {
          reject(e);
        }
      },
      fail: (e) => {
        taskByUid.delete(it.uid);
        reject(e);
      },
    });

    taskByUid.set(it.uid, task);

    task.onProgressUpdate((p) => {
      const prog = Math.max(0, Math.min(100, p.progress || 0));
      const cur = state.items[index];
      if (cur && cur.uid === it.uid && cur.status === "uploading") {
        cur.progress = prog;
        emit("progress", { index, progress: prog });
      }
    });
  });
}

function abort(index: number) {
  const it = state.items[index];
  if (!it) return;
  const task = taskByUid.get(it.uid);
  if (task && typeof task.abort === "function") task.abort();
  taskByUid.delete(it.uid);
  if (it.status === "uploading") {
    it.status = "fail";
    it.progress = 0;
    syncVModel();
  }
}

function removeAt(index: number) {
  if (props.readonly) return;

  const it = state.items[index];
  if (!it) return;

  const doRemove = () => {
    // 如果上传中，先中断
    abort(index);
    state.items.splice(index, 1);
    emit("remove", { index });
    syncVModel();
  };

  if (props.confirmRemove) {
    uni.showModal({
      title: "提示",
      content: "确定移除这个视频吗？",
      showCancel: true,
      success: (r) => {
        if (r.confirm) doRemove();
      },
    });
  } else {
    doRemove();
  }
}

function preview(it: UploadItem) {
  const src = previewSrc(it);
  if (!src) return;
  const anyUni: any = uni as any;
  if (typeof anyUni.previewMedia === "function") {
    anyUni.previewMedia({
      sources: [{ url: src, type: "video" }],
      current: 0,
    });
  }
}

// expose
defineExpose({
  start,
  uploadOne,
  pickVideo,
  removeAt,
  abort,
  setProgress,
  setResult,
  getItems: () => toRaw(state.items),
});
</script>

<style scoped>
.zvu-wrap {
  width: 100%;
}

.zvu-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.zvu-card {
  position: relative;
  overflow: hidden;
}

.zvu-video {
  background: rgba(0, 0, 0, 0.08);
}

.zvu-add {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.zvu-plus {
  font-weight: 800;
  line-height: 1;
}

.zvu-tip {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: rgba(0, 0, 0, 0.55);
}

.zvu-bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 52rpx;
  padding: 0 10rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.35);
}

.zvu-left {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.zvu-state {
  font-size: 22rpx;
  color: rgba(255, 255, 255, 0.92);
}

.zvu-right {
  display: flex;
  align-items: center;
}

.zvu-btn {
  width: 44rpx;
  height: 44rpx;
  border-radius: 999rpx;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}

.zvu-btn-txt {
  font-size: 34rpx;
  color: rgba(255, 255, 255, 0.92);
  line-height: 34rpx;
}

.zvu-progress {
  position: absolute;
  left: 10rpx;
  right: 10rpx;
  bottom: 6rpx;
}

.zvu-footer {
  margin-top: 16rpx;
}

.zvu-actions {
  display: flex;
  gap: 14rpx;
}

.zvu-action {
  flex: 1;
  height: 76rpx;
  border-radius: 18rpx;
  background: rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
}

.zvu-primary {
  background: rgba(59, 130, 246, 0.18);
}

.zvu-disabled {
  opacity: 0.45;
}

.zvu-action-txt {
  font-size: 28rpx;
  color: rgba(0, 0, 0, 0.82);
}

.zvu-hint {
  margin-top: 10rpx;
  padding: 0 6rpx;
}

.zvu-hint-txt {
  font-size: 22rpx;
  color: rgba(0, 0, 0, 0.55);
}
</style>
