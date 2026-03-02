<template>
	<!-- #ifndef APP-NVUE -->
	<view class="z-fly-to" @tap.stop="handleTap">
	<!-- #endif -->
	<!-- #ifdef APP-NVUE -->
	<view class="z-fly-to" @touchstart="onTouchStart" @touchend="onTouchEnd">
	<!-- #endif -->
		<view v-if="flying" class="z-fly-to__x" :style="xStyle">
			<view class="z-fly-to__y" :class="{ 'z-fly-to__y--android': isAndroid }" :style="yStyle">
				<slot name="fly"></slot>
			</view>
		</view>
		<slot></slot>
	</view>
</template>

<script setup>
/**
 * z-fly-to 飞入动画
 * @description 贝塞尔曲线抛物线动画，适用于加入购物车、收藏等场景
 * @property {String}        direction  飞行方向 lt|rt|lb|rb（默认 lb）
 * @property {Number|String} top        目标距顶部 rpx（默认 100）
 * @property {Number|String} bottom     目标距底部 rpx（默认 100）
 * @property {Number|String} left       目标距左侧 rpx（默认 60）
 * @property {Number|String} right      目标距右侧 rpx（默认 60）
 * @property {Number|String} duration   动画时长 ms（默认 500）
 * @property {Any}           extra      自定义数据，回调返回
 * @event {Function} click 点击回调 { extra }
 */
import { ref, nextTick } from 'vue'

const props = defineProps({
	direction: { type: String, default: 'lb' },
	top: { type: [Number, String], default: 100 },
	bottom: { type: [Number, String], default: 100 },
	left: { type: [Number, String], default: 60 },
	right: { type: [Number, String], default: 60 },
	duration: { type: [Number, String], default: 500 },
	extra: { type: [Number, String, Object], default: 0 }
})

const emit = defineEmits(['click'])

const flying = ref(false)
const xStyle = ref('')
const yStyle = ref('')
const isAndroid = ref(false)

let lastTapTime = 0
let screenW = 375
let screenH = 667
let navBarH = 0

const sys = uni.getSystemInfoSync()
screenW = sys.windowWidth
screenH = sys.windowHeight

// #ifdef APP-NVUE
isAndroid.value = (sys.platform || '').toLowerCase() === 'android'
navBarH = sys.statusBarHeight + 44
let _startTouch = {}
let _startTime = 0

const onTouchStart = (e) => {
	_startTouch = e.changedTouches[0]
	_startTime = Date.now()
}

const onTouchEnd = (e) => {
	const endX = e.changedTouches[0].screenX
	if (Math.abs(_startTouch.screenX - endX) < 5 && Date.now() - _startTime < 300) {
		handleTap({ touches: [_startTouch] })
	}
}
// #endif

/** 获取触摸坐标（兼容各平台） */
const resolveTouch = (e) => {
	let touch = null
	// #ifdef MP-ALIPAY
	touch = e.detail
	// #endif
	// #ifdef MP-BAIDU
	touch = e.changedTouches[0]
	// #endif
	// #ifndef MP-ALIPAY || MP-BAIDU
	touch = e.touches[0]
	// #endif
	// #ifdef APP-NVUE
	touch = { clientX: touch.screenX, clientY: touch.screenY }
	// #endif
	return touch
}

/** 计算目标点的视口绝对坐标 */
const getTarget = () => {
	const t = uni.upx2px(Number(props.top))
	const b = uni.upx2px(Number(props.bottom))
	const l = uni.upx2px(Number(props.left))
	const r = uni.upx2px(Number(props.right))

	switch (props.direction) {
		case 'rt': return { x: screenW - r, y: t }
		case 'rb': return { x: screenW - r, y: screenH - b }
		case 'lt': return { x: l, y: t }
		case 'lb':
		default:   return { x: l, y: screenH - b }
	}
}

/** 处理点击（含防抖） */
const handleTap = (e) => {
	const now = Date.now()
	const dur = Number(props.duration)
	if (now - lastTapTime <= dur + 50) return
	lastTapTime = now
	setTimeout(() => { lastTapTime = 0 }, dur + 40)

	playAnimation(e)
	emit('click', { extra: props.extra })
}

/**
 * 飞行动画核心
 * 使用 position:fixed 脱离文档流，不受父容器 overflow 裁剪
 * X/Y 轴分别使用不同贝塞尔曲线做 transition，叠加产生抛物线
 */
const playAnimation = (e) => {
	const touch = resolveTouch(e)
	const target = getTarget()
	const diffX = target.x - touch.clientX
	const diffY = target.y - touch.clientY
	const dur = `${Number(props.duration) / 1000}s`

	// 第一帧：将飞行元素放在点击位置（无动画）
	// #ifdef APP-NVUE
	xStyle.value = `left:${touch.clientX}px;top:${touch.clientY - navBarH}px;`
	// #endif
	// #ifndef APP-NVUE
	xStyle.value = `left:${touch.clientX}px;top:${touch.clientY}px;`
	// #endif
	yStyle.value = ''

	flying.value = true

	nextTick(() => {
		setTimeout(() => {
			// 第二帧：设置 transform 触发过渡动画
			// #ifdef APP-NVUE
			xStyle.value = `left:${touch.clientX}px;top:${touch.clientY - navBarH}px;transform:translate(${diffX}px,0);transition-duration:${dur};`
			yStyle.value = `transform:translate(0,${diffY + navBarH}px);transition-duration:${dur};`
			// #endif
			// #ifndef APP-NVUE
			xStyle.value = `left:${touch.clientX}px;top:${touch.clientY}px;transform:translate3d(${diffX}px,0,0);transition-duration:${dur};`
			yStyle.value = `transform:translate3d(0,${diffY}px,0);transition-duration:${dur};`
			// #endif

			setTimeout(() => {
				flying.value = false
				xStyle.value = ''
				yStyle.value = ''
			}, Number(props.duration) + 40)
		}, 50)
	})
}
</script>

<style scoped>
.z-fly-to {
	position: relative;
}

/* 关键：用 fixed 定位，脱离文档流，不被任何父容器裁剪 */
.z-fly-to__x {
	position: fixed;
	z-index: 9999;
	pointer-events: none;
	/* #ifndef APP-NVUE */
	display: inline-block;
	/* #endif */
	transition-property: transform;
	transition-duration: 0.5s;
	transition-timing-function: cubic-bezier(0, 0, 0, 0);
}

.z-fly-to__y {
	/* #ifndef APP-NVUE */
	display: inline-block;
	/* #endif */
	transition-property: transform;
	transition-duration: 0.5s;
	transition-timing-function: cubic-bezier(0.3, -0.2, 1, 0);
}

/* #ifdef APP-NVUE */
.z-fly-to__y--android {
	width: 600rpx;
	height: 2000px;
	transition-timing-function: cubic-bezier(0.3, -0.02, 1, 0);
}
/* #endif */
</style>
