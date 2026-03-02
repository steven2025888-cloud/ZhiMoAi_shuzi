# z-plate-input

车牌号输入组件（Vue3 / `<script setup>`），内置车牌键盘：
- 支持 7 位 / 8 位
- 支持省份键盘与字母数字键盘切换
- 支持删除、完成、遮罩关闭、深色主题、安全区

## 使用

```vue
<z-plate-input v-model="plate" v-model:show="showKb" :length="7" />
```

演示页面：`/pages/data/plate-input.vue`
