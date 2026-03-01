<template>
  <view class="z-col" :style="wrapStyle">
    <slot />
  </view>
</template>

<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'

type NameType = string | number
type ModelValue = NameType | NameType[] | null

type CollapseChange = {
  name: NameType
  open: boolean
  actives: ModelValue
}

const props = withDefaults(defineProps<{
  /** v-model: active item name(s). accordion: Name|null ; multi: Name[] */
  modelValue?: ModelValue
  /** accordion mode */
  accordion?: boolean

  /** container styles */
  background?: string
  radius?: string | number
  padding?: string | (string | number)[]
  gap?: string | number
  bordered?: boolean
  borderColor?: string
  shadow?: boolean

  /** animation defaults (items can override) */
  animation?: boolean
  duration?: number
  lazy?: boolean

  /** tag: passthrough in events */
  tag?: any
}>(), {
  modelValue: undefined,
  accordion: false,

  background: 'transparent',
  radius: 16,
  padding: '',
  gap: 16,
  bordered: false,
  borderColor: 'rgba(0,0,0,0.08)',
  shadow: false,

  animation: true,
  duration: 220,
  lazy: false,

  tag: 0
})

const emit = defineEmits<{
  (e: 'update:modelValue', v: ModelValue): void
  (e: 'change', payload: CollapseChange & { tag: any }): void
}>()

function toUnit(v: any, unit = 'rpx') {
  if (v == null || v === '') return ''
  if (typeof v === 'number') return `${v}${unit}`
  return String(v)
}

function normalizePadding(p: any): string {
  if (!p) return ''
  if (typeof p === 'string') return p
  if (!Array.isArray(p)) return ''
  const a = p.map((x) => (typeof x === 'number' ? `${x}rpx` : String(x)))
  if (a.length === 1) return a[0]
  if (a.length === 2) return `${a[0]} ${a[1]}`
  if (a.length === 3) return `${a[0]} ${a[1]} ${a[2]}`
  return `${a[0]} ${a[1]} ${a[2]} ${a[3]}`
}

/**
 * Provide/Inject key:
 * 注意：某些 uni-app 编译器对 <script setup> 的 export 支持不完整，
 * 所以这里用字符串 key，避免 `export { ... }` 报错。
 */
const Z_COLLAPSE_INJECT_KEY = 'z-collapse-ctx'

const inner = ref<ModelValue>(props.accordion ? null : [])
watch(
  () => props.accordion,
  (acc) => {
    if (props.modelValue !== undefined) return
    inner.value = acc ? null : []
  }
)

const actives = computed<ModelValue>(() => {
  return props.modelValue !== undefined ? props.modelValue : inner.value
})

function hasActive(name: NameType): boolean {
  const v = actives.value
  if (props.accordion) return v === name
  if (Array.isArray(v)) return v.includes(name)
  return false
}

function toggle(name: NameType) {
  const isOpen = hasActive(name)
  let next: ModelValue

  if (props.accordion) {
    next = isOpen ? null : name
  } else {
    const cur = Array.isArray(actives.value) ? [...actives.value] : []
    if (isOpen) next = cur.filter((x) => x !== name)
    else { cur.push(name); next = cur }
  }

  if (props.modelValue === undefined) inner.value = next
  emit('update:modelValue', next)
  emit('change', { name, open: !isOpen, actives: next, tag: props.tag })
}

const defaults = computed(() => ({
  animation: props.animation,
  duration: props.duration,
  lazy: props.lazy,
  gap: toUnit(props.gap),
  radius: toUnit(props.radius),
  bordered: props.bordered,
  borderColor: props.borderColor,
  background: props.background,
  shadow: props.shadow
}))

const wrapStyle = computed(() => {
  const style: Record<string, any> = {
    background: props.background,
    borderRadius: toUnit(props.radius),
    padding: normalizePadding(props.padding),
    overflow: 'hidden'
  }
  if (props.bordered) {
    style.borderWidth = '2rpx'
    style.borderStyle = 'solid'
    style.borderColor = props.borderColor
  } else {
    style.borderWidth = '0'
  }
  if (props.shadow) {
    style.boxShadow = '0 12rpx 28rpx rgba(0,0,0,0.08)'
  }
  return style
})

type CollapseCtx = {
  hasActive: (name: NameType) => boolean
  toggle: (name: NameType) => void
  defaults: typeof defaults
  key: string
}

provide(Z_COLLAPSE_INJECT_KEY, {
  hasActive,
  toggle,
  defaults,
  key: Z_COLLAPSE_INJECT_KEY
} as CollapseCtx)
</script>

<style scoped>
.z-col{
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
</style>
