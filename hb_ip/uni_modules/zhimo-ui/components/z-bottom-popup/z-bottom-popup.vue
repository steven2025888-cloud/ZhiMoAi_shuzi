<template>
  <view v-if="visible" class="zbp-wrap" :style="{ zIndex: zIndex + '' }" @tap="onMaskTap">
    <view class="zbp-mask" :style="{ background: maskColor }"></view>

    <!-- 阻止冒泡：避免点内容触发遮罩关闭（不使用 .stop，兼容不同编译/runtime） -->
    <view class="zbp-sheet" :style="{ height: sheetHeight, borderTopLeftRadius: radiusRpx, borderTopRightRadius: radiusRpx, background: background }" @tap="onSheetTap">
      <slot />
    </view>
  </view>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  height: { type: [Number, String], default: 900 }, // rpx
  radius: { type: [Number, String], default: 24 }, // rpx
  zIndex: { type: [Number, String], default: 99 },
  maskColor: { type: String, default: 'rgba(0,0,0,0.45)' },
  background: { type: String, default: '#fff' },
  closeOnMask: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = computed(() => !!props.modelValue)
const sheetHeight = computed(() => (typeof props.height === 'number' ? props.height + 'rpx' : props.height))
const radiusRpx = computed(() => (typeof props.radius === 'number' ? props.radius + 'rpx' : props.radius))

function onMaskTap () {
  if (!props.closeOnMask) return
  emit('update:modelValue', false)
  emit('close')
}

function onSheetTap (e) {
  // 关键：阻止事件冒泡到遮罩
  if (e && typeof e.stopPropagation === 'function') e.stopPropagation()
}
</script>

<style>
.zbp-wrap{
  position: fixed;
  left:0; top:0; right:0; bottom:0;
}
.zbp-mask{
  position:absolute; left:0; top:0; right:0; bottom:0;
}
.zbp-sheet{
  position:absolute;
  left:0; right:0; bottom:0;
  overflow:hidden;
}
</style>
