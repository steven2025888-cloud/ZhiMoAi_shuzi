<template>
<view class="z-panel__wrap"
		:style="{background:background,'border-top-color':borderColor,'border-bottom-color':borderColor,marginTop:marginTop+'rpx',marginBottom:marginBottom+'rpx'}"
		:class="{'z-panel__unlined':!isBorder,'z-panel__background':!background}">
		<view class="z-panel__hd"
			:style="{background:hdBackground,paddingLeft:padding+'rpx',paddingRight:padding+'rpx'}"
			v-if="panelData[head]">
			<text :class="{'z-panel__title-color':!headColor}"
				:style="{fontSize:headSize+'rpx',color:headColor}">{{panelData[head] || ''}}</text>
			<view v-if="hdBorder" :style="{background:borderColor,left:hdLeft+'rpx',right:hdRight+'rpx'}"
				class="z-panel__border" :class="{'z-panel__border-color':!borderColor}"></view>
		</view>
		<view class="z-panel__mediabox" :style="{paddingLeft:padding+'rpx',paddingRight:padding+'rpx'}"
			:class="{'z-mediabox__center':!flexStart,'z-panel__hover-weex':highlight,'z-panel__mediabox-row':!rowReverse,'z-panel__row-reverse':rowReverse}"
			v-for="(item,index) in listData" :key="index" :hover-class="highlight?'z-panel__hover':''"
			:hover-stay-time="150" @tap="handleClick(index)">
			<view class="z-panel__mb-hd" :class="[rowReverse?'z-panel__mb-hdright':'z-panel__mb-hdleft']"
				v-if="item[src]" :style="{width:width+'rpx',height:height+'rpx'}">
				<image class="z-panel__mb-thumb" :src="item[src]" mode="widthFix"
					:style="{width:width+'rpx',height:height+'rpx',borderRadius:radius+'rpx'}" />
			</view>
			<view class="z-panel__mb-bd">
				<text class="z-panel__mb-title" v-if="item[title]" :class="{'z-panel__title-color':!color}"
					:style="{color:color,fontSize:size+'rpx',fontWeight:fontWeight}">{{item[title] || ''}}</text>
				<text class="z-panel__mb-desc" v-if="item[desc]" :class="{'z-panel__sub-color':!descColor}"
					:style="{color:descColor,fontSize:descSize+'rpx'}">{{item[desc] || ''}}</text>
				<view class="z-panel__mb-info" v-if="item[source] || item[time] || item[extra]">
					<text class="z-panel__info-meta" :class="{'z-panel__info-color':!infoColor}"
						:style="{color:infoColor,fontSize:infoSize+'rpx'}"
						v-if="item[source]">{{item[source] || ''}}</text>
					<text class="z-panel__info-meta" :class="{'z-panel__info-color':!infoColor}"
						:style="{color:infoColor,fontSize:infoSize+'rpx'}" v-if="item[time]">{{item[time] || ''}}</text>
					<text class="z-panel__info-extra"
						:class="{'z-panel__info-color':!infoColor,'z-panel__extra-bcolor':!infoColor}"
						:style="{color:infoColor,fontSize:infoSize+'rpx','border-left-color':infoColor}"
						v-if="item[extra]">{{item[extra] || ''}}</text>
				</view>
			</view>
			<view v-if="bdBorder && index!==listData.length-1"
				:style="{background:borderColor,left:bdLeft+'rpx',right:bdRight+'rpx'}" class="z-panel__border"
				:class="{'z-panel__border-color':!borderColor}"></view>
		</view>

		<view v-if="showMore" class="z-panel__more"
			:style="{paddingLeft:padding+'rpx',paddingRight:padding+'rpx'}"
			:hover-class="highlight?'z-panel__hover':''" :hover-stay-time="150" @tap.stop="handleMore">
			<view class="z-panel__more-inner">
				<text class="z-panel__more-text"
					:class="{'z-panel__info-color':!moreColor}"
					:style="{color: (moreColor || infoColor), fontSize: moreSize + 'rpx'}">{{ moreText }}</text>
				<view v-if="moreIcon" class="z-panel__more-arrow" :style="{'border-right-color': (moreColor || infoColor), 'border-bottom-color': (moreColor || infoColor)}"></view>
			</view>
			<view class="z-panel__border z-panel__more-border"
				:style="{background:borderColor,left:bdLeft+'rpx',right:bdRight+'rpx'}"
				:class="{'z-panel__border-color':!borderColor}"></view>
		</view>

		<slot></slot>
	</view>
</template>

<script setup>
import { computed } from 'vue'

// 兼容原组件在 NVUE / 非 NVUE 下的默认值差异（保持外观一致）
// #ifdef APP-NVUE
const DEFAULT_BG = '#fff'
const DEFAULT_TEXT = '#181818'
const DEFAULT_DESC = '#7F7F7F'
const DEFAULT_INFO = '#b2b2b2'
const DEFAULT_BORDER = '#eee'
// #endif
// #ifndef APP-NVUE
const DEFAULT_BG = ''
const DEFAULT_TEXT = ''
const DEFAULT_DESC = ''
const DEFAULT_INFO = ''
const DEFAULT_BORDER = ''
// #endif

const props = defineProps({
  // 面板数据，键名可通过 fields 属性配置
  panelData: { type: Object, default: () => ({}) },

  // 面板数据源键名（key）
  fields: { type: Object, default: () => ({}) },

  // 背景色
  background: { type: String, default: DEFAULT_BG },

  // 是否有点击效果
  highlight: { type: Boolean, default: true },

  // 内容垂直对齐：true=顶部对齐；false=居中对齐
  flexStart: { type: Boolean, default: false },

  // 图文左右排列方向
  rowReverse: { type: Boolean, default: false },

  marginTop: { type: [Number, String], default: 0 },
  marginBottom: { type: [Number, String], default: 0 },

  // 左右间距
  padding: { type: [Number, String], default: 32 },

  // header 底部分割线
  hdBorder: { type: Boolean, default: true },
  hdLeft: { type: [Number, String], default: 32 },
  hdRight: { type: [Number, String], default: 0 },
  hdBackground: { type: String, default: '#fff' },

  headSize: { type: [Number, String], default: 32 },
  headColor: { type: String, default: DEFAULT_TEXT },

  // body 分割线
  bdBorder: { type: Boolean, default: true },
  bdLeft: { type: [Number, String], default: 32 },
  bdRight: { type: [Number, String], default: 0 },

  // 图片宽高
  width: { type: [Number, String], default: 100 },
  height: { type: [Number, String], default: 100 },
  radius: { type: [Number, String], default: 0 },

  // 标题
  size: { type: [Number, String], default: 28 },
  color: { type: String, default: DEFAULT_TEXT },
  fontWeight: { type: [Number, String], default: 'normal' },

  // 描述
  descSize: { type: [Number, String], default: 20 },
  descColor: { type: String, default: DEFAULT_DESC },

  // 信息
  infoSize: { type: [Number, String], default: 20 },
  infoColor: { type: String, default: DEFAULT_INFO },


  // 底部“查看更多”
  showMore: { type: Boolean, default: false },
  moreText: { type: String, default: '查看更多' },
  moreIcon: { type: Boolean, default: true },
  moreSize: { type: [Number, String], default: 26 },
  moreColor: { type: String, default: '' },

  // 边框色
  borderColor: { type: String, default: DEFAULT_BORDER },

  // 是否需要 panel 外层上下线条
  isBorder: { type: Boolean, default: true }
})

const emit = defineEmits(['click','more'])

const keyMap = computed(() => {
  const f = props.fields || {}
  return {
    head: f.head || 'head',
    list: f.list || 'list',
    src: f.src || 'src',
    title: f.title || 'title',
    desc: f.desc || 'desc',
    source: f.source || 'source',
    time: f.time || 'time',
    extra: f.extra || 'extra'
  }
})

const head = computed(() => keyMap.value.head)
const list = computed(() => keyMap.value.list)
const src = computed(() => keyMap.value.src)
const title = computed(() => keyMap.value.title)
const desc = computed(() => keyMap.value.desc)
const source = computed(() => keyMap.value.source)
const time = computed(() => keyMap.value.time)
const extra = computed(() => keyMap.value.extra)

const listData = computed(() => {
  const val = props.panelData || {}
  const k = list.value
  const arr = val && Array.isArray(val[k]) ? val[k].slice() : null
  return arr || [val]
})

function handleClick(index) {
  const item = listData.value[index] || {}
  emit('click', { index, ...item })
}

function handleMore() {
  emit('more')
}
</script>

<style scoped>
.z-panel__wrap {
		/* #ifndef APP-NVUE */
		width: 100%;
		border-top-width: 0;
		border-bottom-width: 0;
		/* #endif */
		flex: 1;
		position: relative;
		overflow: hidden;

		/* #ifdef APP-NVUE */
		border-top-width: 0.5px;
		border-top-style: solid;
		border-bottom-width: 0.5px;
		border-bottom-style: solid;
		/* #endif */
	}

	/* #ifndef APP-NVUE */
	.z-panel__background {
		background: var(--z-bg-color, #FFFFFF);
	}

	/* #endif */
	.z-panel__unlined {
		border-top-width: 0 !important;
		border-bottom-width: 0 !important;
	}

	/* #ifndef APP-NVUE */
	.z-panel__wrap::before {
		top: 0;
		border-top: 1px solid var(--z-color-border, #EEEEEE);
		-webkit-transform-origin: 0 0;
		transform-origin: 0 0;
		-webkit-transform: scaleY(.5);
		transform: scaleY(.5)
	}

	.z-panel__wrap:after {
		content: " ";
		position: absolute;
		left: 0;
		right: 0;
		height: 1px;
	}

	.z-panel__wrap::before {
		content: " ";
		position: absolute;
		left: 0;
		right: 0;
		height: 1px;
	}

	.z-panel__wrap::after {
		bottom: 0;
		border-bottom: 1px solid var(--z-color-border, #EEEEEE);
		-webkit-transform-origin: 0 100%;
		transform-origin: 0 100%;
		-webkit-transform: scaleY(.5);
		transform: scaleY(.5)
	}

	.z-panel__unlined::before {
		border-top-width: 0 !important;
		border-bottom-width: 0 !important;
	}

	.z-panel__unlined::after {
		border-top-width: 0 !important;
		border-bottom-width: 0 !important;
	}

	/* #endif */

	.z-panel__hd {
		/* #ifndef APP-NVUE */
		width: 100%;
		display: flex;
		word-break: break-all;
		box-sizing: border-box;
		/* #endif */
		flex: 1;
		padding-top: 26rpx;
		padding-bottom: 26rpx;
		font-weight: 700;
		position: relative;
		flex-direction: row;
		align-items: center;
	}

	.z-panel__border {
		position: absolute;
		bottom: 0;
		/* #ifdef APP-NVUE */
		height: 0.5px;
		z-index: -1;
		/* #endif */
		/* #ifndef APP-NVUE */
		height: 1px;
		-webkit-transform: scaleY(0.5);
		transform: scaleY(0.5);
		transform-origin: 0 100%;
		z-index: 1;
		/* #endif */
	}

	/* #ifndef APP-NVUE */
	.z-panel__border-color {
		background: var(--z-color-border, #EEEEEE) !important;
	}

	/* #endif */

	.z-panel__mediabox {
		padding-top: 32rpx;
		padding-bottom: 32rpx;
		position: relative;
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */

	}

	.z-panel__mediabox-row {
		flex-direction: row;
	}

	.z-panel__row-reverse {
		flex-direction: row-reverse;
	}

	.z-mediabox__center {
		align-items: center;
	}

	.z-panel__mb-hd {
		overflow: hidden;
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */
		align-items: center;
		justify-content: center;
	}

	.z-panel__mb-hdleft {
		margin-right: 32rpx;
	}

	.z-panel__mb-hdright {
		margin-left: 32rpx;
	}


	.z-panel__mb-thumb {
		/* #ifndef APP-NVUE */
		display: block;
		/* #endif */
	}

	.z-panel__mb-bd {
		flex: 1;
		overflow: hidden;
	}

	/* 暂不使用 */
	.z-panel__mb-between {
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */
		flex-direction: column;
		justify-content: space-between;
	}

	/* 暂不使用 */
	/* #ifndef APP-NVUE */
	.z-panel__bd-height {
		min-height: var(--z-img-base, 60px);
	}

	/* #endif */

	.z-panel__mb-title {
		font-weight: normal;
		/* #ifdef APP-NVUE */
		lines: 1;
		/* #endif */

		/* #ifndef APP-NVUE */
		white-space: nowrap;
		line-height: 1.2;
		display: block;
		/* #endif */
	}

	/* #ifndef APP-NVUE */
	.z-panel__title-color {
		color: var(--z-color-title, #181818) !important;
	}

	/* #endif */

	.z-panel__mb-desc,
	.z-panel__mb-title {
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.z-panel__mb-desc {
		padding-top: 12rpx;
		font-weight: 400;
		font-size: 28rpx;
		/* #ifndef APP-NVUE */
		line-height: 1.4;
		word-break: break-all;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 2;
		/* #endif */

		/* #ifdef APP-NVUE */
		lines: 2;
		/* #endif */
	}

	/* #ifndef APP-NVUE */
	.z-panel__sub-color {
		color: var(--z-color-subtitle, #7F7F7F) !important;
	}

	/* #endif */

	.z-panel__mb-info {
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */
		align-items: center;
		flex-direction: row;
		margin-top: 32rpx;
		padding-bottom: 8rpx;
		font-weight: 400;
		line-height: 1;
		overflow: hidden;
	}

	/* #ifndef APP-NVUE */
	.z-panel__info-color {
		color: var(--z-color-label, #B2B2B2) !important;
	}

	/* #endif */

	.z-panel__info-meta {
		padding-right: 32rpx;
	}

	.z-panel__info-extra {
		padding-left: 32rpx;
		border-left-width: 1rpx;
		border-left-style: solid;
	}

	/* #ifndef APP-NVUE */
	.z-panel__extra-bcolor {
		border-left-color: var(--z-color-label, #B2B2B2) !important;
	}

	/* #endif */
	/* #ifndef APP-NVUE */
	.z-panel__hover {
		background-color: var(--z-bg-color-hover, rgba(0, 0, 0, 0.2)) !important;
	}

	/* #endif */

	/* #ifdef APP-NVUE */
	.z-panel__hover-weex:active {
		background: rgba(0, 0, 0, 0.2) !important;
	}

	/* #endif */

	.z-panel__more{
		position: relative;
		padding-top: 22rpx;
		padding-bottom: 22rpx;
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */
		align-items: center;
		justify-content: center;
	}
	.z-panel__more-inner{
		/* #ifndef APP-NVUE */
		display: flex;
		/* #endif */
		flex-direction: row;
		align-items: center;
		justify-content: center;
	}
	.z-panel__more-text{
		font-weight: 500;
	}
	.z-panel__more-arrow{
		width: 14rpx;
		height: 14rpx;
		border-right-width: 2rpx;
		border-right-style: solid;
		border-bottom-width: 2rpx;
		border-bottom-style: solid;
		transform: rotate(-45deg);
		margin-left: 10rpx;
		opacity: .95;
	}
	.z-panel__more-border{
		bottom: auto;
		top: 0;
	}

</style>
