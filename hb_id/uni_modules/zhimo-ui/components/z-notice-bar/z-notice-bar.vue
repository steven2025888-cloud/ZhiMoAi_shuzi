<template>
  <view
    v-if="isShow"
    class="z-notice-bar"
    :class="[
      `z-notice-bar--${type}`,
      `z-notice-bar--${effect}`,
      { 'z-notice-bar--round': round },
      { 'z-notice-bar--wrapable': wrapable },
      { 'z-notice-bar--border': border }
    ]"
    :style="rootStyle"
    @click="onClick"
  >
    <!-- Left icon -->
    <view
      v-if="showLeftIcon"
      class="z-notice-bar__left"
      :style="{ marginRight: gapRpx }"
    >
      <slot name="icon">
        <z-icon
          :name="icon || defaultIconName"
          :size="iconSize"
          :color="computedIconColor"
        />
      </slot>
    </view>

    <!-- Content -->
    <view class="z-notice-bar__content">
      <!-- Column mode -->
      <swiper
        v-if="direction === 'column' && listData.length"
        class="z-notice-bar__swiper"
        :style="{ height: heightRpx }"
        vertical
        circular
        autoplay
        :interval="interval"
        :duration="duration"
        :disable-touch="disableTouch"
      >
        <swiper-item
          v-for="(item, index) in listData"
          :key="index"
          class="z-notice-bar__swiper-item"
        >
          <text class="z-notice-bar__text is-ellipsis" :style="{ color: computedTextColor }">
            {{ item }}
          </text>
        </swiper-item>
      </swiper>

      <!-- Wrapable (multi-line) -->
      <view v-else-if="wrapable" class="z-notice-bar__wrap">
        <text class="z-notice-bar__text" :style="wrapTextStyle">
          {{ displayText }}
        </text>
      </view>

      <!-- Marquee (single-line) -->
      <view v-else class="z-notice-bar__marquee-wrap" :id="wrapperId">
        <view
          class="z-notice-bar__scroller"
          :class="{ 'is-animation': enableAnimation }"
          :style="animationStyle"
        >
          <text
            class="z-notice-bar__text is-nowrap"
            :style="{ color: computedTextColor }"
            :id="textId"
          >
            {{ displayText }}
          </text>
        </view>
      </view>
    </view>

    <!-- Right icon -->
    <view
      v-if="mode || rightIcon || $slots.right"
      class="z-notice-bar__right"
      :style="{ marginLeft: gapRpx }"
    >
      <slot name="right">
        <z-icon
          v-if="mode === 'closeable'"
          :name="rightIcon || 'fontisto:close'"
          :size="iconSize"
          :color="computedIconColor"
          @click="onClose"
        />
        <z-icon
          v-else-if="mode === 'link'"
          :name="rightIcon || 'mdi:link'"
          :size="iconSize"
          :color="computedIconColor"
        />
        <z-icon
          v-else-if="rightIcon"
          :name="rightIcon"
          :size="iconSize"
          :color="computedIconColor"
        />
      </slot>
    </view>
  </view>
</template>

<script setup>
import { computed, ref, onMounted, getCurrentInstance, watch, nextTick } from 'vue'

const props = defineProps({
  // --- Data ---
  text: { type: String, default: '' },
  list: { type: Array, default: () => [] },

  // --- Behavior / Mode ---
  direction: { type: String, default: 'row' }, // row | column
  mode: { type: String, default: '' }, // '' | closeable | link
  scrollable: { type: Boolean, default: true },
  wrapable: { type: Boolean, default: false },
  lines: { type: [Number, String], default: 0 },

  // --- Theme ---
  type: { type: String, default: 'warning' },
  effect: { type: String, default: 'light' },

  // --- Style overrides (high priority) ---
  bgColor: { type: String, default: '' },
  color: { type: String, default: '' },
  fontSize: { type: [Number, String], default: 28 },
  round: { type: Boolean, default: false },
  border: { type: Boolean, default: false },
  borderColor: { type: String, default: '' },
  height: { type: [Number, String], default: 72 },
  gap: { type: [Number, String], default: 16 },
  padding: { type: String, default: '18rpx 24rpx' },

  // --- Icons ---
  icon: { type: String, default: '' },
  rightIcon: { type: String, default: '' },
  iconSize: { type: [Number, String], default: 34 },
  iconColor: { type: String, default: '' },

  // --- Marquee / Swiper ---
  speed: { type: Number, default: 60 }, // px/s
  interval: { type: Number, default: 3000 },
  duration: { type: Number, default: 500 },
  disableTouch: { type: Boolean, default: true }
})

const emit = defineEmits(['click', 'close'])

const instance = getCurrentInstance()
const proxy = instance?.proxy
const uid = instance?.uid ?? Math.floor(Math.random() * 1e9)

const wrapperId = `z-notice-wrapper-${uid}`
const textId = `z-notice-text-${uid}`

const isShow = ref(true)

const suppressClick = ref(false)
const enableAnimation = ref(false)
const animationDuration = ref(0)
const paddingLeft = ref(0)

const themeConfig = {
  warning: { lightBg: '#fffbe8', lightColor: '#ed6a0c', darkBg: '#ed6a0c', darkColor: '#ffffff', icon: 'notification' },
  primary: { lightBg: '#ecf9ff', lightColor: '#2979ff', darkBg: '#2979ff', darkColor: '#ffffff', icon: 'info' },
  success: { lightBg: '#e8ffea', lightColor: '#19be6b', darkBg: '#19be6b', darkColor: '#ffffff', icon: 'checkbox-circle' },
  error: { lightBg: '#fef0f0', lightColor: '#fa3534', darkBg: '#fa3534', darkColor: '#ffffff', icon: 'close-circle' },
  info: { lightBg: '#f4f4f5', lightColor: '#909399', darkBg: '#909399', darkColor: '#ffffff', icon: 'info' }
}

const currentTheme = computed(() => themeConfig[props.type] || themeConfig.warning)

const listData = computed(() => (Array.isArray(props.list) ? props.list.filter(Boolean) : []))
const displayText = computed(() => (props.text || listData.value[0] || ''))

const defaultIconName = computed(() => currentTheme.value.icon)
const showLeftIcon = computed(() => props.icon !== 'none' && (props.icon || defaultIconName.value))

const computedTextColor = computed(() => {
  if (props.color) return props.color
  if (props.effect === 'dark') return currentTheme.value.darkColor
  if (props.effect === 'plain') return currentTheme.value.lightColor
  return currentTheme.value.lightColor
})

const computedIconColor = computed(() => props.iconColor || computedTextColor.value)

const heightRpx = computed(() => `${Number(props.height) || 72}rpx`)
const gapRpx = computed(() => `${Number(props.gap) || 0}rpx`)

const rootStyle = computed(() => {
  const style = {
    padding: props.padding,
    fontSize: `${Number(props.fontSize) || 28}rpx`
  }

  // Background supports gradient
  if (props.bgColor) {
    if (String(props.bgColor).includes('gradient')) {
      style.backgroundImage = props.bgColor
      style.backgroundColor = 'transparent'
    } else {
      style.backgroundColor = props.bgColor
    }
  } else {
    if (props.effect === 'dark') style.backgroundColor = currentTheme.value.darkBg
    else if (props.effect === 'plain') style.backgroundColor = 'transparent'
    else style.backgroundColor = currentTheme.value.lightBg
  }

  // Border
  if (props.effect === 'plain' || props.border) {
    style.borderWidth = '1px'
    style.borderStyle = 'solid'
    if (props.borderColor) style.borderColor = props.borderColor
    else style.borderColor = props.effect === 'plain' ? currentTheme.value.lightColor : 'rgba(0,0,0,0.06)'
  }

  // Height only in single-line marquee mode
  if (!props.wrapable && props.direction !== 'column') {
    style.height = heightRpx.value
  }

  return style
})

const wrapTextStyle = computed(() => {
  const maxLines = Number(props.lines) || 0
  if (maxLines <= 0) return { color: computedTextColor.value, display: 'block' }
  return {
    color: computedTextColor.value,
    display: '-webkit-box',
    '-webkit-line-clamp': String(maxLines),
    '-webkit-box-orient': 'vertical',
    overflow: 'hidden'
  }
})

const animationStyle = computed(() => {
  if (!enableAnimation.value) return {}
  return {
    animationDuration: `${animationDuration.value}s`,
    paddingLeft: `${paddingLeft.value}px`
  }
})

function getRect(selector) {
  return new Promise((resolve) => {
    const query = uni.createSelectorQuery().in(proxy)
    query.select(selector).boundingClientRect((res) => resolve(res)).exec()
  })
}

async function initScroll() {
  // Not marquee cases
  if (props.direction === 'column' || props.wrapable || !props.scrollable) {
    enableAnimation.value = false
    return
  }

  enableAnimation.value = false

  await nextTick()

  // Small delay helps on some App runtimes
  setTimeout(async () => {
    const wrapRes = await getRect(`#${wrapperId}`)
    const textRes = await getRect(`#${textId}`)
    if (!wrapRes || !textRes) return

    const wrapWidth = Number(wrapRes.width) || 0
    const textWidth = Number(textRes.width) || 0

    if (wrapWidth > 0 && textWidth > wrapWidth) {
      enableAnimation.value = true
      paddingLeft.value = wrapWidth
      animationDuration.value = (wrapWidth + textWidth) / Math.max(10, props.speed)
    } else {
      enableAnimation.value = false
    }
  }, 80)
}

function onClick() {
  if (suppressClick.value) return
  emit('click', displayText.value)
}

function onClose() {
  suppressClick.value = true
  // uni-app-x / some runtimes don't provide stopPropagation; avoid .stop modifier
  setTimeout(() => {
    suppressClick.value = false
  }, 0)
  isShow.value = false
  emit('close')
}

onMounted(() => {
  initScroll()
})

watch(
  () => [props.text, props.list, props.scrollable, props.wrapable, props.direction, props.speed],
  () => initScroll(),
  { deep: true }
)
</script>

<style lang="scss" scoped>
.z-notice-bar {
  display: flex;
  align-items: center;
  line-height: 1.5;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;

  &--round {
    border-radius: 100rpx;
  }

  &--wrapable {
    align-items: flex-start;
    height: auto !important;

    .z-notice-bar__left,
    .z-notice-bar__right {
      margin-top: 6rpx;
    }
  }

  &__left {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  &__right {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  &__content {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
  }

  &__wrap {
    width: 100%;
    display: flex;
  }

  &__marquee-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    overflow: hidden;
    position: relative;
    height: 40rpx;
  }

  &__scroller {
    display: flex;
    align-items: center;
    white-space: nowrap;
    position: relative;
    height: 100%;

    &.is-animation {
      animation: z-notice-loop linear infinite;
      will-change: transform;
    }
  }

  &__text {
    font-size: inherit;

    &.is-nowrap {
      white-space: nowrap;
    }

    &.is-ellipsis {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      width: 100%;
    }

    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  &__swiper {
    width: 100%;
    flex: 1;
    height: 100%;
  }

  &__swiper-item {
    display: flex;
    align-items: center;
    width: 100%;
    height: 100%;
  }
}

@keyframes z-notice-loop {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-100%);
  }
}
</style>
