<template>
  <view class="z-vtabs" :style="{ width: wrapW, height: wrapH }">
    <!-- 左侧 Tabs -->
    <view class="z-vtabs__bar" :style="{ width: tabWidthRpx, background: tabBg }">
      <scroll-view
        class="z-vtabs__bar-scroll"
        :show-scrollbar="false"
        scroll-y
        :scroll-into-view="tabScrollInto"
        :scroll-with-animation="isTap"
      >
        <view class="z-vtabs__bar-inner" :style="{ width: tabWidthRpx }">
          <view
            v-for="(t, i) in tabsNorm"
            :key="i"
            class="z-vtabs__tab"
            :id="`z_vtabs_bar_${uid}_${i}`"
            :class="{
              'is-active': current === i,
              'is-disabled': !!t[disabledKey],
              'has-border': border,
              [`style-${tabStyle}`]: true,
              'icon-top': iconPosition === 'top'
            }"
            :style="tabItemStyle(i)"
            @tap="onTabTap(i)"
          >
            <!-- icon：使用 z-icon 渲染 -->
            <view v-if="t[props.iconKey] || t[props.activeIconKey]" class="z-vtabs__tab-icon">
              <z-icon
                :name="current === i && t[props.activeIconKey] ? t[props.activeIconKey] : t[props.iconKey]"
                :size="props.iconSize"
                :color="current === i ? activeColorResolved : props.color"
              />
            </view>

            <view class="z-vtabs__tab-text" :style="tabTextStyle(i)">
              <text class="z-vtabs__tab-label">{{ t[props.labelKey] }}</text>

              <view
                v-if="t[props.badgeKey]"
                class="z-vtabs__badge"
                :class="{ 'is-dot': dotBadge || t[props.badgeKey] === true }"
                :style="{ background: badgeBgResolved, color: badgeColor }"
              >
                <text v-if="!(dotBadge || t[props.badgeKey] === true)" class="z-vtabs__badge-txt">
                  {{ t[props.badgeKey] }}
                </text>
              </view>
            </view>
          </view>
        </view>
      </scroll-view>
    </view>

    <!-- 右侧内容 -->
    <scroll-view
      class="z-vtabs__content-scroll"
      :show-scrollbar="false"
      :scroll-y="true"
      :style="{ height: wrapH }"
      :scroll-top="contentScrollTop"
      :scroll-with-animation="animation"
      @scroll="onContentScroll"
      @scrolltolower="onScrolltolower"
    >
      <view class="z-vtabs__content">
        <!-- 联动模式：渲染所有分组，并根据滚动位置同步高亮 -->
        <template v-if="linkage">
          <view
            v-for="(t, i) in panelsNorm"
            :key="i"
            class="z-vtabs__panel"
            :id="`z_vtabs_panel_${uid}_${i}`"
            ref="panelRefs"
          >
            <slot name="panel" :tab="t" :index="i" :active="current === i">
              <view class="z-vtabs__panel-card">
                <view class="z-vtabs__panel-head">
                  <text class="z-vtabs__panel-title">{{ t.title || t[labelKey] }}</text>
                  <text v-if="t.sub" class="z-vtabs__panel-sub">{{ t.sub }}</text>
                </view>
                <image v-if="t.image" class="z-vtabs__panel-img" :src="t.image" mode="widthFix" />
                <text v-if="t.desc" class="z-vtabs__panel-desc">{{ t.desc }}</text>

                <view v-if="t.tags && t.tags.length" class="z-vtabs__tags">
                  <view v-for="(tag, k) in t.tags" :key="k" class="z-vtabs__tag">
                    <text class="z-vtabs__tag-txt">{{ tag }}</text>
                  </view>
                </view>
              </view>
            </slot>
          </view>
          <!-- 底部空白区域，让最后一个panel可以滚动到顶部 -->
          <view class="z-vtabs__bottom-spacer"></view>
        </template>

        <!-- 不联动：只展示当前索引的内容 -->
        <template v-else>
          <view class="z-vtabs__panel is-single">
            <slot name="single" :tab="panelsNorm[current]" :index="current" :active="true">
              <view class="z-vtabs__panel-card">
                <view class="z-vtabs__panel-head">
                  <text class="z-vtabs__panel-title">{{ panelsNorm[current]?.title || panelsNorm[current]?.[labelKey] }}</text>
                  <text v-if="panelsNorm[current]?.sub" class="z-vtabs__panel-sub">{{ panelsNorm[current]?.sub }}</text>
                </view>
                <image v-if="panelsNorm[current]?.image" class="z-vtabs__panel-img" :src="panelsNorm[current]?.image" mode="widthFix" />
                <text v-if="panelsNorm[current]?.desc" class="z-vtabs__panel-desc">{{ panelsNorm[current]?.desc }}</text>
              </view>
            </slot>
          </view>
        </template>
      </view>
    </scroll-view>
  </view>
</template>

<script setup>
import { computed, getCurrentInstance, nextTick, onMounted, ref, watch } from 'vue'

// #ifdef APP-NVUE
const dom = weex.requireModule('dom')
// #endif

const props = defineProps({
  /** tabs 数据：字符串数组或对象数组 */
  tabs: { type: Array, default: () => [] },
  /** 右侧内容数据：不传则默认使用 tabs */
  panels: { type: Array, default: () => [] },

  /** v-model:active 当前高亮索引 */
  active: { type: [Number, String], default: 0 },

  /** 字段 key（对象 tab 时使用） */
  labelKey: { type: String, default: 'label' },
  badgeKey: { type: String, default: 'badge' },
  iconKey: { type: String, default: 'icon' },
  activeIconKey: { type: String, default: 'activeIcon' },
  disabledKey: { type: String, default: 'disabled' },

  /** 容器尺寸：0 表示全屏 */
  width: { type: [Number, String], default: 0 },
  height: { type: [Number, String], default: 0 },

  /** Tab 区域宽/高（rpx） */
  tabWidth: { type: [Number, String], default: 220 },
  tabHeight: { type: [Number, String], default: 110 },

  /** 字体 */
  fontSize: { type: [Number, String], default: 26 },
  activeFontSize: { type: [Number, String], default: 26 },
  fontWeight: { type: [Number, String], default: 'normal' },
  activeFontWeight: { type: [Number, String], default: 600 },

  /** 颜色 */
  color: { type: String, default: '#222222' },
  activeColor: { type: String, default: '' },
  tabBg: { type: String, default: '#F3F4F6' },
  tabActiveBg: { type: String, default: '#FFFFFF' },

  /** tab style: default | rounded | pill | card | minimal */
  tabStyle: { type: String, default: 'default' },

  /** icon position: left | top */
  iconPosition: { type: String, default: 'left' },

  /** 左侧高亮边框 */
  border: { type: Boolean, default: true },
  borderColor: { type: String, default: '' },
  borderWidth: { type: [Number, String], default: 8 },

  /** 右侧滚动联动 */
  linkage: { type: Boolean, default: true },
  /** 内容滚动动画 */
  animation: { type: Boolean, default: true },

  /** badge */
  badgeColor: { type: String, default: '#fff' },
  badgeBg: { type: String, default: '' },
  dotBadge: { type: Boolean, default: false },

  /** icon */
  iconSize: { type: [Number, String], default: 34 },
  /** 使用的 z-icon 标签名（你项目里是 z-icon） */
  zIconTag: { type: String, default: 'z-icon' }
})

const emit = defineEmits(['update:active', 'tab-click', 'change', 'scrolltolower'])

const inst = getCurrentInstance()
const proxy = inst?.proxy

const uid = `${Math.random().toString(36).slice(2, 8)}${Date.now().toString(36).slice(-4)}`
const current = ref(0)

const wrapW = ref('320px')
const wrapH = ref('600px')

const tabScrollInto = ref('')
const contentScrollTop = ref(0)
const isTap = ref(false)

const heightRecords = ref([]) // cumulative heights
const panelHeights = ref([])

const panelRefs = ref([])

// 添加节流变量
let scrollTimer = null
let lastScrollTime = 0

// normalize
function normalize(list, labelKey) {
  if (!Array.isArray(list)) return []
  if (!list.length) return []
  if (typeof list[0] !== 'object') {
    return list.map((s) => ({ [labelKey]: String(s) }))
  }
  return list.map((x) => ({ ...x }))
}

const tabsNorm = computed(() => normalize(props.tabs, props.labelKey))
const panelsNorm = computed(() => {
  const src = props.panels && props.panels.length ? props.panels : props.tabs
  return normalize(src, props.labelKey)
})

const tabWidthRpx = computed(() => `${Number(props.tabWidth) || 220}rpx`)

const activeColorResolved = computed(() => {
  if (props.activeColor && props.activeColor !== 'true') return props.activeColor
  return 'var(--z-color-primary, #465CFF)'
})
const borderColorResolved = computed(() => {
  if (props.borderColor && props.borderColor !== 'true') return props.borderColor
  return 'var(--z-color-primary, #465CFF)'
})
const badgeBgResolved = computed(() => {
  if (props.badgeBg && props.badgeBg !== 'true') return props.badgeBg
  return 'var(--z-color-danger, #FF2B2B)'
})

function setWrapSize() {
  const res = uni.getSystemInfoSync()
  const w = props.width
  const h = props.height
  wrapW.value = (w === 0 || w === '0' || w === '0px' || w === '0rpx') ? '100%' : String(w)
  wrapH.value = (h === 0 || h === '0' || h === '0px' || h === '0rpx') ? `${res.windowHeight}px` : String(h)
}

function scrollTabBar(i) {
  const len = tabsNorm.value.length
  if (!len) return
  const target = i < 6 ? 0 : i - 5
  tabScrollInto.value = `z_vtabs_bar_${uid}_${Math.min(target, len - 1)}`
}

function setActive(i, fromOuter = false) {
  i = Number(i) || 0
  i = Math.max(0, Math.min(i, tabsNorm.value.length - 1))
  current.value = i
  scrollTabBar(i)
  if (fromOuter) return
  emit('update:active', i)
}

function onTabTap(i) {
  const t = tabsNorm.value[i]
  if (!t || t[props.disabledKey]) return

  if (props.linkage) {
    // 设置isTap标志，防止滚动时触发onContentScroll
    isTap.value = true

    // 更新当前激活的tab
    setActive(i)

    // 计算滚动位置：每个panel应该滚动到容器顶部
    // 第一个panel滚动到0，其他panel滚动到前面所有panel的累计高度
    const targetScrollTop = i === 0 ? 0 : (heightRecords.value[i - 1] || 0)

    // 设置滚动位置
    contentScrollTop.value = targetScrollTop

    emit('tab-click', { index: i, ...t })

    // 等待滚动动画完成后再允许手动滚动检测
    // 使用较长的延迟确保滚动完成
    setTimeout(() => {
      isTap.value = false
      lastScrollTime = 0 // 重置节流时间，确保下次滚动能立即响应
    }, 1000)
  } else {
    setActive(i)
    emit('tab-click', { index: i, ...t })
  }
}

function calcRecords() {
  const len = panelsNorm.value.length
  const rec = []
  let acc = 0
  for (let i = 0; i < len; i++) {
    acc += (panelHeights.value[i] || 0)
    rec[i] = acc
  }
  heightRecords.value = rec
}

async function measurePanels() {
  if (!props.linkage) return
  await nextTick()

  // #ifdef APP-NVUE
  const refs = panelRefs.value || []
  const heights = []
  let done = 0
  if (!refs.length) return
  refs.forEach((el, idx) => {
    dom.getComponentRect(el, (opt) => {
      const h = opt?.size?.height || 0
      heights[idx] = h // 不要加1
      done++
      if (done === refs.length) {
        panelHeights.value = heights
        calcRecords()
      }
    })
  })
  // #endif

  // #ifndef APP-NVUE
  return new Promise((resolve) => {
    const q = uni.createSelectorQuery()
    // #ifndef MP-ALIPAY
    if (proxy) q.in(proxy)
    // #endif
    q.selectAll('.z-vtabs__panel')
      .fields({ size: true }, (list) => {
        // 不要加1，直接使用实际高度
        const heights = (list || []).map((x) => x?.height || 0)
        panelHeights.value = heights
        calcRecords()
        resolve()
      })
      .exec()
  })
  // #endif
}

function onContentScroll(e) {
  if (!props.linkage) return
  if (isTap.value) return
  const rec = heightRecords.value
  if (!rec.length) return

  // 节流：限制更新频率
  const now = Date.now()
  if (now - lastScrollTime < 50) {
    return
  }
  lastScrollTime = now

  const scrollTop = e?.detail?.scrollTop || 0
  let idx = 0

  // 改进的滚动检测逻辑：使用中点判断
  // 当滚动位置超过某个panel的中点时，就切换到下一个panel
  for (let i = 0; i < rec.length; i++) {
    const start = i === 0 ? 0 : rec[i - 1]
    const end = rec[i]
    const middle = (start + end) / 2

    // 如果滚动位置小于这个panel的中点，说明还在这个panel
    if (scrollTop < middle) {
      idx = i
      break
    }

    // 如果已经是最后一个panel了
    if (i === rec.length - 1) {
      idx = i
    }
  }

  // 只更新左侧高亮，不触发任何其他行为
  if (idx !== current.value) {
    current.value = idx
    scrollTabBar(idx)
    // 不emit change和update:active，避免触发外部逻辑
  }
}

function onScrolltolower(e) {
  if (!props.linkage) emit('scrolltolower', e)
}

function tabItemStyle(i) {
  const active = current.value === i
  const style = {
    width: tabWidthRpx.value,
    height: `${Number(props.tabHeight) || 110}rpx`,
    background: active ? props.tabActiveBg : props.tabBg,
    borderLeftColor: active && props.border ? borderColorResolved.value : 'transparent',
    borderLeftWidth: `${Number(props.borderWidth) || 8}rpx`
  }

  // Add style-specific adjustments
  if (props.tabStyle === 'rounded' && active) {
    style.borderRadius = '16rpx'
    style.margin = '8rpx'
    style.width = `calc(${tabWidthRpx.value} - 16rpx)`
  } else if (props.tabStyle === 'pill' && active) {
    style.borderRadius = '999rpx'
    style.margin = '8rpx 12rpx'
    style.width = `calc(${tabWidthRpx.value} - 24rpx)`
  } else if (props.tabStyle === 'card') {
    style.borderRadius = '12rpx'
    style.margin = '6rpx 8rpx'
    style.width = `calc(${tabWidthRpx.value} - 16rpx)`
    if (active) {
      style.boxShadow = '0 4rpx 12rpx rgba(70, 92, 255, 0.15)'
    }
  }

  return style
}

function tabTextStyle(i) {
  const active = current.value === i
  return {
    fontSize: `${Number(active ? props.activeFontSize : props.fontSize) || 26}rpx`,
    color: active ? activeColorResolved.value : props.color,
    fontWeight: active ? props.activeFontWeight : props.fontWeight
  }
}

function useZIcon(t) {
  // 获取icon值
  const iconValue = t.icon || t.activeIcon || t[props.iconKey] || t[props.activeIconKey]
  // 检查是否是iconify格式（包含:）
  return typeof iconValue === 'string' && iconValue.includes(':')
}

defineExpose({
  /** 内容异步变化后可手动调用刷新高度，避免联动错乱 */
  reset: () => measurePanels()
})

onMounted(async () => {
  setWrapSize()
  setActive(props.active, true)

  await nextTick()
  // 让页面布局稳定后再测量
  setTimeout(() => {
    measurePanels()
  }, 120)
})

watch(
  () => [props.width, props.height],
  () => setWrapSize()
)

watch(
  () => props.tabs,
  async () => {
    setActive(props.active, true)
    setTimeout(() => measurePanels(), 120)
  },
  { deep: true }
)

watch(
  () => props.panels,
  async () => {
    setTimeout(() => measurePanels(), 120)
  },
  { deep: true }
)

watch(
  () => props.active,
  (v) => {
    // 外部改 active：联动时等高度计算完再跳
    if (props.linkage) {
      setActive(v, true)
      isTap.value = true
      const targetScrollTop = v === 0 ? 0 : (heightRecords.value[Number(v) - 1] || 0)
      contentScrollTop.value = targetScrollTop
      setTimeout(() => {
        isTap.value = false
        lastScrollTime = 0 // 重置节流时间
      }, 1000)
    } else {
      setActive(v, true)
    }
  }
)
</script>

<style scoped>
.z-vtabs {
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  /* #endif */
  flex-direction: row;
  background: #fff;
  overflow: hidden;
}

.z-vtabs__bar {
  flex-shrink: 0;
  border-right: 1rpx solid rgba(0, 0, 0, 0.06);
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  /* #endif */
}

.z-vtabs__bar-scroll {
  width: 100%;
  height: 100%;
}

.z-vtabs__bar-inner {
  /* #ifndef APP-NVUE */
  display: flex;
  flex-direction: column;
  /* #endif */
}

.z-vtabs__tab {
  padding: 0 20rpx;
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  /* #endif */
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  text-align: center;
  position: relative;
}

.z-vtabs__tab.icon-top {
  flex-direction: column;
  padding: 16rpx 12rpx;
  justify-content: center;
}

.z-vtabs__tab.icon-top .z-vtabs__tab-icon {
  margin-right: 0;
  margin-bottom: 8rpx;
}

.z-vtabs__tab.has-border {
  border-left-width: 8rpx;
  border-left-style: solid;
}

.z-vtabs__tab.style-rounded {
  /* #ifndef APP-NVUE */
  transition: all 0.3s ease;
  /* #endif */
}

.z-vtabs__tab.style-pill {
  /* #ifndef APP-NVUE */
  transition: all 0.3s ease;
  /* #endif */
}

.z-vtabs__tab.style-card {
  /* #ifndef APP-NVUE */
  transition: all 0.3s ease;
  /* #endif */
}

.z-vtabs__tab.style-minimal {
  background: transparent !important;
  border-left: none !important;
}

.z-vtabs__tab.style-minimal.is-active {
  /* #ifndef APP-NVUE */
  transform: translateX(4rpx);
  /* #endif */
}

.z-vtabs__tab:active {
  /* #ifndef APP-NVUE */
  opacity: 0.8;
  /* #endif */
}

.z-vtabs__tab.is-disabled {
  opacity: 0.5;
}

.z-vtabs__tab-icon {
  margin-right: 12rpx;
  width: 44rpx;
  height: 44rpx;
  flex-shrink: 0;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  align-items: center;
  justify-content: center;
}

.z-vtabs__tab-text {
  position: relative;
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex: 1;
  align-items: center;
  justify-content: flex-start;
  text-align: left;
}

.z-vtabs__tab.icon-top .z-vtabs__tab-text {
  justify-content: center;
  text-align: center;
}

.z-vtabs__tab-label {
  line-height: 1.2;
  width: 100%;
}

.z-vtabs__badge {
  position: absolute;
  right: -32rpx;
  top: -18rpx;
  min-width: 36rpx;
  height: 36rpx;
  padding: 0 12rpx;
  border-radius: 100px;
  transform: scale(0.9);
  /* #ifndef APP-NVUE */
  display: flex;
  box-sizing: border-box;
  /* #endif */
  align-items: center;
  justify-content: center;
}

.z-vtabs__badge.is-dot {
  width: 16rpx;
  min-width: 16rpx;
  height: 16rpx;
  padding: 0;
  border-radius: 100px;
  right: -10rpx;
  top: -6rpx;
}

.z-vtabs__badge-txt {
  font-size: 22rpx;
  line-height: 1;
}

.z-vtabs__content-scroll {
  flex: 1;
  background: #fff;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  min-width: 0;
  /* #endif */
}

.z-vtabs__content {
  width: 100%;
  /* #ifndef APP-NVUE */
  box-sizing: border-box;
  overflow: hidden;
  /* #endif */
}

.z-vtabs__bottom-spacer {
  height: 600rpx;
  width: 100%;
}

.z-vtabs__panel {
  width: 100%;
  box-sizing: border-box;
  /* #ifndef APP-NVUE */
  overflow: hidden;
  word-wrap: break-word;
  word-break: break-word;
  /* #endif */
}


.z-vtabs__panel.is-single {
  padding-bottom: 24rpx;
}

.z-vtabs__panel-card {
  width: 100%;
  background: #ffffff;
  border-radius: 18rpx;
  padding: 22rpx 22rpx 24rpx;
  box-sizing: border-box;
  border: 1rpx solid rgba(0, 0, 0, 0.06);
  /* #ifndef APP-NVUE */
  box-shadow: 0 8rpx 22rpx rgba(0, 0, 0, 0.06);
  /* #endif */
}

.z-vtabs__panel-head {
  /* #ifndef APP-NVUE */
  display: flex;
  /* #endif */
  flex-direction: row;
  align-items: baseline;
  justify-content: space-between;
}

.z-vtabs__panel-title {
  font-size: 32rpx;
  font-weight: 700;
  color: #111827;
}

.z-vtabs__panel-sub {
  font-size: 24rpx;
  color: #6B7280;
  margin-left: 16rpx;
}

.z-vtabs__panel-img {
  width: 100%;
  border-radius: 14rpx;
  margin-top: 18rpx;
}

.z-vtabs__panel-desc {
  display: block;
  font-size: 26rpx;
  color: #374151;
  margin-top: 18rpx;
  line-height: 1.65;
}

.z-vtabs__tags {
  margin-top: 16rpx;
  /* #ifndef APP-NVUE */
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  /* #endif */
}

.z-vtabs__tag {
  padding: 8rpx 12rpx;
  border-radius: 999px;
  background: rgba(70, 92, 255, 0.10);
  border: 1rpx solid rgba(70, 92, 255, 0.20);
}

.z-vtabs__tag-txt {
  font-size: 22rpx;
  color: var(--z-color-primary, #465CFF);
}
</style>
