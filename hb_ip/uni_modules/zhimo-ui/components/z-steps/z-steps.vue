<template>
  <view
    class="z-steps"
    :class="{ 'z-steps--row': direction === 'row' }"
    :style="wrapStyle"
  >
    <view
      class="z-steps__item"
      v-for="(item, index) in items"
      :key="index"
      :class="[
        direction === 'column' ? 'z-steps__item--col' : 'z-steps__item--row',
        direction === 'row' ? 'z-steps__item--stretch' : ''
      ]"
      @tap.stop="onItemTap(index)"
    >
      <!-- node + lines -->
      <view
        class="z-steps__rail"
        :class="[
          direction === 'row' ? 'z-steps__rail--row' : 'z-steps__rail--col',
          direction === 'row' ? '' : 'z-steps__rail--nvue'
        ]"
        :style="railStyle"
      >
        <!-- left/top line (row only in original) -->
        <view
          v-if="direction === 'row'"
          class="z-steps__line"
          :class="[
            'z-steps__line--' + direction + (lineBold ? '--bold' : ''),
            leftLineFilled(index) ? 'z-steps__line--filled' : ''
          ]"
          :style="{ background: index === 0 ? 'transparent' : (index <= cur ? leftLineColor(index) : nodeColor) }"
        />

        <!-- node -->
        <view
          class="z-steps__node"
          :class="{ 'z-steps__node--size': direction !== 'row' || (direction === 'row' && !lineThrough) }"
          :style="nodeWrapStyle"
        >
          <!-- number/text node -->
          <text
            v-if="showTextNode(item) && !(showStatusMark && index === cur)"
            class="z-steps__node-text"
            :class="{
              'z-steps__node-text--filled': index <= cur && !activeColorResolved,
              'z-steps__node-text--border': index <= cur && !activeColorResolved
            }"
            :style="textNodeStyle(index)"
          >
            {{ item[textKey] }}
          </text>

          <!-- status mark (on current) -->
          <view
            v-if="showStatusMark && index === cur"
            class="z-steps__status"
            :class="{ 'z-steps__status--filled': !activeColorResolved && !statusColorResolved }"
            :style="{ background: statusColorResolved || activeColorResolved }"
          >
            <template v-if="status === 'fail'">
              <view class="z-steps__fail-a" />
              <view class="z-steps__fail-b" />
            </template>
            <view v-else-if="status === 'wait'" class="z-steps__wait" />
            <view v-else class="z-steps__check" />
          </view>

          <!-- dot node -->
          <view
            v-if="showDotNode(item) && !(showStatusMark && index === cur)"
            class="z-steps__dot"
            :class="{ 'z-steps__dot--filled': index <= cur && !activeColorResolved }"
            :style="{ background: index <= cur ? activeColorResolved : nodeColor }"
          />

          <!-- icon node -->
          <image
            v-if="showIconNode(item) && !(showStatusMark && index === cur)"
            class="z-steps__icon"
            :src="iconSrc(item, index)"
            mode="widthFix"
            :style="{ borderRadius: radius }"
          />
        </view>

        <!-- right/bottom line -->
        <view
          class="z-steps__line"
          :class="[
            'z-steps__line--' + direction + (lineBold ? '--bold' : ''),
            rightLineFilled(index) ? 'z-steps__line--filled' : ''
          ]"
          :style="{ background: index === items.length - 1 ? 'transparent' : rightLineColor(index) }"
        />
      </view>

      <!-- content -->
      <view
        class="z-steps__content"
        :class="[direction === 'row' ? 'z-steps__content--row' : 'z-steps__content--col']"
        :style="contentStyle(index, item)"
      >
        <text
          v-if="item[titleKey]"
          class="z-steps__title"
          :class="[
            direction === 'row' ? 'z-steps__text--center' : '',
            titleHighlight(index) ? 'z-steps__text--active' : ''
          ]"
          :style="{ color: index <= cur ? titleColor(index) : textColor, fontSize: titleSize + 'rpx', fontWeight: titleWeight }"
        >
          {{ item[titleKey] }}
        </text>

        <text
          v-if="item[descKey]"
          class="z-steps__desc"
          :class="[
            direction === 'row' ? 'z-steps__text--center' : '',
            titleHighlight(index) ? 'z-steps__text--active' : ''
          ]"
          :style="{ color: index <= cur ? titleColor(index) : descColorResolved, fontSize: descSize + 'rpx' }"
        >
          {{ item[descKey] }}
        </text>

        <!-- extra slot per item -->
        <slot name="item" :item="item" :index="index" :active="index === cur" :done="index < cur" />
      </view>
    </view>
  </view>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
const props = defineProps({
  items: { type: Array , default: () => [] },

  /** field keys */
  titleKey: { type: String, default: 'title' },
  descKey: { type: String, default: 'desc' },
  textKey: { type: String, default: 'text' },
  iconKey: { type: String, default: 'icon' },
  activeIconKey: { type: String, default: 'activeIcon' },

  /** v-model:current */
  current: { type: [Number, String], default: 0 },

  /** row / column */
  direction: { type: String, default: 'row' },

  /** layout */
  padding: { type: Array , default: () => [] },
  background: { type: String, default: 'transparent' },
  height: { type: [Number, String], default: 50 }, // rpx, rail size

  /** colors & text */
  nodeColor: { type: String, default: '#cccccc' },
  textColor: { type: String, default: '#181818' },
  titleSize: { type: [Number, String], default: 30 },
  titleWeight: { type: [Number, String], default: 500 },
  descColor: { type: String, default: '#8C8C8C' },
  descSize: { type: [Number, String], default: 24 },

  /** active */
  activeColor: { type: String, default: '' },

  /** current status: wait / fail / success */
  status: { type: String, default: '' },
  statusColor: { type: String, default: '' },
  showStatus: { type: Boolean, default: true },
  isWait: { type: Boolean, default: false }, // keep compatibility with old demo

  /** line */
  lineBold: { type: Boolean, default: false },
  itemGap: { type: [Number, String], default: 64 }, // column gap (rpx)
  lineThrough: { type: Boolean, default: false }, // dot node only, row only

  /** icon */
  radius: { type: String, default: '0rpx' },

  /** interaction */
  clickable: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['click','change','update:current'])

// #ifdef APP-NVUE
const isNvue = true
// #endif
// #ifndef APP-NVUE
const isNvue = false
// #endif

const clamp = (n, min, max) => Math.max(min, Math.min(max, n))

const cur = computed(() => clamp(Number(props.current) || 0, 0, Math.max(0, props.items.length - 1)))

const toRpx = (v) => {
  if (v === null || v === undefined || v === '') return ''
  if (typeof v === 'number') return `${v}rpx`
  const s = String(v)
  if (/\d$/.test(s)) return `${s}rpx`
  return s
}

const activeColorResolved = computed(() => {
  let c = props.activeColor
  // #ifdef APP-NVUE
  if (!c || (c ) === true) {
    c = 'var(--z-color-primary, #465CFF)'
  }
  // #endif
  return c || 'var(--z-color-primary, #465CFF)'
})

const statusColorResolved = computed(() => props.statusColor || '')

const descColorResolved = computed(() => props.descColor || '#8C8C8C')

const wrapStyle = computed(() => {
  const p = props.padding || []
  const pt = toRpx(p[0]) || '0rpx'
  const pr = toRpx(p[1]) || '0rpx'
  const pb = toRpx(p[2]) || pt
  const pl = toRpx(p[3]) || pr
  return {
    paddingTop: pt,
    paddingRight: pr,
    paddingBottom: pb,
    paddingLeft: pl,
    background: props.background
  } 
})

const railStyle = computed(() => {
  const h = Number(props.height) || 50
  return props.direction === 'column' ? { width: `${h}rpx` } : { height: `${h}rpx` }
})

const nodeWrapStyle = computed(() => {
  // allow dot icon align in lineThrough mode
  return {}
})

const showStatusMark = computed(() => props.showStatus && !props.disabled && (props.status || props.isWait))

const showTextNode = (item) => !!item[props.textKey]

const showIconNode = (item) => !item[props.textKey] && !!item[props.iconKey]

const showDotNode = (item) => !item[props.textKey] && !item[props.iconKey]

const iconSrc = (item, index) => {
  const base = item[props.iconKey]
  const active = item[props.activeIconKey] || base
  return index <= cur.value ? active : base
}

const textNodeStyle = (index) => {
  const isActive = index <= cur.value
  const bg = isActive ? activeColorResolved.value : '#fff'
  const bd = isActive ? activeColorResolved.value : props.nodeColor
  const c = isActive ? '#fff' : props.textColor
  return { background: bg, borderColor: bd, color: c } 
}

/** line color rule: allow statusColor for current / last finished */
const lineColor = (index, rightSide) => {
  // rightSide means line after index
  let c = activeColorResolved.value
  const isCurrentEdge = rightSide ? index === cur.value : index === cur.value
  const isPrevToCurrent = !rightSide ? index === cur.value : index === cur.value
  // keep original intent: current or (current-1 right line when success) use statusColor
  if (props.statusColor && (isCurrentEdge || isPrevToCurrent)) c = props.statusColor
  return c
}

const leftLineColor = (index) => {
  // line before node index (row only)
  if (index === cur.value) return props.statusColor || activeColorResolved.value
  return activeColorResolved.value
}

const rightLineColor = (index) => {
  // for column & row
  if (index >= props.items.length - 1) return 'transparent'
  // filled rules:
  const waiting = props.status === 'wait' || props.isWait
  if (index < cur.value) return activeColorResolved.value
  if (index === cur.value && waiting && props.direction === 'row') return props.statusColor || activeColorResolved.value
  return props.nodeColor
}

const leftLineFilled = (index) => {
  if (props.direction !== 'row') return false
  if (index === 0) return false
  return index <= cur.value && !activeColorResolved.value.includes('var(') ? false : false
}

const rightLineFilled = (_index) => false

const titleColor = (index) => {
  // current uses statusColor if provided
  if (index === cur.value) return props.statusColor || activeColorResolved.value
  return activeColorResolved.value
}

const titleHighlight = (index) => {
  // completed or current should highlight if activeColor not explicitly provided? keep as active
  return index <= cur.value
}

const contentStyle = (index, _item) => {
  const gap = Number(props.itemGap) || 64
  const isLast = index === props.items.length - 1
  return {
    paddingBottom: isLast || props.direction === 'row' ? '0rpx' : `${gap}rpx`,
    paddingLeft: props.direction === 'row' ? '20rpx' : (isNvue ? `${(Number(props.height) || 50) + 24}rpx` : '24rpx')
  } 
}

const onItemTap = (index) => {
  if (props.disabled) return
  const item = props.items[index] || {}
  emit('click', { index, ...item })
  if (props.clickable) {
    emit('update:current', index)
    emit('change', { current: index, item })
  }
}

// Expose refresh for async slot content (kept for compatibility with your style)
defineExpose({
  refresh() {
    // placeholder: steps is pure render; kept for future expansion
  }
})
</script>

<style scoped>
.z-steps{
  width: 100%;
  box-sizing: border-box;
  flex-direction: column;
}
.z-steps--row{
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  /* #ifdef APP-NVUE */
  align-items: flex-start !important;
  /* #endif */
}
.z-steps__item{
  position: relative;
  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  /* #endif */
}
.z-steps__item--stretch{ flex: 1; }
.z-steps__item--row{ flex-direction: column; }
.z-steps__item--col{ flex-direction: row; }

/* rail */
.z-steps__rail{
  /* #ifndef APP-NVUE */
  display: flex;
  flex-shrink: 0;
  /* #endif */
  align-items: center;
  overflow: hidden;
}
.z-steps__rail--row{ flex-direction: row; }
.z-steps__rail--col{ flex-direction: column; }
 /* #ifdef APP-NVUE */
.z-steps__rail--nvue{
  position: absolute;
  top: 0; bottom: 0; left: 0;
}
 /* #endif */

.z-steps__line{
  flex: 1;
  /* #ifndef APP-NVUE */
  transform-origin: center;
  /* #endif */
}
.z-steps__line--row{
  /* #ifdef APP-NVUE */
  height: 0.5px;
  /* #endif */
  /* #ifndef APP-NVUE */
  height: 1px;
  transform: scaleY(.5) translateZ(0);
  /* #endif */
}
.z-steps__line--row--bold{ height: 1px; transform: none; }
.z-steps__line--col{
  /* #ifdef APP-NVUE */
  width: 0.5px;
  /* #endif */
  /* #ifndef APP-NVUE */
  width: 1px;
  transform: scaleX(.5) translateZ(0);
  /* #endif */
}
.z-steps__line--col--bold{ width: 1px; transform: none; }

.z-steps__node{
  /* #ifndef APP-NVUE */
  display: flex;
  flex-shrink: 0;
  /* #endif */
  align-items: center;
  justify-content: center;
}
.z-steps__node--size{ width: 44rpx; height: 44rpx; }

.z-steps__node-text{
  width: 44rpx; height: 44rpx;
  background: #fff;
  border-style: solid;
  border-width: 1rpx;
  font-size: 28rpx;
  align-items: center;
  justify-content: center;
  text-align: center;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  border-radius: 50%;
  /* #endif */
  /* #ifdef APP-NVUE */
  border-radius: 24rpx;
  line-height: 44rpx;
  /* #endif */
}

.z-steps__icon{ width: 44rpx; height: 44rpx; /* #ifndef APP-NVUE */ display:block; flex-shrink:0; /* #endif */ }

.z-steps__dot{
  width: 18rpx; height: 18rpx;
  background: #ccc;
  /* #ifndef APP-NVUE */ border-radius: 50%; /* #endif */
  /* #ifdef APP-NVUE */ border-radius: 18rpx; /* #endif */
}

/* content */
.z-steps__content{
  /* #ifndef APP-NVUE */
  width: 100%;
  display: flex;
  box-sizing: border-box;
  /* #endif */
  flex: 1;
  flex-direction: column;
}
.z-steps__content--row{
  padding: 12rpx 20rpx 0;
  align-items: center;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  flex-shrink: 0;
  word-break: break-all;
  /* #endif */
}
.z-steps__content--col{
  padding-left: 24rpx;
  padding-bottom: 64rpx;
}

.z-steps__title, .z-steps__desc{
  padding-bottom: 8rpx;
  font-weight: normal;
  /* #ifndef APP-NVUE */
  display: block;
  word-break: break-all;
  /* #endif */
}
.z-steps__desc{ padding-bottom: 0; }

.z-steps__text--center{ text-align: center; }

.z-steps__text--active{
  color: var(--z-color-primary, #465CFF) !important;
}

/* status mark */
.z-steps__status{
  width: 44rpx;
  height: 44rpx;
  position: relative;
  overflow: hidden;
  /* #ifndef APP-NVUE */
  display: inline-flex;
  box-sizing: border-box;
  border-radius: 50%;
  vertical-align: top;
  flex-shrink: 0;
  /* #endif */
  /* #ifdef APP-NVUE */
  border-radius: 44rpx;
  /* #endif */
  align-items: center;
  justify-content: center;
}

.z-steps__check{
  width: 22rpx;
  height: 44rpx;
  border-bottom-style: solid;
  border-bottom-width: 3px;
  border-bottom-color: #FFFFFF;
  border-right-style: solid;
  border-right-width: 3px;
  border-right-color: #FFFFFF;
  transform: rotate(45deg) scale(0.5);
  transform-origin: 54% 48%;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  transform: rotate(45deg) scale(0.5) translateZ(0);
  /* #endif */
}

.z-steps__fail-a{
  width: 48rpx;
  height: 3px;
  transform: rotate(45deg) scale(0.5);
  background: #FFFFFF;
}
.z-steps__fail-b{
  width: 48rpx;
  height: 3px;
  margin-top: -3px;
  transform: rotate(-45deg) scale(0.5);
  background: #FFFFFF;
}
.z-steps__wait{
  height: 32rpx;
  width: 32rpx;
  border-style: solid;
  border-bottom-width: 3px;
  border-left-width: 3px;
  border-top-width: 0;
  border-right-width: 0;
  border-color: #fff;
  margin-left: 6rpx;
  margin-top: -6rpx;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
  transform: scale(.5);
}
</style>
