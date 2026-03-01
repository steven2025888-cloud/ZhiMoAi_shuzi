# z-slider

一个轻量的滑块选择器（Vue3 / `<script setup>`），支持单值与区间选择（range），支持 `marks` 刻度点。

## 用法

```vue
<template>
  <z-slider v-model="v" :min="0" :max="100" :step="5" showValue />
  <z-slider v-model="r" range :min="0" :max="24" :step="1" :marks="marks" showValue />
</template>

<script setup>
import { ref } from 'vue'
const v = ref(30)
const r = ref([6, 18])
const marks = [
  { value: 0, label: '0h' },
  { value: 6, label: '早' },
  { value: 12, label: '中' },
  { value: 18, label: '晚' },
  { value: 24, label: '24h' },
]
</script>
```

## Props

- `modelValue`：`number | [number, number]`
- `range`：是否区间选择
- `min / max / step`
- `width / height / radius`
- `railColor / fillColor`
- `thumbSize / thumbColor / thumbBorder / thumbShadow`
- `disabled`
- `showValue`
- `formatter(v:number)=>string`
- `marks`: `Array<{value:number,label?:string}>`

## Events

- `update:modelValue`
- `changing({ value })`：拖动中实时回调
- `change({ value })`：抬手后回调
