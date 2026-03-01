<template>
  <view class="z-oc" :class="[dense ? 'is-dense' : '', outlined ? 'is-outlined' : '', soft ? 'is-soft' : '']">
    <!-- Header -->
    <view class="z-oc__hd">
      <view class="z-oc__hd-left">
        <!-- ✅ Tag：优先你传的 tag；否则 autoTag=true 时用 statusType 生成 -->
        <view v-if="tagText" class="z-oc__tag" :style="tagStyle">
          <text class="z-oc__tagtext">{{ tagText }}</text>
        </view>

        <text class="z-oc__title">{{ title }}</text>
      </view>

      <view class="z-oc__hd-right">
        <!-- ✅ Status：只要 status 有值就显示，并支持 statusColor -->
        <text
          v-if="status"
          class="z-oc__status"
          :style="{ color: statusColor || statusPreset.color }"
        >
          {{ status }}
        </text>

        <text v-if="amount" class="z-oc__amount">{{ amount }}</text>
      </view>
    </view>

    <!-- sub line -->
    <view v-if="sub" class="z-oc__sub">
      <text class="z-oc__subtext">{{ sub }}</text>
    </view>

    <!-- card divider -->
    <view v-if="divider" class="z-oc__line" :style="dividerStyle" />

    <!-- Rows -->
    <view class="z-oc__bd">
      <view v-for="(row, idx) in rows" :key="idx" class="z-oc__row">
        <view class="z-oc__row-left">
          <image v-if="row.icon" class="z-oc__icon" :src="row.icon" mode="aspectFit" />
          <text class="z-oc__label">{{ row.label }}</text>
        </view>

        <text class="z-oc__value" :class="[row.muted ? 'is-muted' : '', row.emph ? 'is-emph' : '']">
          {{ row.value }}
        </text>

        <view v-if="rowDivider && idx !== rows.length - 1" class="z-oc__rowline" :style="rowLineStyle" />
      </view>
    </view>

    <view v-if="divider && actions.length" class="z-oc__line" :style="dividerStyle" />

    <!-- Actions -->
    <view v-if="actions.length" class="z-oc__ft">
      <view
        v-for="(a, i) in actions"
        :key="i"
        class="z-oc__btn"
        :class="[a.type ? 'is-' + a.type : 'is-ghost', a.disabled ? 'is-disabled' : '']"
        :hover-class="a.disabled ? '' : 'is-press'"
        hover-stay-time="80"
        @tap="onAction(i)"
      >
        <text class="z-oc__btntext">{{ a.text }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type StatusType =
  | 'pending_pay'
  | 'pending_ship'
  | 'shipping'
  | 'pending_receive'
  | 'done'
  | 'refund'
  | 'closed'

export type OrderRowItem = {
  label: string
  value: string
  icon?: string
  muted?: boolean
  emph?: boolean
}

export type OrderActionItem = {
  text: string
  type?: 'primary' | 'danger' | 'ghost'
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    title: string
    status?: string
    statusColor?: string
    amount?: string
    sub?: string

    // ✅ 自动标签/配色（你也可以完全手动传 tagBg/tagColor/statusColor）
    statusType?: StatusType
    autoTag?: boolean

    // Tag 手动控制
    tag?: string
    tagBg?: string
    tagColor?: string
    tagBorder?: string

    // 行数据/按钮
    rows: OrderRowItem[]
    actions?: OrderActionItem[]

    // 外观
    divider?: boolean
    rowDivider?: boolean
    dense?: boolean
    outlined?: boolean
    soft?: boolean

    // 分割线缩进（更商城）
    dividerInset?: number
  }>(),
  {
    status: '',
    statusColor: '',
    amount: '',
    sub: '',

    statusType: 'pending_ship',
    autoTag: true,

    tag: '',
    tagBg: '',
    tagColor: '',
    tagBorder: '',

    actions: () => [],

    divider: true,
    rowDivider: true,
    dense: true,
    outlined: true,
    soft: false,

    dividerInset: 0
  }
)

const emit = defineEmits<{
  (e: 'action', payload: { index: number; item: OrderActionItem }): void
}>()

// ✅ 电商状态色：文字+底色+边框（每个状态都不同）
const STATUS_STYLE: Record<StatusType, { text: string; color: string; bg: string; bd: string }> = {
  pending_pay:     { text: '待付款',   color: '#B45309', bg: 'rgba(245,158,11,0.12)', bd: 'rgba(245,158,11,0.22)' },
  pending_ship:    { text: '待发货',   color: '#1D4ED8', bg: 'rgba(59,130,246,0.10)', bd: 'rgba(59,130,246,0.18)' },
  shipping:        { text: '已发货',   color: '#6D28D9', bg: 'rgba(124,58,237,0.10)', bd: 'rgba(124,58,237,0.18)' },
  pending_receive: { text: '待收货',   color: '#0E7490', bg: 'rgba(6,182,212,0.10)',  bd: 'rgba(6,182,212,0.18)' },
  done:            { text: '已完成',   color: '#15803D', bg: 'rgba(34,197,94,0.10)',  bd: 'rgba(34,197,94,0.18)' },
  refund:          { text: '售后中',   color: '#B91C1C', bg: 'rgba(239,68,68,0.10)',  bd: 'rgba(239,68,68,0.18)' },
  closed:          { text: '已关闭',   color: 'rgba(17,24,39,0.65)', bg: 'rgba(17,24,39,0.06)', bd: 'rgba(17,24,39,0.10)' }
}

const statusPreset = computed(() => STATUS_STYLE[props.statusType] || STATUS_STYLE.pending_ship)

// ✅ Tag 文本：优先你传的 tag；否则 autoTag=true 用预设
const tagText = computed(() => {
  if (props.tag) return props.tag
  return props.autoTag ? statusPreset.value.text : ''
})

// ✅ Tag 样式：你传什么就用什么；没传就用预设（关键：backgroundColor）
const tagStyle = computed(() => ({
  backgroundColor: props.tagBg || statusPreset.value.bg,
  color: props.tagColor || statusPreset.value.color,
  borderColor: props.tagBorder || statusPreset.value.bd
}))

const dividerStyle = computed(() => ({
  marginLeft: `${props.dividerInset}rpx`,
  marginRight: `${props.dividerInset}rpx`
}))

const rowLineStyle = computed(() => ({
  left: `${props.dividerInset}rpx`,
  right: `${props.dividerInset}rpx`
}))

function onAction(index: number) {
  const a = props.actions[index]
  if (!a || a.disabled) return
  emit('action', { index, item: a })
}
</script>

<style scoped lang="scss">
/* —— 商城"小而美"订单卡片 —— */
.z-oc {
  border-radius: 20rpx;
  background: #fff;
  overflow: hidden;
  box-sizing: border-box;
  box-shadow: 0 4rpx 16rpx rgba(0, 0, 0, 0.04), 0 2rpx 8rpx rgba(0, 0, 0, 0.02);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3rpx;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:active {
    transform: scale(0.995);
    box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.06);
  }
}

.z-oc.is-outlined {
  border: 1px solid rgba(17, 24, 39, 0.08);
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.03);

  &:hover::before {
    opacity: 1;
  }
}

.z-oc.is-soft {
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border: 1px solid rgba(17, 24, 39, 0.04);
}

/* 紧凑：更像商城列表 */
.z-oc.is-dense .z-oc__hd { padding: 20rpx 20rpx 12rpx; }
.z-oc.is-dense .z-oc__sub { padding: 0 20rpx 12rpx; }
.z-oc.is-dense .z-oc__bd { padding: 10rpx 20rpx; }
.z-oc.is-dense .z-oc__ft { padding: 14rpx 20rpx 18rpx; }

/* Header：全居中对齐 */
.z-oc__hd {
  padding: 24rpx 24rpx 14rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14rpx;
  position: relative;
}

.z-oc__hd-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
  flex: 1;
}

/* ✅ 胶囊标签：增强视觉效果 */
.z-oc__tag {
  padding: 10rpx 14rpx;
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border: 1px solid;
  position: relative;
  overflow: hidden;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.08);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.5s ease;
  }

  &:active::before {
    left: 100%;
  }
}

.z-oc__tagtext {
  font-size: 22rpx;
  line-height: 24rpx;
  font-weight: 700;
  letter-spacing: 0.5rpx;
}

.z-oc__title {
  font-size: 28rpx;
  line-height: 32rpx;
  font-weight: 700;
  color: #111827;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: 0.3rpx;
}

.z-oc__hd-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: center;
  gap: 8rpx;
  flex-shrink: 0;
}

.z-oc__status {
  font-size: 24rpx;
  line-height: 26rpx;
  font-weight: 600;
  padding: 4rpx 8rpx;
  border-radius: 6rpx;
  background: rgba(0, 0, 0, 0.02);
}

.z-oc__amount {
  font-size: 30rpx;
  line-height: 32rpx;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.5rpx;
  background: linear-gradient(135deg, #111827 0%, #374151 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.z-oc__sub {
  padding: 0 24rpx 14rpx;
}

.z-oc__subtext {
  font-size: 24rpx;
  line-height: 28rpx;
  color: rgba(17, 24, 39, 0.6);
}

.z-oc__line {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, rgba(17, 24, 39, 0.08) 20%, rgba(17, 24, 39, 0.08) 80%, transparent 100%);
  transform: scaleY(0.5);
  transform-origin: 0 0;
}

/* Rows：全居中 + 小字体 */
.z-oc__bd {
  padding: 14rpx 24rpx;
}

.z-oc__row {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14rpx 0;
  gap: 14rpx;
  transition: background 0.2s ease;
  border-radius: 8rpx;
  margin: 0 -8rpx;
  padding-left: 8rpx;
  padding-right: 8rpx;

  &:active {
    background: rgba(0, 0, 0, 0.02);
  }
}

.z-oc__row-left {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
  flex: 0 0 auto;
}

.z-oc__icon {
  width: 32rpx;
  height: 32rpx;
  opacity: 0.85;
  filter: drop-shadow(0 1rpx 2rpx rgba(0, 0, 0, 0.1));
  transition: transform 0.2s ease;

  .z-oc__row:active & {
    transform: scale(1.1);
  }
}

.z-oc__label {
  font-size: 24rpx;
  line-height: 28rpx;
  color: rgba(17, 24, 39, 0.65);
  font-weight: 500;
}

.z-oc__value {
  flex: 1;
  min-width: 0;
  text-align: right;
  font-size: 25rpx;
  line-height: 28rpx;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.z-oc__value.is-muted {
  color: rgba(17, 24, 39, 0.5);
  font-weight: 500;
}

.z-oc__value.is-emph {
  color: #111827;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.z-oc__rowline {
  position: absolute;
  bottom: 0;
  height: 1px;
  background: rgba(17, 24, 39, 0.06);
  transform: scaleY(0.5);
  transform-origin: 0 100%;
}

/* Actions：按压态整块覆盖 + 圆角不漏 */
.z-oc__ft {
  padding: 16rpx 24rpx 20rpx;
  display: flex;
  justify-content: flex-end;
  gap: 14rpx;
}

.z-oc__btn {
  height: 68rpx;
  min-width: 140rpx;
  padding: 0 24rpx;
  border-radius: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  background: transparent;
  overflow: hidden;
  position: relative;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: translate(-50%, -50%);
    transition: width 0.3s ease, height 0.3s ease;
  }

  &:active::before {
    width: 200%;
    height: 200%;
  }
}

.z-oc__btn.is-press {
  transform: scale(0.96);
}

.z-oc__btntext {
  font-size: 26rpx;
  line-height: 28rpx;
  font-weight: 600;
  letter-spacing: 0.3rpx;
  position: relative;
  z-index: 1;
}

/* 三种按钮（增强视觉效果） */
.z-oc__btn.is-ghost {
  border: 1px solid rgba(17, 24, 39, 0.12);
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.04);

  &:active {
    background: rgba(17, 24, 39, 0.04);
    border-color: rgba(17, 24, 39, 0.18);
  }
}

.z-oc__btn.is-ghost .z-oc__btntext {
  color: #374151;
}

.z-oc__btn.is-primary {
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.12) 0%, rgba(99, 102, 241, 0.12) 100%);
  border: 1px solid rgba(79, 70, 229, 0.25);
  box-shadow: 0 4rpx 12rpx rgba(79, 70, 229, 0.15);

  &:active {
    background: linear-gradient(135deg, rgba(79, 70, 229, 0.18) 0%, rgba(99, 102, 241, 0.18) 100%);
    box-shadow: 0 2rpx 8rpx rgba(79, 70, 229, 0.2);
  }
}

.z-oc__btn.is-primary .z-oc__btntext {
  color: #4F46E5;
  font-weight: 700;
}

.z-oc__btn.is-danger {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(220, 38, 38, 0.1) 100%);
  border: 1px solid rgba(239, 68, 68, 0.25);
  box-shadow: 0 4rpx 12rpx rgba(239, 68, 68, 0.12);

  &:active {
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.15) 100%);
    box-shadow: 0 2rpx 8rpx rgba(239, 68, 68, 0.18);
  }
}

.z-oc__btn.is-danger .z-oc__btntext {
  color: #DC2626;
  font-weight: 700;
}

.z-oc__btn.is-disabled {
  opacity: 0.4;
  pointer-events: none;
}
</style>
