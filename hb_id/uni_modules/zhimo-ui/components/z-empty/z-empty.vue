<template>
  <view
    class="z-empty"
    :class="[
      fixed ? 'z-empty--fixed' : '',
      compact ? 'z-empty--compact' : '',
      center ? 'z-empty--center' : ''
    ]"
    :style="wrapStyle"
  >
    <!-- Illustration -->
    <view v-if="image" class="z-empty__media">
      <image
        class="z-empty__img"
        :src="image"
        :style="imgStyle"
        mode="widthFix"
      />
    </view>
    <view v-else class="z-empty__media">
      <slot name="icon">
        <view class="z-empty__illus" :style="illusStyle">
          <view class="z-empty__illus-dot" />
          <view class="z-empty__illus-card" />
          <view class="z-empty__illus-line z-empty__illus-line--1" />
          <view class="z-empty__illus-line z-empty__illus-line--2" />
        </view>
      </slot>
    </view>

    <!-- Text -->
    <text
      v-if="title"
      class="z-empty__title"
      :style="titleStyle"
      :class="titleClamp === 1 ? 'z-ell' : (titleClamp === 2 ? 'z-ell-2' : '')"
    >{{ title }}</text>

    <text
      v-if="desc"
      class="z-empty__desc"
      :style="descStyle"
      :class="descClamp === 1 ? 'z-ell' : (descClamp === 2 ? 'z-ell-2' : '')"
    >{{ desc }}</text>

    <!-- Actions / extra -->
    <view v-if="$slots.default" class="z-empty__slot">
      <slot />
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type Unit = string | number

const props = defineProps({
  /** image url */
  image: { type: String, default: '' },

  /** image size */
  imageWidth: { type: [Number, String] as any, default: 576 },
  imageHeight: { type: [Number, String] as any, default: 318 },

  /** placeholder illustration size (when no image) */
  illusSize: { type: [Number, String] as any, default: 220 },

  /** text */
  title: { type: String, default: '' },
  desc: { type: String, default: '' },

  /** typography */
  titleSize: { type: [Number, String] as any, default: 32 },
  descSize: { type: [Number, String] as any, default: 24 },
  titleColor: { type: String, default: '' },
  descColor: { type: String, default: '' },

  /** clamp lines: 0=off, 1=single line, 2=two lines */
  titleClamp: { type: Number, default: 0 },
  descClamp: { type: Number, default: 0 },

  /** layout */
  marginTop: { type: [Number, String] as any, default: 0 },
  padding: { type: [Number, String] as any, default: 0 },
  background: { type: String, default: 'transparent' },

  /** fixed center of screen */
  fixed: { type: Boolean, default: false },

  /** tighter spacing */
  compact: { type: Boolean, default: false },

  /** align center (default true) */
  center: { type: Boolean, default: true },
})

const toRpx = (v: Unit) => (v === '' || v == null ? '' : `${v}`.includes('rpx') || `${v}`.includes('px') ? `${v}` : `${v}rpx`)

const wrapStyle = computed(() => ({
  marginTop: toRpx(props.marginTop),
  padding: toRpx(props.padding),
  background: props.background,
}))

const imgStyle = computed(() => ({
  width: toRpx(props.imageWidth),
  height: toRpx(props.imageHeight),
}))

const illusStyle = computed(() => ({
  width: toRpx(props.illusSize),
  height: toRpx(props.illusSize),
}))

const titleStyle = computed(() => ({
  color: props.titleColor || 'var(--z-color-title, #222222)',
  fontSize: toRpx(props.titleSize),
}))

const descStyle = computed(() => ({
  color: props.descColor || 'var(--z-color-muted, #9CA3AF)',
  fontSize: toRpx(props.descSize),
}))
</script>

<style scoped>
.z-empty{
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
}
.z-empty--center{
  align-items: center;
  justify-content: center;
}
.z-empty__media{
  display:flex;
  align-items:center;
  justify-content:center;
  width: 100%;
}
.z-empty__img{
  display:block;
}
.z-empty__title{
  text-align:center;
  font-weight: 600;
  padding-top: 40rpx;
  line-height: 1.3;
}
.z-empty__desc{
  text-align:center;
  font-weight: 400;
  padding-top: 10rpx;
  line-height: 1.45;
}
.z-empty__slot{
  padding-top: 26rpx;
}

/* compact */
.z-empty--compact .z-empty__title{ padding-top: 26rpx; }
.z-empty--compact .z-empty__desc{ padding-top: 8rpx; }
.z-empty--compact .z-empty__slot{ padding-top: 18rpx; }

/* fixed */
.z-empty--fixed{
  position: fixed;
  left: 0;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 99;
  padding-left: 24rpx;
  padding-right: 24rpx;
}

/* placeholder illustration */
.z-empty__illus{
  position: relative;
  border-radius: 28rpx;
  overflow: hidden;
  background: linear-gradient(180deg, rgba(70,92,255,.10), rgba(70,92,255,.04));
  border: 1rpx solid rgba(70,92,255,.14);
}
.z-empty__illus-dot{
  position:absolute;
  width: 26%;
  height: 26%;
  left: 12%;
  top: 18%;
  border-radius: 999rpx;
  background: rgba(70,92,255,.18);
}
.z-empty__illus-card{
  position:absolute;
  width: 62%;
  height: 44%;
  right: 10%;
  bottom: 14%;
  border-radius: 20rpx;
  background: rgba(255,255,255,.8);
  border: 1rpx solid rgba(70,92,255,.14);
}
.z-empty__illus-line{
  position:absolute;
  height: 10%;
  left: 14%;
  right: 18%;
  border-radius: 999rpx;
  background: rgba(70,92,255,.12);
}
.z-empty__illus-line--1{ top: 56%; }
.z-empty__illus-line--2{ top: 72%; opacity: .75; }

/* ellipsis helpers (keep local to component for convenience) */
.z-ell{
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 92%;
}
.z-ell-2{
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  max-width: 92%;
}
</style>
