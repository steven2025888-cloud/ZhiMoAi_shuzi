<template>
	<view class="z-popover" ref="popoverRef">
		<!-- 触发器插槽 -->
		<view class="z-popover__trigger" @click="handleTriggerClick">
			<slot></slot>
		</view>
		
		<!-- 遮罩层 -->
		<view 
			v-if="mask && visible"
			class="z-popover__mask"
			:class="{ 'z-popover__mask--show': isShow }"
			:style="maskStyle"
			@click="handleMaskClick"
			@touchmove.stop.prevent
		/>
		
		<!-- 弹出内容 -->
		<view 
			v-if="visible"
			class="z-popover__content"
			:class="[
				`z-popover__content--${placement}`,
				{ 'z-popover__content--show': isShow }
			]"
			:style="contentStyle"
		>
			<!-- 箭头 - 上/左方向时在内容前 -->
			<view 
				v-if="showArrow && (placement === 'bottom' || placement === 'right')"
				class="z-popover__arrow-wrap"
				:style="arrowWrapStyle"
			>
				<view 
					class="z-popover__arrow"
					:class="[`z-popover__arrow--${placement}`]"
					:style="arrowStyle"
				/>
			</view>
			
			<!-- 内容区域 -->
			<view class="z-popover__body" :style="bodyStyle">
				<!-- 菜单列表模式 -->
				<template v-if="items && items.length > 0">
					<view 
						v-for="(item, index) in items" 
						:key="index"
						class="z-popover__item"
						:class="{ 'z-popover__item--disabled': item.disabled }"
						:style="itemStyle"
						@click.stop="handleItemClick(item, index)"
					>
						<!-- 图标 -->
						<z-icon 
							v-if="item.icon" 
							:name="item.icon" 
							:size="item.iconSize || iconSize" 
							:color="item.iconColor || iconColor || color"
						/>
						<!-- 图片 -->
						<image 
							v-else-if="item.image"
							class="z-popover__item-img"
							:src="item.image"
							:style="{ width: (item.imageSize || 40) + 'rpx', height: (item.imageSize || 40) + 'rpx' }"
							mode="aspectFill"
						/>
						<!-- 文本 -->
						<text 
							class="z-popover__item-text"
							:class="{ 'z-popover__item-text--has-icon': item.icon || item.image }"
							:style="textStyle"
						>{{ item.text }}</text>
						<!-- 徽标 -->
						<view v-if="item.badge" class="z-popover__badge">
							<text class="z-popover__badge-text">{{ item.badge }}</text>
						</view>
						<!-- 分割线 -->
						<view 
							v-if="showDivider && index !== items.length - 1"
							class="z-popover__divider"
							:style="dividerStyle"
						/>
					</view>
				</template>
				
				<!-- 自定义内容插槽 -->
				<slot name="content"></slot>
			</view>
			
			<!-- 箭头 - 下/右方向时在内容后 -->
			<view 
				v-if="showArrow && (placement === 'top' || placement === 'left')"
				class="z-popover__arrow-wrap"
				:style="arrowWrapStyle"
			>
				<view 
					class="z-popover__arrow"
					:class="[`z-popover__arrow--${placement}`]"
					:style="arrowStyle"
				/>
			</view>
		</view>
	</view>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps({
	// 是否显示
	show: {
		type: Boolean,
		default: false
	},
	// 菜单项列表
	items: {
		type: Array,
		default: () => []
	},
	// 弹出位置：top / bottom / left / right
	placement: {
		type: String,
		default: 'bottom'
	},
	// 定位方式：absolute / fixed
	position: {
		type: String,
		default: 'absolute'
	},
	// 宽度
	width: {
		type: [Number, String],
		default: 280
	},
	// 距离顶部 (rpx)
	top: {
		type: [Number, String],
		default: 0
	},
	// 距离底部 (rpx)
	bottom: {
		type: [Number, String],
		default: 0
	},
	// 距离左侧 (rpx)
	left: {
		type: [Number, String],
		default: 0
	},
	// 距离右侧 (rpx)
	right: {
		type: [Number, String],
		default: 0
	},
	// 内边距
	padding: {
		type: Array,
		default: () => ['24rpx', '28rpx']
	},
	// 背景色
	background: {
		type: String,
		default: '#ffffff'
	},
	// 文字颜色
	color: {
		type: String,
		default: '#1e293b'
	},
	// 文字大小
	fontSize: {
		type: [Number, String],
		default: 30
	},
	// 文字粗细
	fontWeight: {
		type: [Number, String],
		default: 400
	},
	// 图标大小
	iconSize: {
		type: [Number, String],
		default: 44
	},
	// 图标颜色
	iconColor: {
		type: String,
		default: ''
	},
	// 是否显示分割线
	showDivider: {
		type: Boolean,
		default: true
	},
	// 分割线颜色
	dividerColor: {
		type: String,
		default: '#f1f5f9'
	},
	// 是否显示箭头
	showArrow: {
		type: Boolean,
		default: true
	},
	// 箭头位置配置
	arrow: {
		type: Object,
		default: () => ({})
	},
	// 圆角
	radius: {
		type: [Number, String],
		default: 12
	},
	// 是否显示遮罩
	mask: {
		type: Boolean,
		default: true
	},
	// 遮罩背景色
	maskColor: {
		type: String,
		default: 'transparent'
	},
	// 点击遮罩是否关闭
	maskClosable: {
		type: Boolean,
		default: true
	},
	// 层级
	zIndex: {
		type: Number,
		default: 999
	},
	// 阴影
	shadow: {
		type: Boolean,
		default: true
	},
	// 主题：light / dark
	theme: {
		type: String,
		default: 'light'
	}
})

const emit = defineEmits(['update:show', 'click', 'close', 'open'])

// 响应式状态
const visible = ref(false)
const isShow = ref(false)

// 主题配置
const themeConfig = computed(() => {
	if (props.theme === 'dark') {
		return {
			background: '#1e293b',
			color: '#f8fafc',
			dividerColor: '#334155'
		}
	}
	return {
		background: props.background,
		color: props.color,
		dividerColor: props.dividerColor
	}
})

// 遮罩样式
const maskStyle = computed(() => ({
	background: props.maskColor,
	zIndex: props.zIndex - 1
}))

// 内容样式
const contentStyle = computed(() => {
	const style = {
		zIndex: props.zIndex
	}
	
	if (props.position === 'fixed') {
		style.position = 'fixed'
		if (Number(props.top)) style.top = `${props.top}rpx`
		if (Number(props.bottom)) style.bottom = `${props.bottom}rpx`
		if (Number(props.left)) style.left = `${props.left}rpx`
		if (Number(props.right)) style.right = `${props.right}rpx`
	}
	
	if (props.placement === 'top' || props.placement === 'bottom') {
		style.width = `${props.width}rpx`
	}
	
	return style
})

// 内容区域样式
const bodyStyle = computed(() => {
	const config = themeConfig.value
	return {
		background: config.background,
		borderRadius: `${props.radius}rpx`,
		boxShadow: props.shadow ? '0 8rpx 32rpx rgba(0, 0, 0, 0.12)' : 'none'
	}
})

// 菜单项样式
const itemStyle = computed(() => ({
	paddingTop: props.padding[0] || '24rpx',
	paddingRight: props.padding[1] || '28rpx',
	paddingBottom: props.padding[2] || props.padding[0] || '24rpx',
	paddingLeft: props.padding[3] || props.padding[1] || '28rpx'
}))

// 文字样式
const textStyle = computed(() => {
	const config = themeConfig.value
	return {
		color: config.color,
		fontSize: `${props.fontSize}rpx`,
		fontWeight: props.fontWeight
	}
})

// 分割线样式
const dividerStyle = computed(() => {
	const config = themeConfig.value
	return {
		background: config.dividerColor,
		left: props.padding[3] || props.padding[1] || '28rpx',
		right: props.padding[1] || '28rpx'
	}
})

// 箭头容器样式
const arrowWrapStyle = computed(() => {
	if (props.placement === 'left' || props.placement === 'right') {
		return { width: '16rpx' }
	}
	return { height: '16rpx' }
})

// 箭头样式
const arrowStyle = computed(() => {
	const config = themeConfig.value
	const style = {
		background: config.background
	}
	
	const arrowConfig = props.arrow || {}
	
	if (props.placement === 'top' || props.placement === 'bottom') {
		if (arrowConfig.left) {
			style.left = `${Math.max(24, arrowConfig.left)}rpx`
		} else if (arrowConfig.right) {
			style.right = `${Math.max(24, arrowConfig.right)}rpx`
		} else {
			style.left = '50%'
			style.marginLeft = '-10rpx'
		}
	} else {
		if (arrowConfig.top) {
			style.top = `${Math.max(24, arrowConfig.top)}rpx`
		} else if (arrowConfig.bottom) {
			style.bottom = `${Math.max(24, arrowConfig.bottom)}rpx`
		} else {
			style.top = '50%'
			style.marginTop = '-10rpx'
		}
	}
	
	return style
})

// 监听 show 属性
watch(() => props.show, (val) => {
	if (val) {
		open()
	} else {
		close()
	}
}, { immediate: true })

// 打开弹出框
const open = () => {
	visible.value = true
	nextTick(() => {
		setTimeout(() => {
			isShow.value = true
			emit('open')
		}, 50)
	})
}

// 关闭弹出框
const close = () => {
	isShow.value = false
	setTimeout(() => {
		visible.value = false
		emit('update:show', false)
		emit('close')
	}, 300)
}

// 触发器点击
const handleTriggerClick = () => {
	if (!props.show) {
		emit('update:show', true)
	}
}

// 遮罩点击
const handleMaskClick = () => {
	if (props.maskClosable) {
		close()
	}
}

// 菜单项点击
const handleItemClick = (item, index) => {
	if (item.disabled) return
	emit('click', { item, index })
	close()
}

// 暴露方法
defineExpose({
	open,
	close
})
</script>

<style scoped>
.z-popover {
	position: relative;
	display: inline-block;
}

.z-popover__trigger {
	display: inline-block;
}

/* 遮罩 */
.z-popover__mask {
	position: fixed;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	opacity: 0;
	visibility: hidden;
	transition: all 0.3s ease;
}

.z-popover__mask--show {
	opacity: 1;
	visibility: visible;
}

/* 内容区域 */
.z-popover__content {
	position: absolute;
	display: flex;
	opacity: 0;
	visibility: hidden;
	transform: scale(0.9);
	transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.z-popover__content--show {
	opacity: 1;
	visibility: visible;
	transform: scale(1);
}

/* 位置定位 */
.z-popover__content--top {
	flex-direction: column;
	left: 50%;
	bottom: 100%;
	transform: translateX(-50%) scale(0.9);
	transform-origin: center bottom;
	margin-bottom: 8rpx;
}

.z-popover__content--top.z-popover__content--show {
	transform: translateX(-50%) scale(1);
}

.z-popover__content--bottom {
	flex-direction: column;
	left: 50%;
	top: 100%;
	transform: translateX(-50%) scale(0.9);
	transform-origin: center top;
	margin-top: 8rpx;
}

.z-popover__content--bottom.z-popover__content--show {
	transform: translateX(-50%) scale(1);
}

.z-popover__content--left {
	flex-direction: row;
	right: 100%;
	top: 50%;
	transform: translateY(-50%) scale(0.9);
	transform-origin: right center;
	margin-right: 8rpx;
}

.z-popover__content--left.z-popover__content--show {
	transform: translateY(-50%) scale(1);
}

.z-popover__content--right {
	flex-direction: row;
	left: 100%;
	top: 50%;
	transform: translateY(-50%) scale(0.9);
	transform-origin: left center;
	margin-left: 8rpx;
}

.z-popover__content--right.z-popover__content--show {
	transform: translateY(-50%) scale(1);
}

/* 内容主体 */
.z-popover__body {
	overflow: hidden;
	position: relative;
}

/* 菜单项 */
.z-popover__item {
	display: flex;
	flex-direction: row;
	align-items: center;
	position: relative;
	transition: background 0.2s;
}

.z-popover__item:active {
	background: rgba(0, 0, 0, 0.05);
}

.z-popover__item--disabled {
	opacity: 0.5;
	pointer-events: none;
}

.z-popover__item-img {
	border-radius: 8rpx;
	flex-shrink: 0;
}

.z-popover__item-text {
	flex: 1;
	line-height: 1.4;
}

.z-popover__item-text--has-icon {
	margin-left: 16rpx;
}

/* 徽标 */
.z-popover__badge {
	min-width: 32rpx;
	height: 32rpx;
	padding: 0 8rpx;
	background: #ef4444;
	border-radius: 32rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	margin-left: 12rpx;
}

.z-popover__badge-text {
	font-size: 20rpx;
	color: #fff;
	line-height: 1;
}

/* 分割线 */
.z-popover__divider {
	position: absolute;
	bottom: 0;
	height: 1px;
	transform: scaleY(0.5);
}

/* 箭头 */
.z-popover__arrow-wrap {
	position: relative;
	overflow: hidden;
	flex-shrink: 0;
}

.z-popover__arrow {
	width: 20rpx;
	height: 20rpx;
	position: absolute;
}

.z-popover__arrow--top {
	bottom: 0;
	transform: rotate(45deg) translateY(14rpx);
}

.z-popover__arrow--bottom {
	top: 0;
	transform: rotate(45deg) translateY(-14rpx);
}

.z-popover__arrow--left {
	right: 0;
	transform: rotate(45deg) translateX(14rpx);
}

.z-popover__arrow--right {
	left: 0;
	transform: rotate(45deg) translateX(-14rpx);
}
</style>
