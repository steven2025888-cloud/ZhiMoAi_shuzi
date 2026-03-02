<template>
	<!-- #ifdef APP-VUE || MP-WEIXIN || H5 -->
	<view class="z-swipe__wrap" :style="wrapStyle">
		<view
			class="z-swipe__inner"
			:show="showState"
			:change:show="handler.showChange"
			:threshold="thresholdVal"
			:change:threshold="handler.thresholdChange"
			:clickclose="clickClose"
			:change:clickclose="handler.clickCloseChange"
			:disabled="isDisabled"
			:change:disabled="handler.disabledChange"
			@touchstart="handler.touchstart"
			@touchmove="handler.touchmove"
			@touchend="handler.touchend"
			@mousedown="handler.mousedown"
			@mousemove="handler.mousemove"
			@mouseup="handler.mouseup"
			@mouseleave="handler.mouseleave"
		>
			<!-- 左侧按钮 -->
			<view v-if="leftButtons && leftButtons.length" class="z-swipe__buttons z-swipe__buttons--left">
				<slot name="leftButtons">
					<view
						class="z-swipe__btn"
						v-for="(item, index) in leftButtons"
						:key="'l' + index"
						:style="getBtnStyle(item)"
						@touchstart="onBtnTouchStart"
						@touchend="onLeftBtnTouchEnd($event, index, item)"
						@tap.stop="onLeftBtnClick(index, item)"
					>
						<text class="z-swipe__btn-text" :style="getBtnTextStyle(item)">{{ item.text }}</text>
					</view>
				</slot>
			</view>

			<!-- 内容区 -->
			<view class="z-swipe__content">
				<slot></slot>
			</view>

			<!-- 右侧按钮 -->
			<view v-if="buttons && buttons.length" class="z-swipe__buttons z-swipe__buttons--right">
				<slot name="buttons">
					<view
						class="z-swipe__btn"
						v-for="(item, index) in buttons"
						:key="'r' + index"
						:style="getBtnStyle(item)"
						@touchstart="onBtnTouchStart"
						@touchend="onBtnTouchEnd($event, index, item)"
						@tap.stop="onBtnClick(index, item)"
					>
						<text class="z-swipe__btn-text" :style="getBtnTextStyle(item)">{{ item.text }}</text>
					</view>
				</slot>
			</view>
		</view>
	</view>
	<!-- #endif -->

	<!-- #ifdef APP-NVUE -->
	<view 
		class="z-swipe__wrap" 
		:style="wrapStyle"
		ref="wrapRef"
		@horizontalpan="onNvueTouchStart"
		@touchend="onNvueTouchEnd"
	>
		<view class="z-swipe__buttons" ref="buttonsRef">
			<slot name="buttons">
				<view 
					class="z-swipe__btn" 
					v-for="(item, index) in buttons" 
					:key="index"
					:style="getBtnStyle(item)"
					@tap.stop="onBtnClickNvue($event, index, item)"
				>
					<text class="z-swipe__btn-text" :style="getBtnTextStyle(item)">{{ item.text }}</text>
				</view>
			</slot>
		</view>
		<view class="z-swipe__content" ref="contentRef">
			<slot></slot>
		</view>
	</view>
	<!-- #endif -->

	<!-- #ifndef APP-PLUS || MP-WEIXIN || H5 -->
	<view class="z-swipe__wrap" :style="wrapStyle">
		<view 
			class="z-swipe__inner"
			:class="{ 'z-swipe__ani': isAnimating }"
			:style="{ transform: transformStyle }"
			@touchstart="onOtherTouchStart"
			@touchmove="onOtherTouchMove"
			@touchend="onOtherTouchEnd"
		>
			<view class="z-swipe__content">
				<slot></slot>
			</view>
			<view class="z-swipe__buttons" :class="elClass">
				<slot name="buttons">
					<view 
						class="z-swipe__btn" 
						v-for="(item, index) in buttons" 
						:key="index"
						:style="getBtnStyle(item)"
						@touchstart="onBtnTouchStart"
						@touchend="onBtnTouchEnd($event, index, item)"
					>
						<text class="z-swipe__btn-text" :style="getBtnTextStyle(item)">{{ item.text }}</text>
					</view>
				</slot>
			</view>
		</view>
	</view>
	<!-- #endif -->
</template>

<!-- #ifdef APP-VUE || MP-WEIXIN || H5 -->
<script src="./handler.wxs" module="handler" lang="wxs"></script>
<!-- #endif -->

<script setup>
/**
 * z-swipe-action 滑动菜单
 * @description 滑动操作菜单，左滑显示操作按钮
 * @property {Array} buttons 操作按钮配置
 * @property {Number} size 按钮文字大小，单位rpx
 * @property {String} color 按钮文字颜色
 * @property {Boolean} show 是否显示菜单
 * @property {Number} threshold 滑动阈值
 * @property {Boolean} disabled 是否禁用
 * @property {Boolean} autoClose 是否自动关闭其他菜单
 * @property {Boolean} clickClose 点击内容是否关闭菜单
 * @property {Number} marginTop 上边距
 * @property {Number} marginBottom 下边距
 * @property {String|Number} param 自定义参数
 * @event {Function} click 按钮点击事件
 * @event {Function} change 菜单状态改变事件
 */
import { ref, computed, watch, inject, onMounted, onBeforeUnmount, nextTick, getCurrentInstance } from 'vue'

// #ifdef APP-NVUE
const BindingX = uni.requireNativePlugin('bindingx')
const dom = uni.requireNativePlugin('dom')
const animation = uni.requireNativePlugin('animation')
// #endif

const props = defineProps({
	// 右侧操作按钮配置 [{text, background, color, size}]
	buttons: {
		type: Array,
		default: () => [{
			text: '删除',
			background: '#ff4d4f'
		}]
	},
	// 左侧操作按钮配置 [{text, background, color, size}]
	leftButtons: {
		type: Array,
		default: () => []
	},
	// 按钮文字大小
	size: {
		type: [Number, String],
		default: 32
	},
	// 按钮文字颜色
	color: {
		type: String,
		default: '#ffffff'
	},
	// 是否显示菜单
	show: {
		type: Boolean,
		default: false
	},
	// 滑动阈值
	threshold: {
		type: [Number, String],
		default: 30
	},
	// 是否禁用
	disabled: {
		type: Boolean,
		default: false
	},
	// 是否自动关闭其他菜单
	autoClose: {
		type: Boolean,
		default: true
	},
	// 点击内容是否关闭菜单
	clickClose: {
		type: Boolean,
		default: true
	},
	// 上边距
	marginTop: {
		type: [Number, String],
		default: 0
	},
	// 下边距
	marginBottom: {
		type: [Number, String],
		default: 0
	},
	// 自定义参数
	param: {
		type: [Number, String],
		default: 0
	}
})

const emit = defineEmits(['click', 'change'])

const instance = getCurrentInstance()

// 注入父组件方法
const swipeGroup = inject('swipeGroup', null)

// 响应式状态
const showState = ref('none')
const isDisabled = ref(false)
const thresholdVal = ref(30)
const isAnimating = ref(false)
const leftOffset = ref(0)
const elClass = ref(`z_swipe_${Math.ceil(Math.random() * 10e5).toString(36)}`)

// 触摸相关状态
const touchState = ref({
	startX: 0,
	startY: 0,
	deltaX: 0,
	deltaY: 0,
	direction: '',
	isOpen: false
})

// 按钮宽度
const btnWidth = ref(0)

// refs
const wrapRef = ref(null)
const contentRef = ref(null)
const buttonsRef = ref(null)

// 计算样式
const wrapStyle = computed(() => ({
	marginTop: `${props.marginTop}rpx`,
	marginBottom: `${props.marginBottom}rpx`
}))

const transformStyle = computed(() => `translateX(${leftOffset.value}px)`)

// 获取按钮样式
const getBtnStyle = (item) => ({
	background: item.background || '#ff4d4f'
})

const getBtnTextStyle = (item) => ({
	fontSize: `${item.size || props.size}rpx`,
	color: item.color || props.color
})

// 监听props变化
watch(() => props.show, (val) => {
	showState.value = val ? 'right' : 'none'
})

watch(() => props.disabled, (val) => {
	isDisabled.value = val
})

watch(() => props.threshold, (val) => {
	thresholdVal.value = Number(val)
})

// #ifdef APP-VUE || MP-WEIXIN || H5
// WXS处理的平台，通过callMethod触发
const onTouchStart = () => {
	if (props.autoClose && swipeGroup) {
		swipeGroup.closeOthers(instance)
	}
}

const onStateChange = (e) => {
	emit('change', {
		isOpen: e.isOpen,
		param: props.param
	})
	showState.value = e.isOpen ? 'right' : 'none'
}
// #endif

// 按钮点击相关
let btnTouchStartX = 0
let btnTouchStartTime = 0

const onBtnTouchStart = (e) => {
	const touch = e.changedTouches[0]
	btnTouchStartX = touch.clientX
	btnTouchStartTime = Date.now()
}

const onBtnTouchEnd = (e, index, item) => {
	const touch = e.changedTouches[0]
	const diff = Math.abs(btnTouchStartX - touch.clientX)
	const time = Date.now() - btnTouchStartTime

	if (diff < 40 && time < 300) {
		emit('click', {
			item,
			index,
			param: props.param,
			position: 'right'
		})
	}
}

const onBtnClick = (index, item) => {
	// #ifdef H5
	// PC端直接触发
	if (isPC()) {
		emit('click', {
			item,
			index,
			param: props.param,
			position: 'right'
		})
	}
	// #endif
}

// 左侧按钮点击
const onLeftBtnTouchEnd = (e, index, item) => {
	const touch = e.changedTouches[0]
	const diff = Math.abs(btnTouchStartX - touch.clientX)
	const time = Date.now() - btnTouchStartTime

	if (diff < 40 && time < 300) {
		emit('click', {
			item,
			index,
			param: props.param,
			position: 'left'
		})
	}
}

const onLeftBtnClick = (index, item) => {
	// #ifdef H5
	// PC端直接触发
	if (isPC()) {
		emit('click', {
			item,
			index,
			param: props.param,
			position: 'left'
		})
	}
	// #endif
}

// 判断是否PC
const isPC = () => {
	if (typeof navigator !== 'object') return false
	const ua = navigator.userAgent
	const agents = ['Android', 'iPhone', 'SymbianOS', 'Windows Phone', 'iPad', 'iPod']
	return !agents.some(agent => ua.includes(agent))
}

// #ifdef APP-NVUE
// NVUE平台的处理逻辑
let nvueState = {
	x: 0,
	stop: false,
	isOpen: false,
	btnWidth: 0,
	eventPan: null
}

const getElRef = (el) => el?.ref

const getNvueBtnWidth = () => {
	return new Promise((resolve) => {
		dom.getComponentRect(buttonsRef.value, (data) => {
			if (data?.size) {
				nvueState.btnWidth = data.size.width || 0
				resolve(data.size.width)
			} else {
				resolve(0)
			}
		})
	})
}

const nvueMove = (ref, value) => {
	return new Promise((resolve) => {
		animation.transition(ref, {
			styles: { transform: `translateX(${value}px)` },
			duration: 150,
			timingFunction: 'linear',
			needLayout: false,
			delay: 0
		}, resolve)
	})
}

const nvueOpen = async (open) => {
	const width = nvueState.btnWidth || 0
	
	if (nvueState.eventPan?.token) {
		BindingX.unbind({
			token: nvueState.eventPan.token,
			eventType: 'pan'
		})
	}
	
	const contentEl = getElRef(contentRef.value)
	const buttonsEl = getElRef(buttonsRef.value)
	
	if (open) {
		await Promise.all([
			nvueMove(contentEl, -width),
			nvueMove(buttonsEl, 0)
		])
	} else {
		await Promise.all([
			nvueMove(contentEl, 0),
			nvueMove(buttonsEl, width)
		])
	}
	
	const targetX = open ? -width : 0
	
	if (nvueState.isOpen !== open && nvueState.x !== targetX) {
		emit('change', {
			isOpen: open,
			param: props.param
		})
	}
	
	nvueState.x = targetX
	nvueState.isOpen = open
	nvueState.stop = false
}

const onNvueTouchStart = async (e) => {
	if (props.disabled || nvueState.stop) return
	nvueState.stop = true
	
	if (props.autoClose && swipeGroup) {
		swipeGroup.closeOthers(instance)
	}
	
	await getNvueBtnWidth()
	const width = nvueState.btnWidth || 0
	
	const expression = `min(max(x+${nvueState.x}, ${-width}), 0)`
	const rightExpression = `min(max(x+${nvueState.x}+${width}, 0), ${width})`
	
	const boxEl = getElRef(wrapRef.value)
	const contentEl = getElRef(contentRef.value)
	const buttonsEl = getElRef(buttonsRef.value)
	
	nvueState.eventPan = BindingX.bind({
		anchor: boxEl,
		eventType: 'pan',
		props: [
			{ element: contentEl, property: 'transform.translateX', expression },
			{ element: buttonsEl, property: 'transform.translateX', expression: rightExpression }
		]
	}, (bindingEvent) => {
		if (bindingEvent.state === 'end') {
			nvueState.x = bindingEvent.deltaX + nvueState.x
			
			const threshold = Number(props.threshold)
			if (!nvueState.isOpen) {
				nvueOpen(nvueState.x < -threshold)
			} else {
				const dx = bindingEvent.deltaX
				nvueOpen((dx < threshold && dx > 0) || dx < -threshold)
			}
		}
	})
}

const onNvueTouchEnd = () => {
	if (nvueState.isOpen && !nvueState.stop && props.clickClose) {
		nvueOpen(false)
	}
}

const onBtnClickNvue = (e, index, item) => {
	e.stopPropagation()
	emit('click', {
		item,
		index,
		param: props.param
	})
}

watch(() => props.show, (val) => {
	if (nvueState.stop) return
	nvueState.stop = true
	nvueOpen(val)
})

watch(() => props.buttons, () => {
	nextTick(() => {
		nvueState.x = 0
		setTimeout(getNvueBtnWidth, 200)
	})
})

onMounted(() => {
	nextTick(() => {
		setTimeout(() => {
			getNvueBtnWidth().then(() => {
				if (props.show) nvueOpen(true)
			})
		}, 200)
	})
})

onBeforeUnmount(() => {
	nvueState.x = 0
	nvueState.stop = true
})
// #endif

// #ifndef APP-PLUS || MP-WEIXIN || H5
// 其他平台的处理逻辑
const MIN_DISTANCE = 10
let otherState = {
	startX: 0,
	startY: 0,
	deltaX: 0,
	deltaY: 0,
	direction: '',
	x: 0,
	isOpen: false,
	rightWidth: 0
}

const getOtherBtnWidth = () => {
	uni.createSelectorQuery()
		.in(instance.proxy)
		.select('.' + elClass.value)
		.boundingClientRect(data => {
			// 如果找不到按钮元素，重置宽度为0
			otherState.rightWidth = (data && data.width) || 0
			if (props.show && otherState.rightWidth > 0) {
				openOtherState(true)
			}
		})
		.exec()
}

const getDirection = (x, y) => {
	if (x > y && x > MIN_DISTANCE) return 'horizontal'
	if (y > x && y > MIN_DISTANCE) return 'vertical'
	return ''
}

const resetOtherTouch = () => {
	otherState.direction = ''
	otherState.deltaX = 0
	otherState.deltaY = 0
}

const onOtherTouchStart = (e) => {
	if (props.disabled) return
	isAnimating.value = false
	otherState.x = leftOffset.value || 0
	
	resetOtherTouch()
	const touch = e.touches[0]
	otherState.startX = touch.clientX
	otherState.startY = touch.clientY
	
	if (props.autoClose && swipeGroup) {
		swipeGroup.closeOthers(instance)
	}
}

const onOtherTouchMove = (e) => {
	if (props.disabled) return

	const touch = e.touches[0]
	otherState.deltaX = touch.clientX - otherState.startX
	otherState.deltaY = touch.clientY - otherState.startY

	const offsetX = Math.abs(otherState.deltaX)
	const offsetY = Math.abs(otherState.deltaY)
	otherState.direction = otherState.direction || getDirection(offsetX, offsetY)

	if (otherState.direction !== 'horizontal') return

	// 如果没有按钮，禁止滑动
	if (otherState.rightWidth === 0) {
		otherState.direction = ''
		return
	}

	const value = otherState.x + otherState.deltaX
	leftOffset.value = Math.min(Math.max(value, -otherState.rightWidth), 0)
}

const onOtherTouchEnd = () => {
	if (props.disabled) return
	
	const threshold = Number(props.threshold)
	const left = leftOffset.value
	const width = otherState.rightWidth
	
	if (otherState.deltaX === 0 && props.clickClose) {
		openOtherState(false)
		return
	}
	
	let shouldOpen = false
	if (!otherState.isOpen && width > 0 && -left > threshold) {
		shouldOpen = true
	} else if (otherState.isOpen && width > 0 && width + left < threshold) {
		shouldOpen = true
	}
	
	openOtherState(shouldOpen)
}

const openOtherState = (open) => {
	const width = otherState.rightWidth
	const targetLeft = open ? -width : 0
	
	if (otherState.isOpen !== open) {
		emit('change', {
			isOpen: open,
			param: props.param
		})
	}
	
	otherState.isOpen = open
	isAnimating.value = true
	nextTick(() => {
		leftOffset.value = targetLeft
	})
}

watch(() => props.show, (val) => {
	openOtherState(val)
})

watch(() => props.buttons, () => {
	leftOffset.value = 0
	otherState.x = 0
	setTimeout(getOtherBtnWidth, 100)
})

onMounted(() => {
	nextTick(() => {
		setTimeout(getOtherBtnWidth, 100)
	})
})
// #endif

// 关闭菜单方法（供外部调用）
const close = () => {
	// #ifdef APP-VUE || MP-WEIXIN || H5
	showState.value = 'none'
	// #endif
	
	// #ifdef APP-NVUE
	nvueOpen(false)
	// #endif
	
	// #ifndef APP-PLUS || MP-WEIXIN || H5
	openOtherState(false)
	// #endif
}

// 初始化方法
const init = () => {
	// #ifndef APP-VUE || MP-WEIXIN || H5
	leftOffset.value = 0
	otherState.x = 0
	setTimeout(getOtherBtnWidth, 100)
	// #endif
}

// 注册到父组件
onMounted(() => {
	if (swipeGroup) {
		swipeGroup.addChild({
			close,
			init,
			instance
		})
	}
	
	nextTick(() => {
		setTimeout(() => {
			showState.value = props.show ? 'right' : 'none'
			isDisabled.value = props.disabled
			thresholdVal.value = Number(props.threshold)
		}, 10)
	})
})

onBeforeUnmount(() => {
	if (swipeGroup) {
		swipeGroup.removeChild(instance)
	}
})

// 暴露方法
defineExpose({
	close,
	init
})
</script>

<style scoped>
.z-swipe__wrap {
	position: relative;
	overflow: hidden;
}

.z-swipe__inner {
	/* #ifndef APP-NVUE */
	display: flex;
	flex-shrink: 0;
	/* #endif */
	position: relative;
}

.z-swipe__content {
	/* #ifndef APP-NVUE */
	width: 100%;
	position: relative;
	z-index: 10;
	/* #endif */
	flex: 1;
	background-color: #ffffff;
}

.z-swipe__buttons {
	/* #ifndef APP-NVUE */
	display: inline-flex;
	box-sizing: border-box;
	/* #endif */
	flex-direction: row;
	position: absolute;
	top: 0;
	bottom: 0;
	/* #ifdef H5 */
	cursor: pointer;
	/* #endif */
}

/* 右侧按钮 */
.z-swipe__buttons--right {
	right: 0;
	transform: translateX(100%);
}

/* 左侧按钮 */
.z-swipe__buttons--left {
	left: 0;
	transform: translateX(-100%);
}

.z-swipe__btn {
	/* #ifdef APP-NVUE */
	flex: 1;
	/* #endif */
	/* #ifndef APP-NVUE */
	display: flex;
	/* #endif */
	flex-direction: row;
	justify-content: center;
	align-items: center;
	padding: 0 48rpx;
	/* #ifdef H5 */
	cursor: pointer;
	/* #endif */
}

.z-swipe__btn-text {
	/* #ifndef APP-NVUE */
	flex-shrink: 0;
	white-space: nowrap;
	/* #endif */
}

.z-swipe__ani {
	transition-property: transform;
	transition-duration: 0.3s;
	transition-timing-function: cubic-bezier(0.165, 0.84, 0.44, 1);
}
</style>
