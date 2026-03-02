<template>
  <view class="z-form">
    <slot />
  </view>
</template>

<script setup>
import { provide, reactive, toRefs, watch, computed } from 'vue'
import { validateValue } from '../../utils/validate.js'

const props = defineProps({
  model: { type: Object, required: true },               // form model object
  rules: { type: Object, default: () => ({}) },          // { fieldName: Rule[] }
  validateOn: { type: String, default: 'submit' },       // 'submit' | 'change' | 'blur'
  scrollToError: { type: Boolean, default: true }
})

const emit = defineEmits(['validate', 'submit'])

const items = reactive(new Map()) // name -> itemApi

function register(name, api) {
  if (!name) return
  items.set(name, api)
}

function unregister(name) {
  if (!name) return
  items.delete(name)
}

async function validate(names) {
  const list = Array.isArray(names) ? names : (typeof names === 'string' ? [names] : Array.from(items.keys()))
  const result = { valid: true, errors: {} }

  for (const name of list) {
    const api = items.get(name)
    const value = api?.getValue?.()
    const rules = api?.getRules?.() ?? props.rules?.[name] ?? []
    const err = await validateValue(rules, value, { name, model: props.model })
    api?.setError?.(err)
    if (err) {
      result.valid = false
      result.errors[name] = err
    }
  }

  emit('validate', result)

  if (!result.valid && props.scrollToError) {
    // Try to scroll to first error item
    const firstName = Object.keys(result.errors)[0]
    const api = items.get(firstName)
    api?.scrollIntoView?.()
  }

  return result
}

function clearValidate(names) {
  const list = Array.isArray(names) ? names : (typeof names === 'string' ? [names] : Array.from(items.keys()))
  for (const name of list) {
    items.get(name)?.setError?.(null)
  }
}

function submit() {
  emit('submit')
}

provide('zForm', {
  register,
  unregister,
  formProps: props,
  validate,
  clearValidate,
  submit
})

defineExpose({ validate, clearValidate, submit })
</script>

<style scoped>
.z-form{
  width: 100%;
}
</style>
