<template>
  <checkbox-group class="z-checkbox-group" :name="name">
    <slot />
  </checkbox-group>
</template>

<script setup>
import { computed, provide } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  name: { type: String, default: '' },

  disabled: { type: Boolean, default: false },
  color: { type: String, default: '#2b7cff' },
  shape: { type: String, default: 'square' }, // square | circle
  gap: { type: Number, default: 16 },         // rpx spacing
  shadow: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'change'])

const value = computed(() => Array.isArray(props.modelValue) ? props.modelValue : [])

function toggle(v) {
  if (props.disabled) return
  const list = value.value.slice()
  const i = list.findIndex(x => x === v)
  if (i >= 0) list.splice(i, 1)
  else list.push(v)
  emit('update:modelValue', list)
  emit('change', list)
}

provide('zCheckboxGroup', { value, toggle, props })
</script>

<style scoped>
.z-checkbox-group{ width:100%; }
</style>