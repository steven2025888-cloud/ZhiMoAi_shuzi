<template>
  <view class="z-form-item" :id="anchorId">
    <view class="z-form-item__row" :class="{ 'is-top': labelPosition==='top' }">
      <view v-if="label" class="z-form-item__label" :style="{ width: labelWidthStyle }">
        <text class="z-form-item__label-text">
          <text v-if="requiredMark" class="z-form-item__required">*</text>{{ label }}
        </text>
        <slot name="label" />
      </view>

      <view class="z-form-item__content">
        <slot />
        <view v-if="help" class="z-form-item__help">
          <text class="z-form-item__help-text">{{ help }}</text>
        </view>
        <view v-if="error" class="z-form-item__error">
          <text class="z-form-item__error-text">{{ error }}</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup>
import { inject, ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  label: { type: String, default: '' },
  help: { type: String, default: '' },
  rules: { type: Array, default: null },        // override z-form rules for this field
  labelWidth: { type: [Number, String], default: 180 }, // rpx
  labelPosition: { type: String, default: 'left' },     // left | top
  required: { type: Boolean, default: false },
  scrollOffset: { type: Number, default: 0 }            // px
})

const form = inject('zForm', null)
const error = ref(null)

const anchorId = computed(() => `zfi_${props.name}`)
const labelWidthStyle = computed(() => {
  if (props.labelPosition === 'top') return 'auto'
  const n = Number(props.labelWidth)
  return Number.isFinite(n) ? `${n}rpx` : String(props.labelWidth)
})
const requiredMark = computed(() => {
  if (props.required) return true
  const rules = props.rules || form?.formProps?.rules?.[props.name] || []
  return rules.some(r => r && r.required)
})

function getValue() {
  return form?.formProps?.model?.[props.name]
}

function getRules() {
  return props.rules ?? (form?.formProps?.rules?.[props.name] ?? [])
}

function setError(msg) {
  error.value = msg || null
}

function scrollIntoView() {
  // uni-app scroll into view: use selector query
  nextTick(() => {
    const query = uni.createSelectorQuery()
    query.select('#' + anchorId.value).boundingClientRect()
    query.selectViewport().scrollOffset()
    query.exec(res => {
      const rect = res?.[0]
      const viewport = res?.[1]
      if (!rect || !viewport) return
      const top = rect.top + viewport.scrollTop - props.scrollOffset
      uni.pageScrollTo({ scrollTop: Math.max(top, 0), duration: 250 })
    })
  })
}

onMounted(() => {
  form?.register?.(props.name, { getValue, getRules, setError, scrollIntoView })
})
onBeforeUnmount(() => {
  form?.unregister?.(props.name)
})

defineExpose({ setError })
</script>

<style scoped>
.z-form-item{ width:100%; }
.z-form-item__row{ display:flex; align-items:center; padding: 16rpx 20rpx; }
.z-form-item__row.is-top{ flex-direction:column; align-items:stretch; }
.z-form-item__label{ padding-right: 14rpx; }
.z-form-item__label-text{ font-size: 26rpx; font-weight: 400; opacity: .9; }
.z-form-item__required{ margin-right: 6rpx; color:#ff3b30; }
.z-form-item__content{ flex:1; min-width: 0; }
.z-form-item__help{ margin-top: 12rpx; }
.z-form-item__help-text{ font-size: 22rpx; opacity: .65; }
.z-form-item__error{ margin-top: 12rpx; }
.z-form-item__error-text{ font-size: 22rpx; }


.z-form-item__row.is-top .z-form-item__label{ width:100%; padding-right:0; margin-bottom: 10rpx; }
</style>
