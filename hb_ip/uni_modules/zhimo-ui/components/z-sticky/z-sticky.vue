<template>
  <view
    class="z-sticky"
    :class="{
      'z-sticky--normal': !props.bounded,
      'z-sticky--bounded': props.bounded
    }"
    :style="wrapStyle"
    :id="elId"
    ref="rootEl"
  >
    <view
      class="z-sticky__inner"
      :class="{
        'z-sticky__inner--fixed': !props.bounded && fixed,
        'z-sticky__inner--bounded': props.bounded
      }"
      :style="innerStyle"
    >
      <slot />
    </view>

    <!-- 占位元素，当使用 fixed 定位时保持布局 -->
    <view
      v-if="!props.bounded && fixed"
      class="z-sticky__placeholder"
      :style="{ height: height + 'px' }"
    />
  </view>
</template>

<script setup>
// z-sticky: 吸顶容器（Sticky）
import { computed, getCurrentInstance, nextTick, onMounted, ref, watch } from 'vue'

// #ifdef APP-NVUE
const dom = weex.requireModule('dom')
// #endif

const props = defineProps({
  /** 距离顶部的偏移（px） */
  offsetTop: { type: [Number, String], default: 0 },
  /** 是否限制吸顶范围：只在元素自身高度范围内吸顶 */
  bounded: { type: Boolean, default: false },
  /** 页面滚动距离（px），仅部分端需要手动传入 */
  scrollTop: { type: Number, default: 0 },
  /** 层级 */
  zIndex: { type: [Number, String], default: 999 },
  /** nvue 下可指定容器宽度（rpx），其它端会忽略 */
  width: { type: [Number, String], default: 750 },
  /** 自定义标识（会在 change 事件中原样透传） */
  tag: { type: [String, Number, Object], default: 0 },
  /** 禁用吸顶 */
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['change'])

const inst = getCurrentInstance()
const rootEl = ref(null)

const elId = `z_${Math.ceil(Math.random() * 1e6).toString(36)}`
const elTop = ref(0)
const height = ref(0)
const fixed = ref(false)
const initialized = ref(false) // 标记是否已初始化

const toNum = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const wrapStyle = computed(() => {
  const styles = []

  // #ifdef APP-NVUE
  styles.push(`width:${props.width}rpx`)
  // #endif

  // 非 bounded 模式：在外层设置 top 和 z-index（用于 sticky 定位）
  if (!props.bounded) {
    styles.push(`top:${toNum(props.offsetTop)}px`)
    styles.push(`z-index:${toNum(props.zIndex)}`)
  }

  return styles.join(';')
})

const innerStyle = computed(() => {
  const styles = []

  if (props.bounded) {
    // bounded 模式：在内层设置 sticky 定位的样式
    styles.push(`top:${toNum(props.offsetTop)}px`)
    styles.push(`z-index:${toNum(props.zIndex)}`)
  } else if (fixed.value) {
    // 页面级场景且已吸顶：设置 fixed 定位的样式
    styles.push(`top:${toNum(props.offsetTop)}px`)
    styles.push(`z-index:${toNum(props.zIndex)}`)
  }

  return styles.join(';')
})

function updateSticky() {
  if (props.disabled) {
    if (fixed.value) {
      fixed.value = false
      emit('change', { fixed: false, tag: props.tag })
    }
    return
  }

  const et = elTop.value
  const h = height.value
  const st = props.scrollTop || 0
  const t = toNum(props.offsetTop)

  let isFixed = false
  if (props.bounded) {
    // bounded 模式：只在容器范围内吸顶
    isFixed = st + t >= et && st + t < et + h
  } else {
    // 非 bounded 模式：滚动超过元素位置就吸顶
    isFixed = st + t >= et
  }

  if (fixed.value !== isFixed) {
    fixed.value = isFixed
    emit('change', { fixed: isFixed, tag: props.tag })
  }
}

function initRect(cb) {
  // #ifndef APP-NVUE
  const selector = `#${elId}`
  const q = uni.createSelectorQuery()
  // #ifndef MP-ALIPAY
  if (inst && inst.proxy) q.in(inst.proxy)
  // #endif
  q.select(selector)
    .fields({ size: true, rect: true }, (res) => {
      if (res) {
        elTop.value = res.top + (props.scrollTop || 0)
        height.value = res.height
        cb && cb()
      }
    })
    .exec()
  // #endif

  // #ifdef APP-NVUE
  dom.getComponentRect(rootEl.value, (option) => {
    if (option && option.result && option.size) {
      height.value = option.size.height + 1
      elTop.value = option.size.top + (props.scrollTop || 0)
      cb && cb()
    }
  })
  // #endif
}

function refresh() {
  nextTick(() => {
    setTimeout(() => initRect(updateSticky), 30)
  })
}

watch(
  () => props.scrollTop,
  (newVal, oldVal) => {
    // 第一次 scrollTop 变化时，初始化位置信息
    if (!initialized.value && newVal > 0) {
      initialized.value = true
      refresh()
    } else if (initialized.value) {
      // 已初始化后，只更新吸顶状态
      updateSticky()
    }
  }
)

onMounted(() => {
  // 如果传了 scrollTop 或者是 bounded 模式，需要初始化
  if (props.scrollTop > 0 || props.bounded) {
    initialized.value = true
    refresh()
  }
  // 否则（scroll-view 场景），不需要初始化，使用纯 CSS sticky
})

defineExpose({
  /** 手动刷新位置与吸顶状态（比如 slot 内容异步变化后） */
  refresh
})
</script>

<style scoped>
.z-sticky {
  /* #ifndef APP-VUE */
  width: 100%;
  /* #endif */
}

/* 非 bounded 模式：外层使用 sticky 定位 */
.z-sticky--normal {
  position: -webkit-sticky;
  position: sticky;
}

/* bounded 模式：外层使用 relative 定位 */
.z-sticky--bounded {
  position: relative;
}

.z-sticky__inner {
  width: 100%;
}

/* 非 bounded 模式且已吸顶：内层使用 fixed 定位覆盖外层的 sticky */
.z-sticky__inner--fixed {
  position: fixed;
  left: 0;
  right: 0;
  width: 100%;
}

/* bounded 模式：内层使用 sticky 定位 */
.z-sticky__inner--bounded {
  position: -webkit-sticky;
  position: sticky;
}

/* 占位元素，防止 fixed 定位时布局塌陷 */
.z-sticky__placeholder {
  width: 100%;
}
</style>
