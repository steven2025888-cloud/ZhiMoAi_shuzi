<template>
  <view class="zpi">
    <!-- 输入框显示区域 -->
    <view class="zpi-box" :class="`theme-${theme}`" @tap="onTapBox">
      <view class="zpi-box__hd" v-if="title || $slots.title || $slots.right">
        <view class="zpi-box__title">
          <slot name="title">
            <text class="zpi-title">{{ title }}</text>
          </slot>
          <text v-if="sub" class="zpi-sub">{{ sub }}</text>
        </view>
        <view class="zpi-box__right">
          <slot name="right"></slot>
        </view>
      </view>

      <view class="zpi-cells" :style="{ gap: cellsGap + 'rpx' }">
        <view
          v-for="i in length"
          :key="i"
          class="zpi-cell"
          :class="[
            i - 1 === activeIndex && show ? 'is-active' : '',
            valueArr[i - 1] ? 'is-filled' : ''
          ]"
          @tap="setActive(i - 1)"
        >
          <text class="zpi-cell__txt">{{ valueArr[i - 1] || placeholderChar }}</text>
        </view>
      </view>

      <view class="zpi-hint" v-if="hint">
        <text class="zpi-hint__txt">{{ hint }}</text>
      </view>
    </view>

    <!-- 遮罩层 -->
    <view v-show="mask && kbVisible" class="zpi-mask" :class="{ 'zpi-mask--show': show }" @tap="close" catchtouchmove @touchmove.stop.prevent="noop"></view>

    <!-- 键盘 -->
    <view v-show="kbVisible" class="zpi-keyboard" :class="[`theme-${theme}`, { 'zpi-keyboard--show': show }]" catchtouchmove @touchmove.stop.prevent="noop">
      <!-- 工具栏 -->
      <view v-if="toolbar" class="zpi-toolbar">
        <text class="zpi-toolbar__tip">{{ toolbarTip }}</text>
        <text class="zpi-toolbar__btn" @tap="onConfirm">{{ confirmText }}</text>
      </view>

      <!-- 按键区域 -->
      <view class="zpi-keys">
        <view v-for="row in currentRows" :key="row.id" class="zpi-keys__row">
          <view
            v-for="(k, idx) in row.keys"
            :key="idx"
            class="zpi-key"
            :class="getKeyClass(k, row, idx)"
            @tap.stop="onKeyTap(k)"
          >
            <text class="zpi-key__text">{{ getKeyLabel(k) }}</text>
          </view>

          <!-- 删除键 -->
          <view v-if="row.isLast" class="zpi-key zpi-key--del" @tap.stop="onDelete">
            <text class="zpi-key__text">删除</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

// 省份键盘
const KB_PROVINCE = [
  {
    id: 'p1',
    keys: [
      { cn: '京' }, { cn: '津' }, { cn: '沪' }, { cn: '渝' },
      { cn: '冀' }, { cn: '豫' }, { cn: '云' }, { cn: '辽' },
      { cn: '黑' }, { cn: '湘' }
    ]
  },
  {
    id: 'p2',
    keys: [
      { cn: '皖' }, { cn: '鲁' }, { cn: '新' }, { cn: '苏' }, { cn: '浙' },
      { cn: '赣' }, { cn: '鄂' }, { cn: '桂' }, { cn: '甘' }, { cn: '晋' }
    ]
  },
  {
    id: 'p3',
    keys: [
      { cn: '蒙' }, { cn: '陕' }, { cn: '吉' }, { cn: '闽' }, { cn: '贵' },
      { cn: '粤' }, { cn: '青' }, { cn: '藏' }, { cn: '川' }, { cn: '宁' }
    ]
  },
  {
    id: 'p4',
    isLast: true,
    keys: [
      { cn: '琼' }, { cn: '使' }, { cn: '领' }, { cn: '学' },
      { cn: '警' }, { cn: '港' }, { cn: '澳' }, { cn: '挂' }
    ]
  }
]

// 字母键盘（第二位，不含I/O）
const KB_LETTER = [
  {
    id: 'l1',
    keys: [
      { en: 'A' }, { en: 'B' }, { en: 'C' }, { en: 'D' }, { en: 'E' },
      { en: 'F' }, { en: 'G' }, { en: 'H' }, { en: 'J' }, { en: 'K' }
    ]
  },
  {
    id: 'l2',
    keys: [
      { en: 'L' }, { en: 'M' }, { en: 'N' }, { en: 'P' }, { en: 'Q' },
      { en: 'R' }, { en: 'S' }, { en: 'T' }, { en: 'U' }, { en: 'V' }
    ]
  },
  {
    id: 'l3',
    isLast: true,
    keys: [
      { en: 'W' }, { en: 'X' }, { en: 'Y' }, { en: 'Z' }
    ]
  }
]

// 字母数字键盘（第三位及以后）
const KB_ALPHANUM = [
  {
    id: 'n1',
    keys: [
      { en: '1' }, { en: '2' }, { en: '3' }, { en: '4' }, { en: '5' },
      { en: '6' }, { en: '7' }, { en: '8' }, { en: '9' }, { en: '0' }
    ]
  },
  {
    id: 'n2',
    keys: [
      { en: 'Q' }, { en: 'W' }, { en: 'E' }, { en: 'R' }, { en: 'T' },
      { en: 'Y' }, { en: 'U' }, { en: 'P' }
    ]
  },
  {
    id: 'n3',
    keys: [
      { en: 'A' }, { en: 'S' }, { en: 'D' }, { en: 'F' }, { en: 'G' },
      { en: 'H' }, { en: 'J' }, { en: 'K' }, { en: 'L' }
    ]
  },
  {
    id: 'n4',
    isLast: true,
    keys: [
      { en: 'Z' }, { en: 'X' }, { en: 'C' }, { en: 'V' },
      { en: 'B' }, { en: 'N' }, { en: 'M' }
    ]
  }
]

const props = defineProps({
  modelValue: { type: String, default: '' },
  length: { type: Number, default: 7 },
  show: { type: Boolean, default: false },
  title: { type: String, default: '' },
  sub: { type: String, default: '' },
  hint: { type: String, default: '' },
  placeholderChar: { type: String, default: ' ' },
  disabled: { type: Boolean, default: false },
  theme: { type: String, default: 'light' },
  toolbar: { type: Boolean, default: true },
  toolbarTip: { type: String, default: '车牌键盘' },
  confirmText: { type: String, default: '完成' },
  mask: { type: Boolean, default: false },
  cellsGap: { type: Number, default: 12 },
  autoClose: { type: Boolean, default: true }
})

const emit = defineEmits([
  'update:modelValue',
  'update:show',
  'change',
  'confirm'
])

const activeIndex = ref(0)



// keyboard transition
const kbVisible = ref(false)
const ANIM_MS = 220
function noop() {}
const valueArr = computed(() => {
  const v = (props.modelValue || '').toString()
  return v.split('').slice(0, props.length)
})

const currentRows = computed(() => {
  if (activeIndex.value === 0) {
    return KB_PROVINCE
  } else if (activeIndex.value === 1) {
    return KB_LETTER
  } else {
    return KB_ALPHANUM
  }
})

function onTapBox() {
  if (props.disabled) return
  emit('update:show', true)
}

function close() {
  emit('update:show', false)
}

function setActive(i) {
  if (props.disabled) return
  activeIndex.value = Math.max(0, Math.min(i, props.length - 1))
  if (!props.show) {
    emit('update:show', true)
  }
}

function getKeyLabel(k) {
  return k.cn || k.en || ''
}

function getKeyClass(k, row, idx) {
  const label = getKeyLabel(k)
  return {
    'zpi-key--empty': !label
  }
}

function onKeyTap(k) {
  const label = getKeyLabel(k)
  if (!label || props.disabled) return

  const arr = valueArr.value.slice()
  arr[activeIndex.value] = label.toUpperCase()

  const newValue = arr.join('')
  emit('update:modelValue', newValue)
  emit('change', newValue)

  // 移动到下一位
  if (activeIndex.value < props.length - 1) {
    activeIndex.value++
  }
}

function onDelete() {
  if (props.disabled) return

  const arr = valueArr.value.slice()
  if (arr[activeIndex.value]) {
    arr[activeIndex.value] = ''
  } else if (activeIndex.value > 0) {
    activeIndex.value--
    arr[activeIndex.value] = ''
  }

  const newValue = arr.join('')
  emit('update:modelValue', newValue)
  emit('change', newValue)
}

function onConfirm() {
  emit('confirm', props.modelValue)
  if (props.autoClose) {
    close()
  }
}

watch(() => props.show, async (v) => {
  if (v) {
    kbVisible.value = true
    // 等待渲染后再触发进入态，避免“从中间闪一下”
    await nextTick()
    // 找到第一个空位
    const firstEmpty = valueArr.value.findIndex(c => !c)
    activeIndex.value = firstEmpty >= 0 ? firstEmpty : 0
  } else {
    // 先播放离场动画，再销毁
    setTimeout(() => {
      kbVisible.value = false
    }, ANIM_MS)
  }
}, { immediate: true })

</script>

<style scoped>
.zpi{ position: relative; }

/* 输入框 */
.zpi-box{
  padding: 24rpx;
  background: #FFFFFF;
  border-radius: 16rpx;
  border: 1rpx solid #E5E7EB;
}
.zpi-box.theme-dark{
  background: #1C1C1E;
  border-color: rgba(255,255,255,.1);
}

.zpi-box__hd{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16rpx;
}
.zpi-box__title{
  display: flex;
  flex-direction: column;
  gap: 6rpx;
}
.zpi-title{
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
}
.theme-dark .zpi-title{ color: #F9FAFB; }
.zpi-sub{
  font-size: 24rpx;
  color: #6B7280;
}
.theme-dark .zpi-sub{ color: rgba(249,250,251,.6); }

.zpi-cells{
  display: flex;
  align-items: center;
}
.zpi-cell{
  width: 70rpx;
  height: 80rpx;
  border-radius: 12rpx;
  border: 2rpx solid #E5E7EB;
  background: #F9FAFB;
  display: flex;
  align-items: center;
  justify-content: center;
}
.theme-dark .zpi-cell{
  border-color: rgba(255,255,255,.16);
  background: rgba(255,255,255,.06);
}
.zpi-cell.is-active{
  border-color: #007AFF;
  background: rgba(0,122,255,.06);
}
.zpi-cell.is-filled{
  border-color: #007AFF;
  background: #FFFFFF;
}
.theme-dark .zpi-cell.is-filled{
  background: rgba(255,255,255,.08);
}
.zpi-cell__txt{
  font-size: 36rpx;
  font-weight: 600;
  color: #111827;
}
.theme-dark .zpi-cell__txt{ color: #F9FAFB; }

.zpi-hint{
  margin-top: 12rpx;
}
.zpi-hint__txt{
  font-size: 24rpx;
  color: #6B7280;
}
.theme-dark .zpi-hint__txt{ color: rgba(249,250,251,.6); }

/* 遮罩 */
.zpi-mask{
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,.3);
  z-index: 999;
  opacity: 0;
  pointer-events: none;
  transition: opacity 220ms ease;
}
.zpi-mask--show{
  opacity: 1;
  pointer-events: auto;
}


/* 键盘 */
.zpi-keyboard{
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  background: #D1D5DB;
  z-index: 1000;
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);

  /* off-screen by default */
  transform: translate3d(0, 100%, 0);
  opacity: 0;
  transition: transform 220ms ease, opacity 220ms ease;
  will-change: transform;
  pointer-events: auto;
}
.zpi-keyboard--show{
  transform: translate3d(0, 0, 0);
  opacity: 1;
}
.zpi-keyboard.theme-dark{
  background: #1C1C1E;
}

/* 工具栏 */
.zpi-toolbar{
  height: 88rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #E5E7EB;
  border-bottom: 1rpx solid rgba(0,0,0,.08);
}
.theme-dark .zpi-toolbar{
  background: #2C2C2E;
  border-bottom-color: rgba(255,255,255,.08);
}
.zpi-toolbar__tip{
  font-size: 26rpx;
  color: #6B7280;
}
.theme-dark .zpi-toolbar__tip{ color: rgba(249,250,251,.6); }
.zpi-toolbar__btn{
  font-size: 30rpx;
  font-weight: 600;
  color: #007AFF;
}
.theme-dark .zpi-toolbar__btn{ color: #0A84FF; }

/* 按键区域 */
.zpi-keys{
  padding: 16rpx 12rpx 20rpx;
  min-height: 424rpx; /* 4行键盘固定高度，防止切换乱跳 */
}
.zpi-keys__row{
  display: flex;
  gap: 10rpx;
  margin-bottom: 12rpx;
}
.zpi-keys__row:last-child{
  margin-bottom: 0;
}

.zpi-key{
  flex: 1;
  height: 88rpx;
  position: relative;
  z-index: 1;
  user-select: none;
  -webkit-user-select: none;
  background: #FFFFFF;
  border-radius: 10rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2rpx 4rpx rgba(0,0,0,.08);
}
.theme-dark .zpi-key{
  background: #3A3A3C;
  box-shadow: none;
}
.zpi-key:active{
  opacity: 0.7;
}
.zpi-key--empty{
  opacity: 0;
  pointer-events: none;
}
.zpi-key--del{
  flex: 1.5;
  background: #AEB4BC;
}
.theme-dark .zpi-key--del{
  background: #636366;
}
.zpi-key__text{
  font-size: 40rpx;
  font-weight: 500;
  color: #000000;
}
.theme-dark .zpi-key__text{ color: #FFFFFF; }
</style>
