<template>
	<view 
		v-if="visible"
		ref="notifyRef"
		class="z-notify"
		:class="[
			`z-notify--${type}`,
			{ 'z-notify--show': isShow },
			{ 'z-notify--with-icon': showIcon }
		]"
		:style="notifyStyle"
		@click="handleClick"
	>
		<!-- 图标 -->
		<view v-if="showIcon" class="z-notify__icon">
			<slot name="icon">
				<z-icon :name="iconName" :color="iconColor" :size="40" />
			</slot>
		</view>
		
		<!-- 自定义前置内容 -->
		<slot name="prefix"></slot>
		
		<!-- 文本内容 -->
		<text 
			v-if="text" 
			class="z-notify__text"
			:style="textStyle"
		>{{ text }}</text>
		
		<!-- 默认插槽 -->
		<slot></slot>
		
		<!-- 自定义后置内容 -->
		<slot name="suffix"></slot>
		
		<!-- 关闭按钮 -->
		<view v-if="closable" class="z-notify__close" @click.stop="close">
			<z-icon name="mdi:close" :color="closeColor" :size="36" />
		</view>
	</view>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
	// 通知类型：primary / success / warning / danger / info / dark
	type: {
		type: String,
		default: 'dark'
	},
	// 自定义背景色
	background: {
		type: String,
		default: ''
	},
	// 文字颜色
	color: {
		type: String,
		default: ''
	},
	// 文字大小
	size: {
		type: [Number, String],
		default: 28
	},
	// 文字对齐：left / center / right
	align: {
		type: String,
		default: 'center'
	},
	// 顶部距离 (px)
	top: {
		type: [Number, String],
		default: 0
	},
	// 左侧距离 (rpx)
	left: {
		type: [Number, String],
		default: 0
	},
	// 右侧距离 (rpx)
	right: {
		type: [Number, String],
		default: 0
	},
	// 内边距
	padding: {
		type: Array,
		default: () => ['24rpx', '32rpx']
	},
	// 圆角
	radius: {
		type: [Number, String],
		default: 0
	},
	// 是否显示图标
	showIcon: {
		type: Boolean,
		default: false
	},
	// 自定义图标名称
	icon: {
		type: String,
		default: ''
	},
	// 是否可关闭
	closable: {
		type: Boolean,
		default: false
	},
	// 层级
	zIndex: {
		type: Number,
		default: 1001
	}
})

const emit = defineEmits(['click', 'close', 'open', 'closed'])

// 响应式状态
const visible = ref(false)
const isShow = ref(false)
const text = ref('')
const timer = ref(null)

// 动态配置（通过 show 方法传入）
const dynamicType = ref('')
const dynamicBackground = ref('')
const dynamicColor = ref('')

// 类型配置
const typeConfig = {
	primary: {
		background: '#6366f1',
		color: '#ffffff',
		icon: 'mdi:information'
	},
	success: {
		background: '#22c55e',
		color: '#ffffff',
		icon: 'mdi:check-circle'
	},
	warning: {
		background: '#f59e0b',
		color: '#ffffff',
		icon: 'mdi:alert'
	},
	danger: {
		background: '#ef4444',
		color: '#ffffff',
		icon: 'mdi:close-circle'
	},
	info: {
		background: '#06b6d4',
		color: '#ffffff',
		icon: 'mdi:information-outline'
	},
	dark: {
		background: 'rgba(0, 0, 0, 0.75)',
		color: '#ffffff',
		icon: 'mdi:bell'
	}
}

// 当前使用的类型
const currentType = computed(() => dynamicType.value || props.type)

// 当前类型配置
const currentConfig = computed(() => typeConfig[currentType.value] || typeConfig.dark)

// 背景色
const bgColor = computed(() => {
	return dynamicBackground.value || props.background || currentConfig.value.background
})

// 文字颜色
const textColor = computed(() => {
	return dynamicColor.value || props.color || currentConfig.value.color
})

// 图标名称
const iconName = computed(() => {
	return props.icon || currentConfig.value.icon
})

// 图标颜色
const iconColor = computed(() => textColor.value)

// 关闭按钮颜色
const closeColor = computed(() => {
	const color = textColor.value
	return color === '#ffffff' ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.5)'
})

// 计算内边距
const computedPadding = computed(() => {
	const p = props.padding
	return {
		top: p[0] || '24rpx',
		right: p[1] || '32rpx',
		bottom: p[2] || p[0] || '24rpx',
		left: p[3] || p[1] || '32rpx'
	}
})

// 通知栏样式
const notifyStyle = computed(() => ({
	top: `${props.top}px`,
	left: `${props.left}rpx`,
	right: `${props.right}rpx`,
	paddingTop: computedPadding.value.top,
	paddingRight: computedPadding.value.right,
	paddingBottom: computedPadding.value.bottom,
	paddingLeft: computedPadding.value.left,
	background: bgColor.value,
	borderRadius: `${props.radius}rpx`,
	zIndex: props.zIndex
}))

// 文字样式
const textStyle = computed(() => ({
	color: textColor.value,
	fontSize: `${props.size}rpx`,
	textAlign: props.align
}))

// 清除定时器
const clearTimer = () => {
	if (timer.value) {
		clearTimeout(timer.value)
		timer.value = null
	}
}

/**
 * 显示通知
 * @param {Object} options 配置选项
 * @param {string} options.text 通知文本
 * @param {number} options.duration 显示时长，默认2000ms，0表示不自动关闭
 * @param {string} options.type 通知类型
 * @param {string} options.background 自定义背景色
 * @param {string} options.color 自定义文字颜色
 */
const show = (options = {}) => {
	clearTimer()
	
	// 设置选项
	text.value = options.text || ''
	dynamicType.value = options.type || ''
	dynamicBackground.value = options.background || ''
	dynamicColor.value = options.color || ''
	
	const duration = options.duration ?? 2000
	
	// 显示通知
	visible.value = true
	
	nextTick(() => {
		setTimeout(() => {
			isShow.value = true
			emit('open')
		}, 50)
		
		// 自动关闭
		if (duration > 0) {
			timer.value = setTimeout(() => {
				close()
			}, duration)
		}
	})
}

// 关闭通知
const close = () => {
	clearTimer()
	isShow.value = false
	
	setTimeout(() => {
		visible.value = false
		dynamicType.value = ''
		dynamicBackground.value = ''
		dynamicColor.value = ''
		emit('closed')
	}, 300)
	
	emit('close')
}

// 点击事件
const handleClick = () => {
	emit('click')
}

// 组件卸载时清除定时器
onBeforeUnmount(() => {
	clearTimer()
})

// 暴露方法
defineExpose({
	show,
	close
})
</script>

<style scoped>
.z-notify {
	position: fixed;
	left: 0;
	right: 0;
	box-sizing: border-box;
	display: flex;
	flex-direction: row;
	align-items: center;
	justify-content: center;
	opacity: 0;
	transform: translate3d(0, -100%, 0);
	transition: all 0.3s ease-out;
	backdrop-filter: blur(10px);
	-webkit-backdrop-filter: blur(10px);
}

.z-notify--show {
	opacity: 1;
	transform: translate3d(0, 0, 0);
}

.z-notify--with-icon {
	justify-content: flex-start;
}

/* 类型样式 */
.z-notify--primary {
	box-shadow: 0 4rpx 20rpx rgba(99, 102, 241, 0.3);
}

.z-notify--success {
	box-shadow: 0 4rpx 20rpx rgba(34, 197, 94, 0.3);
}

.z-notify--warning {
	box-shadow: 0 4rpx 20rpx rgba(245, 158, 11, 0.3);
}

.z-notify--danger {
	box-shadow: 0 4rpx 20rpx rgba(239, 68, 68, 0.3);
}

.z-notify--info {
	box-shadow: 0 4rpx 20rpx rgba(6, 182, 212, 0.3);
}

.z-notify--dark {
	box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.2);
}

/* 图标 */
.z-notify__icon {
	margin-right: 16rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
}

/* 文本 */
.z-notify__text {
	flex: 1;
	word-break: break-all;
	line-height: 1.5;
}

/* 关闭按钮 */
.z-notify__close {
	margin-left: 16rpx;
	padding: 8rpx;
	display: flex;
	align-items: center;
	justify-content: center;
	flex-shrink: 0;
	opacity: 0.8;
	transition: opacity 0.2s;
}

.z-notify__close:active {
	opacity: 1;
}
</style>
