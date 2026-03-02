<template>
  <view class="z-upload">
    <view class="z-upload__grid">
      <view
        v-for="(url, idx) in inner"
        :key="url + '_' + idx"
        class="z-upload__cell"
        :style="cellStyle"
      >
        <image class="z-upload__img" :src="url" mode="aspectFill" @tap="preview(idx)" />
        <view v-if="deletable" class="z-upload__del" @tap.stop="remove(idx)">
          <text class="z-upload__del-x">×</text>
        </view>
      </view>

      <view
        v-if="showAdd && inner.length < maxCount"
        class="z-upload__cell z-upload__add"
        :style="cellStyle"
        @tap="pick"
      >
        <text class="z-upload__plus">＋</text>
        <text class="z-upload__hint">上传</text>
      </view>
    </view>
    <view v-if="tip" class="z-upload__tip"><text class="z-upload__tip-text">{{ tip }}</text></view>
  </view>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  maxCount: { type: Number, default: 6 },
  size: { type: Number, default: 160 }, // rpx
  radius: { type: Number, default: 18 },
  gap: { type: Number, default: 12 },
  deletable: { type: Boolean, default: true },
  showAdd: { type: Boolean, default: true },
  tip: { type: String, default: '' },
  compress: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'change', 'remove', 'add'])

const inner = ref([...(props.modelValue || [])])
watch(() => props.modelValue, v => { inner.value = [...(v || [])] }, { deep: true })

const cellStyle = computed(() => ({
  width: props.size + 'rpx',
  height: props.size + 'rpx',
  borderRadius: props.radius + 'rpx',
  marginRight: props.gap + 'rpx',
  marginBottom: props.gap + 'rpx',
}))

function sync(next) {
  inner.value = next
  emit('update:modelValue', next)
  emit('change', next)
}

function pick() {
  const remain = props.maxCount - inner.value.length
  if (remain <= 0) return
  uni.chooseImage({
    count: remain,
    sizeType: props.compress ? ['compressed'] : ['original', 'compressed'],
    success(res) {
      const files = res?.tempFilePaths || []
      const next = inner.value.concat(files)
      sync(next)
      emit('add', files)
    }
  })
}

function preview(idx) {
  const urls = inner.value
  if (!urls.length) return
  uni.previewImage({
    current: urls[idx],
    urls
  })
}

function remove(idx) {
  const next = inner.value.slice()
  const removed = next.splice(idx, 1)
  sync(next)
  emit('remove', removed[0])
}
</script>

<style scoped>
.z-upload__grid{
  display:flex;
  flex-wrap: wrap;
}
.z-upload__cell{
  position: relative;
  background: rgba(0,0,0,.03);
  border: 1px dashed rgba(0,0,0,.18);
  overflow:hidden;
  box-sizing: border-box;
}
.z-upload__img{
  width: 100%;
  height: 100%;
}
.z-upload__del{
  position:absolute;
  top: 8rpx;
  right: 8rpx;
  width: 38rpx;
  height: 38rpx;
  border-radius: 999rpx;
  background: rgba(0,0,0,.55);
  display:flex;
  align-items:center;
  justify-content:center;
}
.z-upload__del-x{
  color:#fff;
  font-size: 28rpx;
  line-height: 1;
}
.z-upload__add{
  display:flex;
  align-items:center;
  justify-content:center;
  flex-direction:column;
  border-style: solid;
}
.z-upload__plus{
  font-size: 40rpx;
  line-height: 1;
  opacity:.8;
}
.z-upload__hint{
  margin-top: 6rpx;
  font-size: 22rpx;
  opacity:.65;
}
.z-upload__tip{ margin-top: 4rpx; }
.z-upload__tip-text{ font-size: 22rpx; opacity:.6; }
</style>
