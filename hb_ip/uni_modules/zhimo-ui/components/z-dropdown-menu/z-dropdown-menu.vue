<template>
  <view class="zdm">
    <!-- Trigger -->
    <view class="zdm__trigger" @tap="onTriggerTap" @touchstart.stop @touchend.stop>
      <slot name="trigger">
        <view class="zdm__trigger-inner" :class="{ 'is-open': show }">
          <text class="zdm__trigger-text" :class="{ 'is-placeholder': !displayText }">
            {{ displayText || placeholder }}
          </text>
          <view class="zdm__trigger-icon" :class="{ 'is-rot': show }">
            <z-icon :name="triggerIcon" :size="triggerIconSize" />
          </view>
        </view>
      </slot>
    </view>

    <!-- Overlay -->
    <view
      v-if="show"
      class="zdm__overlay"
      :style="{ zIndex: String(zIndex) }"
      :catchtouchmove="lockScroll"
      @touchmove.stop.prevent
      @tap="onMaskTap"
    >
      <!-- mask -->
      <view class="zdm__mask" :style="maskStyle" />

      <!-- menu -->
      <view
        class="zdm__menu"
        :class="[{ 'is-dark': theme === 'dark' }, `p-${placementSide}`]"
        :style="menuStyle"
        @tap.stop
      >
        <!-- header -->
        <view v-if="title || $slots.header" class="zdm__header">
          <slot name="header">
            <view class="zdm__header-main">
              <text class="zdm__title">{{ title }}</text>
              <text v-if="subtitle" class="zdm__subtitle">{{ subtitle }}</text>
            </view>
          </slot>
        </view>

        <!-- list -->
        <scroll-view class="zdm__list" :scroll-y="true" :show-scrollbar="false" :style="listStyle">
          <view v-if="options.length === 0" class="zdm__empty">
            <text class="zdm__empty-text">{{ emptyText }}</text>
          </view>

          <view
            v-for="(opt, idx) in normalizedOptions"
            :key="opt.__key"
            class="zdm__item"
            :class="itemClass(opt)"
            @tap.stop.prevent="onItemTap(opt, idx)"
          >
            <slot name="item" :option="opt" :index="idx">
              <view class="zdm__item-left">
                <view v-if="opt.icon" class="zdm__item-icon">
                  <z-icon :name="opt.icon" :size="iconSize" />
                </view>

                <view class="zdm__item-texts">
                  <text class="zdm__item-label">{{ opt.label }}</text>
                  <text v-if="opt.desc" class="zdm__item-desc">{{ opt.desc }}</text>
                </view>
              </view>

              <view class="zdm__item-right">
                <view v-if="multiple" class="zdm__checkbox" :class="{ 'is-on': isChecked(opt) }" />
                <view v-else class="zdm__check">
                  <z-icon v-if="isChecked(opt)" name="check" :size="checkIconSize" />
                </view>
              </view>
            </slot>
          </view>
        </scroll-view>

        <!-- footer -->
        <view v-if="multiple && showFooter" class="zdm__footer">
          <slot name="footer">
            <view class="zdm__footer-actions">
              <z-button type="text" @tap="close">取消</z-button>
              <z-button type="primary" @tap="confirm">确定</z-button>
            </view>
          </slot>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, ref, watch } from 'vue'

type Theme = 'light' | 'dark'
type Placement = 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end'

type OptionValue = string | number | boolean | object | null
type MenuOption = {
  label: string
  value: OptionValue
  icon?: string
  desc?: string
  disabled?: boolean
  danger?: boolean
}

const props = withDefaults(
  defineProps<{
    /** selected value (single) */
    value?: OptionValue
    /** selected values (multiple) */
    values?: OptionValue[]
    /** menu options */
    options?: Array<string | MenuOption>
    /** show menu */
    modelValue?: boolean

    /** UI */
    placeholder?: string
    title?: string
    subtitle?: string
    emptyText?: string
    theme?: Theme

    /** behavior */
    multiple?: boolean
    closeOnSelect?: boolean
    closeOnMask?: boolean
    lockScroll?: boolean
    showFooter?: boolean

    /** placement */
    placement?: Placement
    offsetY?: number | string
    minWidth?: string
    maxHeight?: string

    /** colors */
    maskColor?: string
    zIndex?: number

    /** icons */
    triggerIcon?: string
    triggerIconSize?: number
    iconSize?: number
    checkIconSize?: number
  }>(),
  {
    value: null,
    values: () => [],
    options: () => [],
    modelValue: false,

    placeholder: '请选择',
    title: '',
    subtitle: '',
    emptyText: '暂无选项',
    theme: 'light',

    multiple: false,
    closeOnSelect: true,
    closeOnMask: true,
    lockScroll: true,
    showFooter: true,

    placement: 'bottom-start',
    offsetY: 10, // px
    minWidth: '220rpx',
    maxHeight: '520rpx',

    maskColor: 'rgba(0,0,0,0.45)',
    zIndex: 3000,

    triggerIcon: 'chevron-down',
    triggerIconSize: 18,
    iconSize: 18,
    checkIconSize: 18,
  }
)

const emit = defineEmits<{
  (e: 'update:value', v: OptionValue): void
  (e: 'update:values', v: OptionValue[]): void
  (e: 'update:modelValue', v: boolean): void
  (e: 'open'): void
  (e: 'close'): void
  (e: 'select', payload: { option: MenuOption; index: number }): void
  (e: 'confirm', v: OptionValue[]): void
}>()

const show = ref(!!props.modelValue)
watch(
  () => props.modelValue,
  (v) => (show.value = !!v)
)
watch(show, (v) => emit('update:modelValue', v))

const inst = getCurrentInstance()
const triggerRect = ref<{ left: number; top: number; width: number; height: number }>({ left: 0, top: 0, width: 0, height: 0 })
const screen = ref({ windowWidth: 375, windowHeight: 667 })

const normalizedOptions = computed(() => {
  const raw = props.options || []
  return raw.map((it, idx) => {
    const opt: MenuOption =
      typeof it === 'string'
        ? { label: it, value: it }
        : {
            label: it.label,
            value: it.value,
            icon: it.icon,
            desc: it.desc,
            disabled: !!it.disabled,
            danger: !!it.danger,
          }
    // stable key
    return { ...opt, __key: `${idx}-${opt.label}-${String((opt.value as any) ?? '')}` }
  })
})

const displayText = computed(() => {
  if (props.multiple) {
    const vs = new Set((props.values || []).map((v) => stringify(v)))
    const labels = normalizedOptions.value.filter((o) => vs.has(stringify(o.value))).map((o) => o.label)
    return labels.join('、')
  }
  const v = stringify(props.value)
  const found = normalizedOptions.value.find((o) => stringify(o.value) === v)
  return found?.label || ''
})

const placementSide = computed(() => (props.placement.startsWith('top') ? 'top' : 'bottom'))

const maskStyle = computed(() => ({ background: props.maskColor }))

const listStyle = computed(() => ({ maxHeight: props.maxHeight }))

const menuStyle = computed(() => {
  const { left, top, width, height } = triggerRect.value
  const offsetY = typeof props.offsetY === 'number' ? props.offsetY : parseFloat(String(props.offsetY || 0))
  const minW = props.minWidth || '220rpx'
  const base: Record<string, any> = {
    minWidth: minW,
  }

  const isTop = props.placement.startsWith('top')
  const y = isTop ? top - offsetY : top + height + offsetY
  base.top = `${y}px`

  // align start/end
  const alignEnd = props.placement.endsWith('end')
  if (alignEnd) {
    base.right = `${Math.max(12, screen.value.windowWidth - (left + width))}px`
  } else {
    base.left = `${Math.max(12, left)}px`
  }

  return base
})

function stringify(v: any) {
  try {
    return typeof v === 'string' ? v : JSON.stringify(v)
  } catch {
    return String(v)
  }
}

function isChecked(opt: MenuOption) {
  if (props.multiple) {
    const vs = new Set((props.values || []).map((v) => stringify(v)))
    return vs.has(stringify(opt.value))
  }
  return stringify(props.value) === stringify(opt.value)
}

function itemClass(opt: MenuOption) {
  return {
    'is-disabled': !!opt.disabled,
    'is-danger': !!opt.danger,
    'is-active': isChecked(opt),
  }
}

async function measure() {
  // refresh screen
  try {
    const info = uni.getSystemInfoSync()
    screen.value.windowWidth = info.windowWidth || 375
    screen.value.windowHeight = info.windowHeight || 667
  } catch {}

  await nextTick()
  const q = uni.createSelectorQuery().in(inst?.proxy as any)
  q.select('.zdm__trigger')
    .boundingClientRect((rect: any) => {
      if (!rect) return
      triggerRect.value = { left: rect.left, top: rect.top, width: rect.width, height: rect.height }
    })
    .exec()
}

async function open() {
  await measure()
  show.value = true
  emit('open')
}

function close() {
  show.value = false
  emit('close')
}

function toggle() {
  if (show.value) close()
  else open()
}

function onTriggerTap() {
  toggle()
}

function onMaskTap() {
  if (!props.closeOnMask) return
  close()
}

function onItemTap(opt: MenuOption, index: number) {
  if (opt.disabled) return

  emit('select', { option: opt, index })

  if (props.multiple) {
    const next = new Set((props.values || []).map((v) => stringify(v)))
    const key = stringify(opt.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)

    // convert back to values using original types when possible
    const result: OptionValue[] = []
    normalizedOptions.value.forEach((o) => {
      if (next.has(stringify(o.value))) result.push(o.value)
    })
    emit('update:values', result)
    if (props.closeOnSelect && !props.showFooter) close()
    return
  }

  emit('update:value', opt.value)
  if (props.closeOnSelect) close()
}

function confirm() {
  emit('confirm', props.values || [])
  close()
}
</script>

<style scoped>
/* wrapper */
.zdm { display: inline-block; }

/* trigger */
.zdm__trigger { width: 100%; }
.zdm__trigger-inner {
  height: 76rpx;
  padding: 0 18rpx;
  border-radius: 18rpx;
  background: #ffffff;
  border: 1rpx solid rgba(0,0,0,0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
  box-shadow: 0 10rpx 26rpx rgba(0,0,0,0.05);
}
.zdm__trigger-text {
  font-size: 28rpx;
  color: #111827;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.zdm__trigger-text.is-placeholder { color: #94a3b8; }
.zdm__trigger-icon { opacity: 0.86; }
.zdm__trigger-icon.is-rot { transform: rotate(180deg); transition: transform 160ms ease; }

/* overlay */
.zdm__overlay {
  position: fixed;
  inset: 0;
}
.zdm__mask {
  position: absolute;
  inset: 0;
}
.zdm__menu {
  position: absolute;
  border-radius: 22rpx;
  overflow: hidden;
  border: 1rpx solid rgba(0,0,0,0.08);
  background: #ffffff;
  box-shadow: 0 18rpx 60rpx rgba(0,0,0,0.20);
  transform-origin: top left;
  animation: zdmPop 150ms ease-out;
}
.zdm__menu.p-top { transform-origin: bottom left; }
.zdm__menu.is-dark {
  background: #0b1220;
  border-color: rgba(255,255,255,0.10);
}
@keyframes zdmPop {
  from { transform: translateY(-6px) scale(0.98); opacity: 0.0; }
  to { transform: translateY(0) scale(1); opacity: 1; }
}

/* header */
.zdm__header {
  padding: 18rpx 18rpx 14rpx 18rpx;
  border-bottom: 1rpx solid rgba(0,0,0,0.06);
}
.zdm__menu.is-dark .zdm__header { border-bottom-color: rgba(255,255,255,0.10); }
.zdm__title {
  font-size: 28rpx;
  font-weight: 800;
  color: #0f172a;
}
.zdm__menu.is-dark .zdm__title { color: rgba(255,255,255,0.92); }
.zdm__subtitle {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #64748b;
  line-height: 1.4;
}
.zdm__menu.is-dark .zdm__subtitle { color: rgba(255,255,255,0.68); }

/* list */
.zdm__list { width: 100%; }
.zdm__empty { padding: 26rpx 18rpx; }
.zdm__empty-text { font-size: 24rpx; color: #94a3b8; }
.zdm__menu.is-dark .zdm__empty-text { color: rgba(255,255,255,0.55); }

/* items */
.zdm__item {
  padding: 16rpx 16rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14rpx;
}
.zdm__item + .zdm__item { border-top: 1rpx solid rgba(0,0,0,0.06); }
.zdm__menu.is-dark .zdm__item + .zdm__item { border-top-color: rgba(255,255,255,0.10); }

.zdm__item-left { display: flex; align-items: center; gap: 14rpx; flex: 1; min-width: 0; }
.zdm__item-icon {
  width: 44rpx; height: 44rpx;
  border-radius: 14rpx;
  background: rgba(59,130,246,0.12);
  display: flex;
  align-items: center;
  justify-content: center;
}
.zdm__menu.is-dark .zdm__item-icon { background: rgba(59,130,246,0.18); }
.zdm__item-texts { flex: 1; min-width: 0; }
.zdm__item-label {
  font-size: 28rpx;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.zdm__menu.is-dark .zdm__item-label { color: rgba(255,255,255,0.92); }
.zdm__item-desc {
  margin-top: 6rpx;
  font-size: 24rpx;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.zdm__menu.is-dark .zdm__item-desc { color: rgba(255,255,255,0.64); }

.zdm__item-right { width: 44rpx; display: flex; align-items: center; justify-content: flex-end; }

.zdm__checkbox {
  width: 30rpx; height: 30rpx;
  border-radius: 10rpx;
  border: 2rpx solid rgba(0,0,0,0.22);
}
.zdm__menu.is-dark .zdm__checkbox { border-color: rgba(255,255,255,0.28); }
.zdm__checkbox.is-on {
  border-color: rgba(59,130,246,1);
  background: rgba(59,130,246,1);
  position: relative;
}
.zdm__checkbox.is-on::after {
  content: '';
  position: absolute;
  left: 9rpx; top: 5rpx;
  width: 7rpx; height: 14rpx;
  border: 3rpx solid #fff;
  border-top: 0; border-left: 0;
  transform: rotate(45deg);
}

.zdm__check { opacity: 0.95; }

.zdm__item.is-active { background: rgba(59,130,246,0.08); }
.zdm__menu.is-dark .zdm__item.is-active { background: rgba(59,130,246,0.16); }

.zdm__item.is-danger .zdm__item-label { color: #dc2626; }
.zdm__menu.is-dark .zdm__item.is-danger .zdm__item-label { color: #f87171; }

.zdm__item.is-disabled { opacity: 0.45; }

/* footer */
.zdm__footer {
  padding: 14rpx 16rpx 16rpx 16rpx;
  border-top: 1rpx solid rgba(0,0,0,0.06);
}
.zdm__menu.is-dark .zdm__footer { border-top-color: rgba(255,255,255,0.10); }
.zdm__footer-actions { display: flex; justify-content: flex-end; gap: 14rpx; }
</style>
